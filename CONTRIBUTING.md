# Contributing to Cień Władcy Demonów - Generator Bohaterów

Thank you for your interest in contributing. This document gives a short overview of how to get involved.

## How to contribute

**Report bugs or suggest features** — Open an issue and describe the problem or idea. Check existing issues first to
avoid duplicates.

**Submit code changes** — Create a branch (in your fork or directly in this repo if you have access), make your changes,
and open a pull request (PR). Keep PRs focused; one feature or fix per PR is easier to review.

**Improve documentation** — Fixes and clarifications in the README or code are always welcome. Use the `docs:` prefix
in your commit.

**Add or fix tests** — If you add or change behavior, add or update tests. Use the `test:` prefix in commits.

## Project Structure

```
main.py              # Flask routes, wizard state management, API endpoints
models/              # Pydantic data models — the schema for all game data
domain/              # Domain/business logic (actions, backstory, choices, progression, state)
data/                # Data access layer (JSON loading and caching)
utils/utils.py       # Core game logic — dice rolls, hero building, action pipeline
utils/pdf_creator.py # PDF character sheet generation
export/              # PDF export pipeline
data_base/           # Game data as JSON files (ancestry, paths, spells, equipment)
static/js/           # Frontend (wizard.js web components + creation_store.js state manager)
templates/           # Single-page Jinja2 template
tests/               # pytest test suite (11 test files)
```

## Key Concepts

- **AncestryHero** — the mutable Pydantic model representing a character being built (levels 0–10)
- **Action** — a discriminated union of 10 types representing any modification to a hero:
  `AddAttribute | AddProfession | AddLanguage | AddItem | GrantLiteracy | AddTalent | AddSpell | AddTradition | AddReligion | UpdateLanguage`.
  All actions have a `type` field for discrimination.
- **Choice** — a `list[Action]` where the user (or random roll) picks one
- **CreationState** — the server-side wizard state machine (current level, cursor, selections, applied actions)
- **AncestryData** — the Pydantic model for loading ancestry JSON templates

When adding a new action type:
1. Add the model class to `models/action.py` with a `Literal` type field
2. Add it to the `Action` union
3. Handle it in `apply_action()` in `utils/utils.py`
4. If it uses `"any"` placeholder expansion, handle it in `expand_any_to_choices()` and
   `_expand_dynamic_choice_group()` in `utils/utils.py`
5. Add UI label rendering in `wizard.js`

When adding a new ancestry:
1. Create `data_base/ancestry/<name>/<name>.json` following the existing schema
2. Create `data_base/ancestry/<name>/<name>_tables.json` with backstory roll tables
3. Add the backstory roll sequence in the `build_hero()` match/case block
4. Add the ancestry key to `ANCESTRIES` in `main.py`
5. Add the display name and description to `data_base/ancestry/descriptions.json`

When adding a new path:
1. Create `data_base/paths/<tier>/<path_name>.json` with `level_benefits` defining actions and choices per level
2. Path files follow the `LevelBenefit` schema (actions + choices arrays per level)
3. Include a `path_description` field with a short summary — this is shown in the ⓘ tooltip on path cards

When adding or editing spells:
1. Each spell in a tradition JSON has `book_description` and `card_description` fields
2. The `card_description` is shown in the ⓘ tooltip when the spell appears as a choice in the wizard

## Running Tests

```bash
pip install pytest
pytest tests/ -v
```

The test suite covers:
- **test_models.py** — Pydantic model validation, creation, mutation, JSON loading
- **test_utils.py** — dice rolling, attribute/language/profession/item/wealth logic, full hero generation
- **test_pdf.py** — PDF generation, field population verification, all-ancestry PDF generation
- **test_app.py** — Flask route integration tests, manual choice flow
- **test_api.py** — API endpoint tests
- **test_creation_contract.py** — creation workflow contract tests
- **test_creation_state.py** — CreationState state machine tests
- **test_export_boundary.py** — PDF export boundary tests
- **test_spells_json.py** — spell/tradition JSON data validation
- **test_talent_placement.py** — talent placement logic tests

## Commit Message Conventions

We use [Conventional Commits](https://www.conventionalcommits.org/) for clear history.

| Prefix   | Meaning                             |
|:---------|:------------------------------------|
| `feat:`  | A new feature                       |
| `fix:`   | A bug fix                           |
| `perf:`  | A change that improves performance  |
| `chore:` | Maintenance (deps, tooling, config) |
| `docs:`  | Documentation only                  |
| `test:`  | Adding or updating tests            |

Examples:

```
feat: add dwarf ancestry support
fix: correct wealth roll range for Komfort tier
docs: update README with architecture diagram
test: add PDF field verification tests
chore: bump pydantic to 2.x
```
