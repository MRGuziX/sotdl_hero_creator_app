# Repair progress / handoff memory

Updated: 2026-10-06. Branch: `fix-for-the-app`.

## User decisions and scope

- Implement the repair plan in `docs/fix-plan.md`, one focused fix and commit at a time.
- Fix reliability before any UI prototype or visual redesign.
- Production persistence: PostgreSQL (user confirmed). Local development: SQLite.
- Do not provision paid services, deploy, or push without a separate request.
- Preserve unrelated user changes. Never commit secrets.

## Completed and committed

| Commit | Change |
| --- | --- |
| `df84750` | Production secret configuration and safe PDF destinations |
| `7f2148d` | Strict API request validation |
| `2a850c0` | Immutable checkpoints and deterministic undo |
| `ab2d98b` | Atomic choice batches, rollback on failure |
| `7ff6867` | Required paths/equipment block incomplete progression/export |
| `66a9e9b` | Creation service, owned snapshots and atomic version comparisons |
| `270cb9d` | Literacy and language-learning benefits |
| `0d78a85` | Lazy choices, random progression, broken profession keys |
| `ab5d386` | Enabled-supplement filtering in manual/random generation |
| `9d6bb03` | Cached isolated catalog access, validation, embedded path spells |
| `d24e4ff` | Durable SQLite/PostgreSQL adapters and owned creation listing |

The original suite had 246 passing tests, 32 Ruff findings and four PDF warnings.
After persistence: 388 passed, three PostgreSQL tests skipped without configuration.
Separately, all seven persistence tests passed with a real, isolated PostgreSQL cluster,
including concurrent compare-and-swap across independent connections.

## Current uncommitted work

PDF reliability: persisted immutable export snapshots, versioned download routes,
scratch-directory cleanup and atomic publication, API/PDF healing-rate consistency,
spell-effect position and pypdf writer attachment. These changes are not yet committed.
Latest full test run: one existing export-boundary mock fails because it does not create
the output file required by the new atomic export contract; 387 passed, three skipped,
and the four PDF deprecation warnings are gone. Update that test and add regressions
before committing. Healing-rate bonuses also need a focused test.

## Remaining work

1. Finish/test/commit PDF snapshot, concurrency, failure cleanup and layout repairs.
2. Frontend: per-tab refresh recovery, stale-version recovery, request errors/busy state,
   duplicate/late-response prevention, Home/reset, supplement lock, keyboard path selection.
3. Browser coverage at desktop/mobile widths; inspect representative rendered PDFs.
4. CI: full tests, PostgreSQL integration, catalog validation, deterministic generation,
   frontend checks and Ruff. Resolve remaining legacy lint findings.
5. Update architecture/setup documentation and remove placeholder descriptions without
   inventing game rules. Update this record and the plan with final verification.

## Practical resumption notes

- Python: `.venv/bin/python`; lint/formatter: `ruff`; Node is installed.
- Full suite: `.venv/bin/python -m pytest -q`.
- Catalog: `.venv/bin/python -m data.validate`.
- Database: `python -m data.persistence init`; cleanup: `python -m data.persistence cleanup`.
- Set `TEST_DATABASE_URL` to an isolated test database for PostgreSQL integration tests.
- Storage expires seven days after last mutation. State format is version 4; incompatible
  saves produce HTTP 410. Session cookies and a stable `SECRET_KEY` establish ownership.
- Git add/commit require approved elevated execution in this workspace.
- An isolated temporary PostgreSQL cluster is currently running on a Unix socket in
  `/private/tmp/sotdl-postgres.8MBqaM`, port 55439, role `sotdl`, database `postgres`.
  It has no TCP listener. Stop it after verification using `pg_ctl -D
  /private/tmp/sotdl-postgres.8MBqaM/data stop`. This is disposable test data, not a
  user database; do not use production database credentials for tests.
