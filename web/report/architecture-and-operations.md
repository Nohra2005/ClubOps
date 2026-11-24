# Report sections: architecture, web app, deployment and monitoring

Christophe's C-29 draft, updated 24 November 2026. Interface baseline: main `62d1787`.
For Tatiana to review and incorporate into T-27. These sections describe implemented
boundaries and local evidence. Final provider/evaluation results, hosted acceptance
and team/user observations must be added from their actual records.

## Architecture and human approval

ClubOps separates a cabinet-facing React app from a FastAPI service through published
HTTP interfaces and versioned contracts. The browser presents events, agent runs,
Review, knowledge, calendar, handover and settings. Its HTTP adapter translates
contract fields, rejects incompatible responses and reports unavailable actions;
its separate demo adapter uses synthetic data. A working demo screen therefore does
not establish a working production integration. The interface boundaries and diagram
are in [architecture.md](../../docs/architecture.md) and
[API_NOTES.md](../API_NOTES.md).

Before protected screens render, the HTTP adapter validates the published session
view: declared roles, identity/club fields, boolean setup flags and nonnegative
badge counts. Invalid responses show a recoverable connection error with an
explicit retry; the client does not infer a role or substitute demo data. The
server independently authorizes each action. The merged
[session validator](../src/api/session-response.ts) and
[HTTP regression cases](../e2e/session-http.spec.ts) support this boundary; synthetic
responses do not establish real Google or deployed authentication acceptance.

Within a person-started planning run, the agent chooses tools and can ask for missing
information. Code constrains transitions and each allowance of eight steps and $0.05.
A limited run needs explicit continuation. Saving a proposed plan does not approve
it: the person approves a specific revision before internal calendar items appear.
The local [real HTTP regression](../e2e/live-api.spec.ts) observes this before/after
boundary with actual session cookies and SQLite, using a scripted model. This is
integration evidence, rather than a measurement of model planning quality or Google
Calendar synchronization.

Knowledge has a separate approval boundary. External descriptions, documents and
interview answers are untrusted inputs. Learning proposes source-supported changes;
a person's Review decision normally creates verified knowledge. The merged trusted
OSA exception allows code to apply a clean new fact after source checks and the
explicit paid read. Overrides/merges, contradictions and flagged mail still wait
for review (D-151/#150), and applied changes retain Edit/Undo history. This does
not establish a deployed background-reading schedule. Shared AUB rules and club
know-how occupy separate scopes, with current validity filtering. Warning, disputed
and shared cards require individual frontend review; their server authorization is
independent of visibility in the browser. The current shared-review flow follows
the single-president contract; proposed future governance is not described as
implemented. See [knowledge-base.md](../../docs/knowledge-base.md),
[REVIEW_GUIDE.md](../REVIEW_GUIDE.md) and the
[HTTP review regressions](../e2e/contracts.spec.ts).

## Web app and new-club onboarding

The president interview is the onboarding path, without requiring member chat
history (D-103). Merged #55 provides the owned setup service and #87 registers it in
the application. `POST /api/setup/next` either resumes, submits an explicit answer
or skips a question. Durable per-club progress is separate from proposed/verified
knowledge. Extracted proposals pass to Review; completion does not rename the club,
change cabinet accounts or approve facts. The four starter steps are separate,
browser-local acknowledgements, and upload acknowledgement is not learning success.

The new [setup HTTP regression](../e2e/setup-live.spec.ts) uses the production app
factory without intercepting or replacing its routes. Separate synthetic clubs
exercise desktop and phone redirects, stop/reload/resume, completion with skips,
`/me` completion, empty Review and unchanged starter ticks. Missing-CSRF requests and
adviser writes receive 403. Skipping avoids model extraction; these results do not
measure learned-fact correctness, real Google login, worker-restart persistence or
actual ASME onboarding. The older Python endpoint fixture installs a reference
adapter and tests a different boundary. Reproduction and acceptance gaps are in
[CLUB_SETUP.md](../CLUB_SETUP.md).

The answer-only setup contract retains an accepted stale-tab limit (F-151): a delayed
answer can reach a later question. The UI asks for one tab. Rejected-card
persistence was addressed in #142; the setup browser test does not establish
recovery of every interrupted capture/queue failure path.

Merged #123 adds a four-stop guided role introduction with browser-local,
member/club/role-isolated progress and an expandable cited reference. It does not
transfer membership or prove training. Ask is now wired to the source-gated core
for the authenticated club (#149/D-200), with dated source labels and inactive
facts filtered. Structured tutoring, term persistence and measured user benefit
remain separate work. Expiry visibility and Review draft protection merged in
#152; Knowledge expiry editing after approval still needs an API field.

## Deployment and authentication

The production image builds the static frontend and serves it through Caddy on the
same origin as `/api`. One API worker uses `CLUBOPS_DATA_DIR` on a persistent volume.
The production configuration requires a Google client ID, a server signing secret,
secure cookies and disabled development login. Google identity maps to the cabinet
list; authorization derives from the server session. The frontend does not keep
the provider token or choose the acting club. A separate local Compose target
provides explicit synthetic development login and a volume-backed signing secret.
The production target rejects that development build. See [Dockerfile](../../Dockerfile),
[deployment configuration](../../render.yaml) and [DEPLOYMENT.md](../DEPLOYMENT.md).

Local container and persistence checks are implemented in the
[Compose persistence checker](../scripts/check-compose-persistence.mjs) and recorded
in [VERIFICATION.md](../VERIFICATION.md). They do not prove a public deployment,
production OAuth origin, paid-service approval or backup restoration. The prepared
Render configuration needs persistent storage; the configuration alone is not evidence of a hosting purchase
or successful deployment. In-process planning also means durable background-job recovery and
horizontal scaling are not supported claims. Finish active runs before restart.

## Cost reporting and observability

The [reporting modules](../../src/clubops/reports/) aggregate scoped run/trace metadata,
deduplicate cumulative snapshots and distinguish planner steps from provider calls.
Unavailable tokens, retries or latency remain unavailable rather than becoming zero.
Cost per successful recorded plan is a recorded-coverage metric, not an assertion
that every historical plan or provider bill was observed. Source text, prompts,
answers and personal labels are excluded from this report sink. Private debug logs
and model recordings are separate sensitive stores, as explained in
[data-provenance.md](../../docs/data-provenance.md).

The optional closed-run OTLP/HTTP exporter is implemented, defaults off and requires
explicit run/step/model-call associations and aware timing windows. The
[observability guide and evidence](../observability/README.md) document actual local
Jaeger readback for a synthetic run. That proves the exporter/viewer path for supplied
metadata; it does not prove real agent producer hooks or a deployed dashboard and
alert. Real provider measurements, producer integration and hosted monitoring remain
C-20/C-25/C-26 acceptance work. No synthetic zero cost is treated as a measured bill.

## Verification and remaining acceptance

Reproduce root checks with `make check`; run frontend quality/build checks with
`cd web` then `npm ci` and `npm run check`. Run the actual local HTTP integration
suite with `npm run test:e2e:live`; its setup cases also run on desktop and phone.
These require the documented Python/Node tools and installed Playwright browser.
CI replays/scripted responses do not spend provider credit. Dated commands and
outcomes belong in [VERIFICATION.md](../VERIFICATION.md).

Merge commits preserve the small change history. Earlier PRs have independent
review evidence; Chris relayed a temporary review waiver on 24 November. Do not
claim that a waived PR had an approving review.
Prepared tooling and synthetic tests support engineering claims within their stated
scope. C-29 remains doing until Joey's fresh README-only setup and Tatiana's report
handoff/review are recorded. Public deployment, real Google/provider tests, actual
club acceptance, final frozen evaluation thresholds require their own evidence; none are inferred from a passing test or board
iteration date. The owner-maintained report evidence index must link these files
before publication.

## README-only teammate setup evidence

[Joey's 20 November attempt](setup-attempt-2026-11-20.md) stopped at the Docker
prerequisite: the Linux engine named pipe was absent. It did not reach Compose
startup or login, so the fresh README-only setup acceptance remains open. Retain
this concrete failure alongside the automated local evidence rather than replacing
it with an inferred success. Repeat the documented flow when a working engine is
available; real deployment and provider acceptance remain separate.

## Weekly-review and backlog evidence

C-31 was restored on 23 November, superseding the earlier D-133 cut (D-137 in #91).
Christophe reports Monday meetings on 2, 9, 16 and 23 November. The native board
reconciler maps task statuses and real GitHub assignees, creates those Monday
iterations and supplies present-day backlog priorities/estimates. Existing custom
fields, issue cards and historical receipts remain intact.

The [weekly commit-history summaries](https://github.com/Nohra2005/ClubOps/pull/91) in #91 link
repository activity for those weeks. Dates are owner-reported; the summaries do
not establish attendance, oral decisions or original assignments. They should not
be described as contemporaneous minutes or used to claim unverified outcomes.
Other CI, testing and observability evidence retains its stated scope and limits.

## 24 November hosted availability observation

A read-only request to the previously supplied Azure origin returned HTTP 200
for `/login`; unauthenticated `/api/me` returned 401. This proves the public page
and session boundary responded at that observation, not a logged-in cabinet flow
or the deployed build version. `/health` was not accepted as an API-health proof:
the static router can serve the SPA for arbitrary non-API paths. SSH to the VM
port 22 timed out, so no running-image inspection or deployment update is claimed.
No private account, provider call, raw club data or credential was used in this
public check. Google login, current-image deployment and recovery acceptance remain
separate checks once administrative access is restored.
