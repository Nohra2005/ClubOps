"""One client for any OpenAI-compatible provider (D-01): Gemini, Groq, OpenAI, a university gateway...

What a call does, in order:

1. Build the recording key from the model, prompt version, messages and output schema.
2. **Replay mode** (default): return the saved answer, or fail if there is none. Never touches the network.
3. **Record / live mode**: check the budget, call ``{base_url}/chat/completions``, count tokens and cost.
4. Validate the answer against the output schema (a pydantic model). Bad JSON or a wrong shape
   raises ``MALFORMED_MODEL_OUTPUT`` with the cost attached, so the runner retries and the
   spend is still counted (F-40).
5. Record mode saves valid answers only, so a replay always gives a usable answer.

Errors are mapped to the shared ``ErrorCode`` set, so the runner decides retry / fallback / fail.
The API key is never logged, traced or written to a recording.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from clubops.capabilities.runner import CapabilityError, Usage
from clubops.config import ModelMode, Settings
from clubops.contracts.common import ErrorCode
from clubops.model.budget import Budget
from clubops.model.recordings import Recording, RecordingStore, recording_key

T = TypeVar("T", bound=BaseModel)

_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)


@dataclass(frozen=True)
class ModelRequest:
    """What a capability asks the model. ``prompt_version`` changes whenever the prompt text changes."""

    prompt_version: str
    system: str
    user: str
    max_tokens: int = 1500
    temperature: float = 0.0

    def messages(self) -> list[dict[str, str]]:
        return [{"role": "system", "content": self.system}, {"role": "user", "content": self.user}]


def _strip_fences(text: str) -> str:
    match = _FENCE.match(text)
    return match.group(1) if match else text.strip()


class ModelClient:
    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout_s: float = 30.0,
    ) -> None:
        self.settings = settings
        self.recordings = RecordingStore(settings.recordings_dir)
        self._transport = transport
        self._timeout_s = timeout_s

    # ------------------------------------------------------------------ public

    def complete(self, request: ModelRequest, output: type[T], budget: Budget | None = None) -> tuple[T, Usage]:
        """Ask the model and return the validated answer plus what it cost."""
        model = self.settings.model or "unset"
        key = recording_key(model, request.prompt_version, request.messages(), output.model_json_schema())

        if self.settings.mode is ModelMode.REPLAY:
            saved = self.recordings.get(key)
            if saved is None:
                raise CapabilityError(
                    ErrorCode.NOT_FOUND,
                    f"no recording for prompt {request.prompt_version}; run once with CLUBOPS_MODEL_MODE=record",
                )
            usage = Usage(
                model=saved.model,
                prompt_version=saved.prompt_version,
                tokens_in=saved.tokens_in,
                tokens_out=saved.tokens_out,
                replayed=True,
            )
            if budget is not None:
                budget.check()
                budget.charge(usage)
            return self._parse(saved.text, output, usage), usage

        if budget is not None:
            budget.check()
        text, usage = self._call(request, output)
        if budget is not None:
            budget.charge(usage)
        parsed = self._parse(text, output, usage)
        if self.settings.mode is ModelMode.RECORD:
            self.recordings.put(
                Recording(
                    key=key,
                    model=model,
                    prompt_version=request.prompt_version,
                    text=text,
                    tokens_in=usage.tokens_in,
                    tokens_out=usage.tokens_out,
                )
            )
        return parsed, usage

    # ----------------------------------------------------------------- private

    def _cost(self, tokens_in: int, tokens_out: int) -> Decimal:
        per_million = Decimal(1_000_000)
        cost_in = Decimal(tokens_in) * self.settings.price_in_per_mtok
        cost_out = Decimal(tokens_out) * self.settings.price_out_per_mtok
        return (cost_in + cost_out) / per_million

    def _call(self, request: ModelRequest, output: type[BaseModel]) -> tuple[str, Usage]:
        s = self.settings
        if not (s.base_url and s.api_key and s.model):
            raise CapabilityError(
                ErrorCode.INTERNAL,
                "model not configured: set CLUBOPS_BASE_URL, CLUBOPS_API_KEY and CLUBOPS_MODEL",
            )
        body: dict[str, Any] = {
            "model": s.model,
            "messages": request.messages(),
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {s.api_key.get_secret_value()}"}
        try:
            with httpx.Client(transport=self._transport, timeout=self._timeout_s) as http:
                response = http.post(f"{s.base_url}/chat/completions", json=body, headers=headers)
        except httpx.TimeoutException as exc:
            raise CapabilityError(ErrorCode.UPSTREAM_TIMEOUT, "model provider timed out") from exc
        except httpx.HTTPError as exc:
            reason = f"could not reach the model provider: {type(exc).__name__}"
            raise CapabilityError(ErrorCode.UPSTREAM_ERROR, reason) from exc

        if response.status_code == 429:
            raise CapabilityError(ErrorCode.RATE_LIMITED, "model provider rate limit")
        if response.status_code in (401, 403):
            raise CapabilityError(ErrorCode.INTERNAL, "model provider refused the API key")
        if response.status_code >= 400:
            raise CapabilityError(ErrorCode.UPSTREAM_ERROR, f"model provider returned HTTP {response.status_code}")

        try:
            payload = response.json()
            text = payload["choices"][0]["message"]["content"] or ""
            tokens = payload.get("usage") or {}
            tokens_in = int(tokens.get("prompt_tokens", 0))
            tokens_out = int(tokens.get("completion_tokens", 0))
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            reason = "unexpected response shape from the model provider"
            raise CapabilityError(ErrorCode.UPSTREAM_ERROR, reason) from exc

        usage = Usage(
            model=s.model,
            prompt_version=request.prompt_version,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=self._cost(tokens_in, tokens_out),
        )
        return text, usage

    @staticmethod
    def _parse(text: str, output: type[T], usage: Usage) -> T:
        try:
            return output.model_validate(json.loads(_strip_fences(text)))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise CapabilityError(
                ErrorCode.MALFORMED_MODEL_OUTPUT,
                f"model answer did not match {output.__name__}",
                usage=usage,
            ) from exc
