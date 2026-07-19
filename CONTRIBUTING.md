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
models/          # Pydantic data models — the schema for all game data
utils/utils.py   # Core game logic — dice rolls, hero building, action pipeline
utils/pdf_creator.py  # PDF character sheet generation
data_base/       # Game data as JSON files (ancestry stats, roll tables, equipment)
templates/       # Frontend (single-page Jinja2 + vanilla JS)
tests/           # pytest test suite (models, utils, PDF, integration)
```

## Key Concepts

- **AncestryHero** — the mutable Pydantic model representing a character being built
- **Action** — a discriminated union type (`AddAttribute | AddProfession | AddLanguage | AddItem | GrantLiteracy`)
  representing any modification to a hero. All actions have a `type` field for discrimination.
- **Choice** — a `list[Action]` where the user (or random roll) picks one
- **AncestryData** — the Pydantic model for loading ancestry JSON templates

When adding a new action type:
1. Add the model class to `models/action.py` with a `Literal` type field
2. Add it to the `Action` union
3. Handle it in `apply_action()` in `utils/utils.py`
4. Add UI label translation in `displayChoices()` in `templates/index.html`

When adding a new ancestry:
1. Create `data_base/ancestry/<name>/<name>.json` following the existing schema
2. Create `data_base/ancestry/<name>/<name>_tables.json` with backstory roll tables
3. Add the backstory roll sequence in the `build_hero()` match/case block
4. Add the ancestry key to `ANCESTRIES` in `main.py`
5. Add the display name to `ancestryDisplayNames` in `index.html`

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
