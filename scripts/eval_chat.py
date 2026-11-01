"""Score the cited chatbot in replay mode on a redacted private or synthetic CSV.

CSV columns: id, question, expected_answer, supporting_ids. Blank expected_answer
means the correct reply is unknown. supporting_ids is a semicolon-separated list.
Knowledge JSON, if supplied, is an array of approved KnowHowItem objects. Do not
commit private questions, facts, recordings, or answer text.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.load_rulebook import read_rulebook

from clubops.chat.ask import ask
from clubops.config import load_settings
from clubops.contracts.knowhow import Answer, AskRequest, KnowHowItem
from clubops.evaluation.chat import load_cases, score, table
from clubops.knowhow.store import KnowHowStore
from clubops.model.budget import Budget
from clubops.model.client import ModelClient, ModelRequest


class MeteredModel:
    def __init__(self, client: ModelClient) -> None:
        self.client = client
        self.last_cost = Decimal("0")

    def complete(self, request: ModelRequest, output: type[Answer], budget: Budget) -> tuple[Answer, object]:
        answer, usage = self.client.complete(request, output, budget)
        prices = self.client.settings
        self.last_cost = usage.cost_usd or (
            Decimal(usage.tokens_in) * prices.price_in_per_mtok + Decimal(usage.tokens_out) * prices.price_out_per_mtok
        ) / Decimal(1_000_000)
        return answer, usage


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--knowledge", type=Path, help="private approved KnowHowItem JSON array")
    parser.add_argument("--club", default="running-club")
    parser.add_argument("--as-of", type=date.fromisoformat, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    store = KnowHowStore()
    for item in read_rulebook():
        store.backend.append(item)
    if args.knowledge is not None:
        for item in json.loads(args.knowledge.read_text(encoding="utf-8")):
            store.backend.append(KnowHowItem.model_validate(item))
    cases = load_cases(args.cases, args.club, args.as_of)
    model = MeteredModel(ModelClient(load_settings()))

    def predict(request: AskRequest) -> tuple[Answer, Decimal]:
        model.last_cost = Decimal("0")
        answer = ask(request, store, model)  # type: ignore[arg-type]  # duck-typed meter
        return answer, model.last_cost

    result = score(cases, predict)
    rendered = f"# Chatbot evaluation ({len(cases)} questions)\n\n{table(result)}\n"
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
