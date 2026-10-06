# Repair progress / handoff memory

Updated: 2026-10-06. Branch: `fix-for-the-app`.

## User decisions and scope

- Implement `docs/fix-plan.md`, with a focused commit for each repair.
- Fix reliability before a UI prototype. No visual redesign in this work.
- Superseding decision: database-free create → preview PDF → download PDF. The earlier
  PostgreSQL/local SQLite choice is retired; see `docs/db-free-plan.md`.
- Do not provision services, deploy, or push without another request.
- Keep detailed completed-fix history here; chat updates should stay brief.

## Completed commits

Database-free conversion:

- `0c325cc`: signed browser-carried full state/undo history and detached domain transitions.
- `e48c305`: stateless HTTP/UI switch replaces database adapters and saved-character listing.
  Tokens live in per-tab session storage; Home clears the draft. PDF export returns bytes
  and the browser reuses one Blob for preview/download, revoking it on reset/mutation.
  Python workflow regressions now use a browser-like token-carrying test client; raw-client
  tests prove IDs/cookies alone cannot recover state and independent instances need no DB.
  PostgreSQL dependency, schema/cleanup commands and CI database service are removed.
- `f029ca8`: recoverable oversized-state errors, lossless spell-PDF compaction, isolated
  page overlays and full-Chromium viewer regressions. Verified the full manual magic flow.
- Final packaging/handoff commit: `.vercelignore` excludes dependencies, test artifacts,
  development secrets and old local database/output files while retaining runtime PDF,
  font and web assets. Plans are marked complete; use `git log` for this commit's ID.

The original repair history below describes the earlier architecture; the database-free
decision above supersedes its persistence, ownership-cookie and deployment requirements.

Current conversion checks: 414 Python tests on a clean Python 3.12 environment, 15 frontend
regressions, eight desktop/phone browser workflows, catalog validation and Ruff lint/format
checks pass. Browser preview/download bytes match; fixed a CSS rule that overrode the
download link's `hidden` attribute on Home. No database credentials, services or cookies
are used. No push or deployment was performed.
Browser checks use full Chromium (`channel: chromium`) rather than its PDF-less headless
shell. Inspected the actual filled PDF viewer on desktop/phone and final spell-card pages.

Final edge-case work: distinguish oversized valid drafts (HTTP 413, preserve current token)
from invalid drafts (HTTP 410). A complete level-10 mage exposed a >10 MB PDF response;
exclude non-rendering Photoshop `/PieceInfo` from spell templates, reuse their reader,
compress content streams and deduplicate objects. A visual check also caught shared content
streams accumulating overlays: only background resources are shared now, with independent
page content and exact per-page card regression checks. The representative 21-spell/five-page
PDF is 3,805,639 bytes instead of >10 MB. The level-10 API regression fits Vercel's 4.5 MB
buffered-response limit; renderer and pixel-identity tests remain mandatory.

| Commit | Repair |
| --- | --- |
| `df84750` | Production session secret and safe PDF destinations |
| `7f2148d` | API request validation |
| `2a850c0` | Immutable checkpoints and deterministic undo |
| `ab2d98b` | Atomic choice batches |
| `7ff6867` | Required paths/equipment gate progression and export |
| `66a9e9b` | Creation service, ownership and atomic version checks |
| `270cb9d` | Literacy and language benefits |
| `0d78a85` | Lazy choices, random progression and profession keys |
| `ab5d386` | Supplement filtering throughout generation |
| `9d6bb03` | Cached isolated catalog access and embedded path spells |
| `d24e4ff` | Durable SQLite/PostgreSQL storage and owned creation listing |
| `09fa9b6` | Immutable versioned PDF snapshots and isolated rendering |
| `e862a4b` | Refresh/resume, Home, busy/errors, stale recovery and accessibility |
| `59af100` | Embedded Unicode form font, fitted text and CID escaping |
| `96dcaae` | Stable weapon IDs distinguish same-named variants |
| `a9c4412` | Goblin copper inheritance |
| `ceab18d` | Full roll-table validation and dropped ancestry benefits |
| `96646bd` | Placeholder descriptions replaced by existing talent summaries |
| `3953281` | Repository copies nested input snapshots |
| `c814665` | Seven-day owner cookie; HttpOnly, SameSite and Vercel Secure settings |

The final verification/maintenance commit also contains CI, formatting/lint cleanup,
extra PDF geometry/multi-page tests, updated setup/architecture docs and this record.
Use `git log` for that commit's ID.

## Original repair verification (before database-free conversion)

- 413 Python tests passed with actual PostgreSQL 16 integration enabled; no skips/warnings.
- Eight Node regressions passed (duplicate requests, late responses, stale recovery,
  expired states, tab restore, source locking and PDF request versions).
- Eight Chromium workflows passed: desktop 1440×1000 and phone 390×844, including
  manual creation, keyboard choices/paths, reload/resume, undo, Home/PDF reset,
  failed-start retry, versioned PDF download, sources and separate tabs.
- Full game catalog validation, Ruff lint/format and git diff whitespace checks passed.
- Inspected representative desktop/phone screenshots and a three-page level-10 magic
  character PDF. Renderer tests check Polish text, long notes, effects below descriptions
  and 20 spells across three card pages.
- Added GitHub Actions checks with PostgreSQL, Python, Node and Chromium. The remote
  workflow itself has not run: no push or deployment was performed.

## Path-picker follow-up repairs (2026-10-06)

- `5e52d91`: restore button-like path cards: the whole card label is clickable, selection has the
  existing active-card styling, and native radio controls are visually hidden while
  retaining keyboard and screen-reader behavior. Desktop/phone browser regression checks
  cover clicks in card padding, changing selections and keyboard selection.
- `bb8b00c`: path tooltips now use editable `path_description` JSON fields. All four novice paths
  have original draft flavor descriptions labeled "Opis roboczy"; missing expert/master
  descriptions use a labeled template. No rulebook text or talent-list fallback is used.
  Catalog regressions verify provided, empty and missing descriptions. Desktop/phone
  workflows open every novice tooltip and ensure reading it cannot select a path.
- Path-picker Back now cancels the last advance using a completed-level checkpoint, not
  the current level's entry snapshot. Character, paths and previous choices are preserved;
  advancing again cannot apply benefits twice. The return does not automatically open
  the PDF drawer over the crossroads. Older signed drafts without these checkpoints can
  still go back, but reopen the previous level's entry choices.
  Regressions cover novice/expert/master pickers, repeated Back/Advance, reload, stale
  versions, missing tokens and invalid contexts. No database or state-format bump is needed.
  This fix is in the final follow-up commit; use `git log` for its ID.

Follow-up verification: 428 Python tests (clean Python 3.12), 16 frontend regressions and
eight full-Chromium desktop/phone workflows pass. Catalog validation, Ruff lint/format
and whitespace checks pass. Inspected the path-card layout and mobile description popover.
All three user-reported issues are handled in separate commits; no push/deployment occurred.

## Remaining / separate work

No planned code repairs remain. Independent rulebook/supplement accuracy review,
visual UI redesign and product features remain separate tasks. Cosmetic mobile toolbar
crowding is left for the redesign, not treated as a new layout project here.

Deployment now needs only a stable `SECRET_KEY`; no database URL or schema/cleanup step.
Preview the Vercel deployment before production: no cloud deployment has been verified.
Do not claim the app has been deployed or that all rulebook content has been audited.

## Resumption notes

- Install Python tooling using `pip install -r requirements-dev.txt` into `.venv`.
- Run `.venv/bin/python -m pytest -q`; no database or database credentials are needed.
- Catalog: `.venv/bin/python -m data.validate`; lint: `ruff check .`;
  formatting: `ruff format --check .`.
- Frontend: `npm ci && npm test`; install Chromium using `npx playwright install chromium`;
  workflows: `npm run test:browser`.
- State format is version 4; incompatible saves produce HTTP 410. No automatic migration.
  A stable secret verifies browser-carried state. Home clears the tab's draft and PDF.
- PDF font/appearance integration uses isolated private adapters from the pinned pypdf
  version. Keep the actual-renderer regressions when upgrading that dependency.
- Git add/commit require approved elevated execution in this workspace.
- The isolated PostgreSQL test cluster has been stopped. Disposable reproduction data
  remains at `/private/tmp/sotdl-postgres.8MBqaM` (role `sotdl`, database `postgres`,
  private socket port 55439, no TCP listener). No user database was modified.
- Temporary Chromium cache: `/private/tmp/sotdl-playwright-browsers`; representative
  PDF renderings: `/private/tmp/sotdl-pdf-check.NH8vNT`. These are not committed assets.
- Database-free verification environment and final five-page magic PDF/rendering:
  `/private/tmp/sotdl-db-free-check.AsFQbM`. This disposable Python 3.12 environment uses
  the exact development dependency pins; the existing project `.venv` is unchanged.
