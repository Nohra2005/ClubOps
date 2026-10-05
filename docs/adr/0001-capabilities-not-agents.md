# ADR 0001: Contracts belong to capabilities, not agents

**Status:** accepted · 2026-10-05

**Context.** The brief warns that "more agents do not imply a better system", and the poster commits to keeping specialist agents only if they beat a single-agent baseline. If interfaces were defined per agent (intake agent, sponsor agent…), losing that comparison would mean rewriting them.

**Decision.** Contracts are defined per **capability**: a typed function with one request and one response model (`capabilities/registry.py`). An "agent" is only a policy for calling capabilities. A single agent and a multi-agent orchestration call the same functions.

**Consequences.** The single- versus multi-agent comparison becomes a controlled experiment. Capabilities can be built and tested in parallel behind stable contracts.
