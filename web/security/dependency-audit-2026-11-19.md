# Frontend dependency audit: 19 November 2026 (C-36)

The locked development chain reported nine affected package nodes through one
minimatch advisory, [GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249).
The advisory describes glob-pattern resource amplification and identifies 11.0.1
as the first patched version. The original lock resolved 10.2.6 through ESLint and
TypeScript-ESLint. Production-only audit reported zero; no production incident or
measured exploit rate is inferred from these scans.

`npm audit fix --package-lock-only --ignore-scripts` resolved compatible tool updates
without force or dependency overrides. Application dependency ranges are unchanged.
A structural comparison against main 166f27e verifies every non-development lock
entry is unchanged. The development chain now resolves:

| Package              | Before  | After   |
| -------------------- | ------- | ------- |
| eslint               | 10.13.0 | 10.15.0 |
| typescript-eslint    | 8.72.0  | 8.73.0  |
| @eslint/config-array | 0.23.5  | 0.23.6  |
| minimatch            | 10.2.6  | 11.0.9  |

A fresh `npm ci` installs the patched lock. Both full and production-only audits
report zero vulnerabilities at this date. Reproduce from `web/`:

```sh
npm ci
npm run audit:dependencies
npm audit --omit=dev
npm run check
```

The full command includes development dependencies and fails at moderate severity;
it is the regression check for the vulnerable tool chain. Results depend on the
registry's current advisory data and require network access. On Windows with the
trusted enterprise root installed, `NODE_USE_SYSTEM_CA=1` lets Node use that trust
store; certificate verification and audit checks stay enabled.

This update changes no application behavior, backend contracts or workflow files.
The report evidence index is owner-maintained; link this file after independent
review. Final validation counts and current-head CI belong in the PR/handoff.
