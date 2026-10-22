# Frontend verification — 22 October 2026

Scope: C-01 through C-12 against the synthetic demo API. C-13 is blocked by T-22. Google OAuth, model calls, real calendar sync, forwarding email and deployment have not been exercised or represented as completed integration.

| Check                                          | Observed result                                                        | Reproduce                                                                             |
| ---------------------------------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Frontend lint, formatting, strict types, build | Passed                                                                 | `cd web && npm run check`                                                             |
| Frontend unit tests                            | 13 passed                                                              | `npm test` in `web/`                                                                  |
| Real-browser workflows                         | 36 passed, desktop and 375px phone                                     | `npm run test:e2e` in `web/`                                                          |
| Automated accessibility                        | Passed on 11 main routes at both widths; WCAG 2 A/AA and 2.1 AA checks | Accessibility test within the browser suite                                           |
| Production npm dependency audit                | 0 reported vulnerabilities                                             | `npm audit --omit=dev`                                                                |
| Existing Python suite                          | 116 passed; 93.63% coverage                                            | Root `uv run pytest --cov`, using a workspace temporary directory on this machine     |
| Existing Python lint/types                     | Passed                                                                 | Root Make targets / equivalent Ruff and mypy commands                                 |
| Schema and task checks                         | Passed                                                                 | `python -X utf8 scripts/export_schemas.py --check`; `python scripts/tasks.py --check` |

Browser workflows cover planning, questions, approval persistence, chat sources/uncertainty/teaching, review batches, second-president state, calendar completion, knowledge edit proposals, handover export/sign-off, member/document management, setup with skipped questions, adviser restrictions, double clicks, offline/error/fallback/empty/loading states and run limits. They use real Chrome with synthetic records and do not incur model charges.

Visual inspection included the event overview and task workspace at desktop and phone sizes, plus the loaded phone Settings layout. Text contrast was corrected after automated checks found low-contrast secondary labels. Browser tests also check horizontal fit of the main routes.

This is frontend evidence, not evidence that the unimplemented backend agent meets its evaluation targets. The existing Python dependency-audit failure reported in the project review is outside this frontend change; the shared GitHub workflow does not yet run the new frontend checks.
