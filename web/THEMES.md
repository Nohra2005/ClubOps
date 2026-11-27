# Frost and Afterdark

Task: C-40. Decision: D-256. Safeguards: F-511/F-512.

Chris selected both glass appearances after eight standalone previews. Frost uses
ice-blue surfaces and a warm backdrop; Afterdark uses deep blue glass and mint
actions. The sun/moon button is available in the workspace header and on sign-in.

The choice is saved in the browser as `clubops.theme`, applied before React
renders and shared between tabs. Invalid or cleared values use Frost. Blocked
storage keeps an in-tab choice. Appearance does not change club, role, term,
session, permissions or Google connections and sends no API mutation.

## Surfaces and reading

- Semantic tokens in `src/theme/tokens.css` define text, controls and status colors
  for both appearances. Existing status labels remain alongside color.
- `glass.css` styles the shell and navigation. Its decorative backdrop is a
  pseudo-element so it cannot change fixed dialogs' containing block.
- `controls.css` keeps form controls, menus, source chips and dialogs on readable
  surfaces. `workspaces.css` covers the planning, review, knowledge and chat pages.
- Desktop events use two columns; phones use one, with contained horizontal
  filtering and floating navigation. Primary actions retain generous targets.
- Reduced transparency and missing blur support use solid surfaces. Motion
  preferences and a light, source-preserving print layout remain available.

The design retains fact expiry, provenance, disagreement, explicit approvals,
cost limits, independent errors and role restrictions. It adds no copy, provider
integration or automatic model activity to the product flows.

## Verification

```sh
cd web
npm run check
npm run test:e2e
npm run test:e2e:http
npm run test:e2e:live
```

`e2e/theme.spec.ts` covers persistence, malformed/blocked storage, tab updates and
absence of API mutations. `e2e/theme-accessibility.spec.ts` scans 13 routes with
Axe in both themes on desktop and phone, checks overflow, source printing and
review-dialog reading, keyboard controls, Escape and focus restoration. Native
Chromium focus visits browser chrome between cycles; the test rejects focused
background controls while allowing that browser-owned transition.

Automated accessibility checks supplement visual inspection; they do not prove
every assistive-technology combination or real Google sign-in. Synthetic workflow
and HTTP tests remain separate from production/provider acceptance. Live cabinet
activation still needs the backend contract requested in #169.
