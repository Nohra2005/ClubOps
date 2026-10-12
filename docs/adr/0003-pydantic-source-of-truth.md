# ADR 0003: Pydantic models are the source of truth for contracts

**Status:** accepted · 2026-10-05

**Decision.** Contracts are Pydantic v2 models with invariants as validators. JSON Schemas and `docs/capabilities.md` are generated (`scripts/export_schemas.py`) and CI fails if they drift. Model output is validated against the same models.

**Alternatives.** Hand-written JSON Schema (drifts from code); TypedDicts (no runtime validation).

**Consequences.** One definition is used for validation, structured model output, docs and tests.
