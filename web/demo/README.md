# C-28 synthetic demo rehearsal

This tool practices the five-minute [presenter script](../../docs/demo-script.md).
It uses the actual frontend HTTP adapter with intercepted synthetic responses.
The persistent on-screen disclosure is part of the recording. It makes no backend,
model, Google, email or OSA call and proves no backend authorization or injection
defense. C-28 remains in progress until the deployed run, team rehearsal and final
narrated backup exist.

## Fast checks

From `web/`, with dependencies installed using `npm ci`:

```powershell
npm run typecheck:rehearsal
npm run demo:check
```

Use installed Chrome (the default) or the normal `PLAYWRIGHT_CHANNEL=bundled`
configuration after installing Chromium. The check starts its own HTTP-mode Vite
on `127.0.0.1:5174`, runs on desktop and phone, and exits nonzero if a scene or guard
fails. The regular HTTP suite includes these checks in existing web CI. Fifteen
fixture/target tests are also included in `npm test`; the runner is type-checked by
`npm run check` and is outside the shipped `src/` bundle.

Run browser suites sequentially: normal suites share `web/test-results`, which
Playwright clears. The dedicated recording uses a new uniquely allocated
directory under root `output/`, without overwriting earlier recordings.

## Record the silent five-minute walkthrough

```powershell
npx playwright install ffmpeg
npm run demo:record
```

If Node reports a certificate-chain error on a managed Windows machine, enable
its normal Windows certificate store for the current shell and retry:

```powershell
$env:NODE_OPTIONS = ($env:NODE_OPTIONS + ' --use-system-ca').Trim()
npx playwright install ffmpeg
```

This preserves TLS verification; do not disable certificate checks. Use Node 24
for this certificate option on this machine. The FFmpeg binary is a Playwright
runtime tool; no project dependency or global video application is installed.

Recording starts an isolated Vite on `127.0.0.1:5176`, a fresh browser context and
one desktop test. Port conflicts fail rather than reusing another running app.
No arbitrary/public target URL option exists. WebSockets are closed, service
workers are blocked and external requests are aborted. Unknown API actions are
fulfilled with a synthetic 501 and fail the screenplay instead of reaching a server.
The script uses only its inline TXT fixture; it never opens a file picker onto
personal files or connects to an existing browser/profile.

Chapter timings total 300 seconds, including pauses to practice narration. Slow
actions can add time; the test has a 390-second cap and no automatic retry. The
video is **silent**, so use it to rehearse with the script. It is not the final
narrated/deployed backup and should not be submitted as one.

The launcher prints its new `output/demo-rehearsal-<unique>` directory at the
repository root and checks that it stays inside the workspace. It passes the same
absolute output path to every worker. Use `npm run demo:record`, rather than calling
the recording config directly. `npm run demo:record -- --list` checks the configuration
without starting a server or recording. Inside the take's test subdirectory:

- `backup-rehearsal.webm`: validated silent take when recording succeeds.
- `rehearsal-proof.json`: disclosure, six passing chapters, fixture request/action
  counts, zero unexpected requests, video byte size/SHA-256 and pending acceptance.
- `rehearsal-summary.png`: the final disclosed frame.

Videos are local runtime artifacts under untracked `output/`; do not commit raw
recordings or personal footage. A failure may still produce Playwright's automatic
`video.webm` or an error context, but **no passing proof** is written for an incomplete
script. Diagnose the failed assertion and run a new take; do not rename failed
footage into a passing backup. The checksum binds the proof to the successful file,
not to a person's approval or a deployed result.

To check a take without opening it (replace the path with the printed directory):

```powershell
$take = 'C:\path\to\output\demo-rehearsal-...\test-directory'
$proof = Get-Content -Raw (Join-Path $take 'rehearsal-proof.json') | ConvertFrom-Json
$actual = (Get-FileHash (Join-Path $take $proof.recording.file) -Algorithm SHA256).Hash
$actual.ToLowerInvariant() -eq $proof.recording.sha256
```

The comparison must be `True`, all six chapters must pass and `unexpected_requests`
must be zero. Inspect the video/disclosure visually too; the manifest is operational
evidence, not a security proof or authenticated review. Keep the full take and its
matching proof together; label any edited/narrated export separately with a new hash.

## Remaining final acceptance

The [local proof](evidence/local-proof.json) records an actual 301.56-second silent
take on 10 November, with a matching file hash and six passing chapters. The
[question frame](evidence/question.png) and [warning frame](evidence/warning.png)
were extracted from that take and inspected. The source revision and the later
bare-API-prefix guard are distinguished in the proof. Raw footage stays local;
its hash is historical evidence, not an expected byte-for-byte result of a new take.

Tatiana/Joey review the script and replace scripted scenes with observed real
backend outcomes, using synthetic accounts/documents and a declared provider mode.
C-14/C-18 provide the verified deployed link. Rehearse with the team once, time it,
record narration, preserve the exact backup/checksum and link the evidence. Do not
invent missing evaluation numbers, AUB rules, real club facts or successful defenses.
