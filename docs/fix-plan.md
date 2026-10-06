# Codebase repair plan

Status: code repairs implemented and locally verified on 2026-10-06. Completed commits,
test evidence and deployment requirements are recorded in [repair-progress.md](repair-progress.md).
Visual redesign, independent rulebook accuracy review and deployment are separate work.

Superseding decision: the user requested database-free create → preview → download on
2026-10-06. See [db-free-plan.md](db-free-plan.md); database persistence and global
compare-and-swap requirements below describe the original repair architecture only.

## Objective and scope

Make character creation secure, deterministic under undo, atomic under failed or concurrent
requests, and recoverable across refreshes and supported deployments. Repair existing UI
behavior before starting a visual redesign.

Keep the existing Polish interface, JSON game content, character progression, and PDF output.
Make changes in focused increments with regression coverage. Preserve valid character creation
behavior while deliberately rejecting incomplete progression and malformed requests.

The review baseline was 246 passing tests, 32 Ruff findings, and four PDF deprecation warnings.
Four of 200 sampled level-10 random builds failed. These are review observations, not production
failure-rate estimates. Browser layout and rulebook accuracy still require separate validation.

## 1. Secure session configuration and validate requests

Primary files: `main.py`, request models under `models/`, API tests, deployment documentation.

- Require an environment-provided secret outside an explicit development/test configuration.
  Remove the publicly known fallback from production execution.
- Validate session identifiers as server-generated identifiers before using them in a filename.
  Enforce that resolved PDF destinations remain inside the configured output directory.
- Introduce request models for creation, choices, paths, advancement, rewind, and equipment.
  Validate object shape, list element types, level bounds, source IDs, and catalog references.
- Return consistent JSON errors for invalid requests without changing character state.

Acceptance: production startup fails clearly without its secret; invalid identifiers cannot
read or overwrite PDFs outside the output directory; malformed payloads return a defined 4xx
JSON response instead of an unhandled exception. Legitimate sessions remain isolated.

## 2. Make undo deterministic

Primary files: `domain/creation_state.py`, a creation service under `domain/`, `main.py`.

- Capture the original resolved baseline and store immutable checkpoints before each state
  transition. Each checkpoint includes the hero, choices and cursor, path selections, equipment,
  selections, and completion metadata, but excludes checkpoint history to avoid recursion.
- Restore checkpoints for choice and level rewind instead of calling `get_hero()` again.
  Random outcomes already recorded in a checkpoint must not be rolled again during restoration.
- Define level rewind as returning to the beginning of the requested level, with choices and
  path/equipment decisions for that level available again. Invalidate later checkpoints.
- Apply deterministic level benefits once and keep `hero.level` equal to `current_level`.
- Keep the concurrency version monotonic: undo is a new mutation, not a restoration of an old
  version number. Version the serialized checkpoint format explicitly.

Acceptance: undo preserves unrelated backstory, money, professions, and equipment; health and
talents do not accumulate from repeated rewind; level and choice rewind work at levels 0, 1,
3, and 7, including spell choices and a second Expert path. Restoration performs no random rolls.

## 3. Centralize transitions and make mutations atomic

Primary files: creation service, `domain/creation_state.py`, `main.py`, creation API tests.

- Move creation operations out of routes into a service that accepts typed requests and returns
  a new state or a defined error. Routes handle HTTP concerns and session ownership.
- Apply choice batches to a deep copy. Validate successive groups against that working copy,
  including newly inserted spell choices; publish nothing unless the complete batch succeeds.
- Define one completion predicate covering choices, required paths, and required equipment.
  Use it for advancement and finalization, including server-side checks for each mode.
- Make owner checks, expected-version comparison, and state replacement one atomic operation.
  Use a per-creation lock for the current single-process store; require an atomic conditional
  update or transaction in the shared store introduced in phase 5.
- Give each successful transition one version increment and checkpoint. Errors preserve the
  entire state, history, and version. Never return a live mutable repository object to routes.

Acceptance: a valid selection followed by an invalid one leaves the state unchanged; missing
paths or required equipment block progression/export; two requests for the same version yield
one success and one conflict; owners cannot read or modify another session's creations.

## 4. Repair game-data and choice resolution

Primary files: `utils/utils.py`, `data/repository.py`, action models, JSON data, data tests.

- Correct Infiltrator's invalid profession key and validate all profession, tradition, spell,
  path, and equipment references across the catalogs. Distinguish stable IDs from display text.
- Retain original choice definitions and expand them when they become active. Preserve valid
  spell alternatives when a tradition is already known. Define explicit behavior for exhausted
  groups; never submit unresolved placeholders or select randomly from an empty list.
- Handle literacy and language-update placeholders explicitly. Learning a new language with
  writing proficiency must add the language with the requested capability.
- Apply enabled-source filtering throughout manual and random generation, including automatic
  path picks, traditions, spells, and server-side validation of user selections.
- Make supplement changes consistent with a creation's captured settings. For now, lock those
  settings during an active creation and explain how to change them for a new character.
- Route production data access through one repository with consistent normalization and
  validation; remove duplicate loaders once their callers are migrated.

Acceptance: known crash cases, including random seeds 2 and 116 in the reviewed environment,
have explicit regression tests; broader deterministic generation samples complete; PG-only
creations contain no SWD content; literacy benefits survive the action pipeline. A catalog-wide
validation check catches broken references before serving requests.

## 5. Add persistence and refresh recovery

Primary files: a creation repository, creation service, `static/js/creation_store.js`, configuration.

- Store creations by their own ID, with a separate session-owner association. Starting a second
  creation must not replace the first. Persist checkpoint history with the creation.
- Implement serialized load/save, atomic version updates, expiration, and schema compatibility
  handling. Define an actionable response for expired or incompatible creations.
- Add a session-owned creation listing/resume API. Recover the active creation on page load;
  use a per-tab active ID so tabs can work on separate characters.
- Restore source settings from the creation. Recover from stale-version responses by loading
  authoritative state and informing the user; do not silently repeat a mutation.

Deployment decision: use the documented Vercel deployment as the planning assumption. It needs
shared storage accessible to every instance; process memory or local SQLite does not satisfy
that requirement. Build the repository contract and local/test adapter first. Choose and
configure the production storage service before enabling the deployment. Provisioning services,
incurring costs, and deploying are separate actions from these code changes.

Resolved: the user selected PostgreSQL. Both production PostgreSQL and local SQLite adapters
are implemented; PostgreSQL ownership, snapshots and atomicity were tested against a real
isolated server. Provisioning/configuration and deployment have not been performed.

Acceptance: characters survive page refresh and application restart against the persistent
adapter; independent instances see the same state; two tabs can create separate characters;
ownership, expiration, and atomic conflict handling work across repository connections.

## 6. Make PDF export reliable

Primary files: `export/pdf.py`, `utils/pdf_creator.py`, export routes, PDF tests.

- Export an immutable, fully validated character snapshot through the existing export boundary.
- Use unique per-export scratch files, clean them up on success and failure, and publish completed
  output atomically. Associate the artifact with a creation and version rather than one shared
  session filename.
- Ensure downloads work on the selected deployment: use shared artifact storage or regenerate
  from the persisted snapshot when an artifact is not available locally.
- Make derived statistics consistent between the API and PDF, including healing rate.
- Check spell-card effects against the actual description bottom, verify long-content layout,
  and repair the deprecated page-merging usage identified by the test warnings.

Acceptance: overlapping exports do not mix or corrupt files; failed exports leave no abandoned
scratch files; downloads retrieve the requested character version; multi-page spell output and
representative long cards render correctly. Verify layout in an actual PDF viewer.

## 7. Repair existing frontend behavior

Primary files: `static/js/creation_store.js`, `static/js/wizard.js`, `templates/index.html`.

- Centralize Home/reset navigation, including wizard mode, screen, active state, and PDF preview.
- Add a shared request/error mechanism and visible busy state. Catch failures from creation,
  path selection, equipment, advance, rewind, and PDF actions.
- Prevent overlapping mutations and duplicate PDF requests; distinguish recovery from retry.
  Suppress late responses belonging to a previous creation or reset operation.
- Make path choices keyboard accessible using native controls, preserve focus after rendering,
  and give information buttons meaningful accessible labels.
- Expose resume, expiration, and source-lock behavior through the current UI.

Acceptance: Home returns to the main menu; failures are visible and recoverable; keyboard users
can complete creation; repeated clicks do not duplicate actions. Verify these behaviors in a
browser at desktop and phone widths without introducing the planned visual redesign.

## 8. Complete verification and documentation

- Run the existing suite plus targeted regressions for every fixed issue. Add browser workflow
  coverage for creation, reload/resume, path selection, undo, error recovery, and export.
- Require full game-data validation and a deterministic generation sample in CI.
- Resolve Ruff findings and update README/CONTRIBUTING to describe the actual architecture,
  development dependency installation, secrets, storage, cleanup, and deployment requirements.
- Replace placeholder path descriptions with reviewed content; avoid inventing game rules.
- Document state/schema compatibility and any required migration. Validate production behavior
  against the selected shared-storage adapter before considering deployment ready.

Acceptance: automated checks pass, browser/PDF checks are recorded, and setup instructions are
reproducible. No unresolved security, state-corruption, or generation-crash findings remain.

## Implementation sequence and redesign gate

Implement phases in the order above, using focused commits or PRs for independently reviewable
changes. Add each bug's reproduction with its fix and keep the suite passing between phases.
Test repository ownership and atomicity when persistence is introduced, not only against mocks.

Start the visual UI prototype after these acceptance criteria are met. That later work can add
an HTML character summary, richer navigation, and improved presentation on top of reliable
creation and resume behavior. Character naming and other product features belong to that
separate phase.
