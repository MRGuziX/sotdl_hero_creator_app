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

Database-free conversion is in progress. First change: signed browser-carried full
state/undo history and detached domain transitions; the HTTP/UI switch follows.

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

## Final verification

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

## Remaining / separate work

No planned code repairs remain. Independent rulebook/supplement accuracy review,
visual UI redesign and product features remain separate tasks. Cosmetic mobile toolbar
crowding is left for the redesign, not treated as a new layout project here.

Deployment requires the user to provision PostgreSQL, configure stable `SECRET_KEY`
and `DATABASE_URL`, then run `python -m data.persistence init`. Re-run initialization
when upgrading from the first persistence commit so the export table is present.
Periodically run `python -m data.persistence cleanup`; state and export TTL is seven days.
Do not claim the app has been deployed or that all rulebook content has been audited.

## Resumption notes

- Install Python tooling using `pip install -r requirements-dev.txt` into `.venv`.
- Run `.venv/bin/python -m pytest -q`; set `TEST_DATABASE_URL` to a dedicated test DB
  to include PostgreSQL tests. Never use production credentials for tests.
- Catalog: `.venv/bin/python -m data.validate`; lint: `ruff check .`;
  formatting: `ruff format --check .`.
- Frontend: `npm ci && npm test`; install Chromium using `npx playwright install chromium`;
  workflows: `npm run test:browser`.
- State format is version 4; incompatible saves produce HTTP 410. No automatic migration.
  A stable secret and the signed owner cookie preserve access; Home does not delete saves.
- PDF font/appearance integration uses isolated private adapters from the pinned pypdf
  version. Keep the actual-renderer regressions when upgrading that dependency.
- Git add/commit require approved elevated execution in this workspace.
- The isolated PostgreSQL test cluster has been stopped. Disposable reproduction data
  remains at `/private/tmp/sotdl-postgres.8MBqaM` (role `sotdl`, database `postgres`,
  private socket port 55439, no TCP listener). No user database was modified.
- Temporary Chromium cache: `/private/tmp/sotdl-playwright-browsers`; representative
  PDF renderings: `/private/tmp/sotdl-pdf-check.NH8vNT`. These are not committed assets.
