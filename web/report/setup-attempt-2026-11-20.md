# README-only teammate setup attempt - 20 November 2026

Task: C-29. Reviewer: Joey (`JS9872`). This receipt records his reported outcome;
Christophe did not repeat or witness the attempt on Joey's machine.

Source: [Joey's dated PR comment](https://github.com/Nohra2005/ClubOps/pull/99#issuecomment-7025379118).

## Attempt and result

Joey followed the README's complete-app Docker prerequisite. His Docker version
check failed while connecting to `//./pipe/dockerDesktopLinuxEngine`: the named
pipe was absent. Docker's Linux engine was unavailable on that machine, so the
attempt stopped before the app could start.

He did not claim a fresh install, successful Compose startup, browser login,
deployed persistence or changes to dependencies/host configuration. Existing
Python/uv checks are separate evidence. No secrets or club data are included here.

## What remains

The acceptance condition remains open: a teammate must bring up the complete app
from a fresh checkout using only the README. Once a working Linux container engine
is available, repeat the documented Compose command and record the source commit,
commands, startup/login outcome and any exact failure. If instructions need changing,
request the README owner's edit rather than silently substituting undocumented steps.

This is a concrete prerequisite failure, not a successful setup receipt or a claim
that the application itself failed. C-29 stays doing; the existing setup browser
regressions prove a different, synthetic local HTTP boundary.
