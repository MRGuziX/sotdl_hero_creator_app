# Cień Władcy Demonów - Generator Bohaterów

## Purpose

A web-based character generator for the Shadow of the Demon Lord RPG (Polish edition: "Cień Władcy Demonów").
Supports the full level 0–10 character lifecycle — ancestry selection, backstory rolls, profession assignment,
wealth, equipment, novice/expert/master path progression, magic traditions, spells, and PDF character sheet generation.

Supported ancestries (core book): Human, Automaton, Goblin, Dwarf, Orc, Changeling.

## How It Works

### Character Creation Flow

1. User selects an **ancestry** and a **mode** (random or manual)
2. The app loads ancestry base stats from JSON data files
3. **Backstory** is rolled on ancestry-specific tables (past, personality, age, body, appearance, etc.)
4. **Professions** are assigned — some grant additional abilities (e.g. literacy)
5. **Wealth** is rolled — determines starting money, backpack contents, and equipment choices
6. **Oddity** is rolled — a random curiosity item
7. **Actions** (attribute bonuses, professions, languages, talents, traditions, spells) are applied to the hero
8. **Choices** are either resolved randomly or presented to the user in the step-by-step wizard
9. **Level advancement** (levels 1–10) — the user picks novice/expert/master paths, gains benefits, and resolves
   new choices at each level via a crossroads screen
10. A **PDF character sheet** is generated and displayed in-browser

### UI Features

- **Info tooltips (ⓘ)** on ancestry cards, path cards, talent choices, and spell choices — click to see a
  description popover (bottom-sheet on mobile)
- **Home button** in the header toolbar to return to the main menu at any time
- **Supplement selector** (cog wheel) to enable/disable game supplement sources (e.g. SWD)
- **Responsive design** with three breakpoints (1024px tablet, 768px mid-size, 480px phone) — the PDF preview
  becomes a slide-up drawer on mobile with a floating action button

### Random vs Manual Mode

- **Random mode**: all choices are resolved automatically using dice rolls. Path selection and target level are
  configured upfront, then the PDF is generated immediately.
- **Manual mode**: a step-by-step wizard guides the user through each level. Actions with `"any"` targets
  (e.g. "add any attribute +1", "add any tradition") are expanded into choice groups. The user picks from
  selection tiles in the UI, can rewind choices, and advances level-by-level through a crossroads screen.

### Path Progression

At certain levels, the hero picks a **path** that grants new abilities:
- **Novice paths** (level 1): Magik, Priest, Rogue, Warrior
- **Expert paths** (level 3): 16 paths including Artificer, Cleric, Druid, Fighter, Sorcerer, Wizard, etc.
- **Master paths** (level 7): 27+ paths including Aeromancer, Champion, Chronomancer, Duelist, Hexer, etc.

### Magic System

Paths like Magik and Priest grant **magic traditions** (e.g. Fire, Shadow, Necromancy). When a tradition is learned:
- The hero gains rank 0 spells from that tradition (2 if the hero has the "Sztuczki" talent)
- At higher levels, the hero can learn higher-rank spells from known traditions or discover new traditions

## Architecture

```
sotdl_hero_creator_app/
├── main.py                  # Stateless Flask commands and direct PDF responses
├── config.py                # Development/production state-signing secret
├── models/                  # Pydantic data models
│   ├── action.py            # Action discriminated union (10 types) + Choice, LevelBenefit
│   ├── ancestry.py          # AncestryData + GeneralStats (for loading ancestry JSONs)
│   ├── base_hero.py         # AncestryHero — the mutable character model (levels 0–10)
│   ├── equipment.py         # Weapon, Armor, Shield, Money, Equipment
│   ├── language.py          # Language (name, can_speak, can_write)
│   ├── path.py              # Path model (novice/expert/master path definitions)
│   ├── requests.py          # Strict creation/mutation request envelopes
│   ├── spell.py             # Spell and embedded path-spell data
│   ├── tables.py            # RollTableEntry, ProfessionEntry, WealthEntry
│   └── talent.py            # Talent (name, description, level)
├── domain/                  # Domain/business logic
│   ├── creation_service.py  # Atomic transitions and completion/progression guards
│   ├── creation_state.py    # Versioned state and immutable undo checkpoints
│   ├── state_token.py       # Signed browser-carried character and undo history
│   └── progression.py       # Level progression (benefits_between)
├── data/                    # Data access layer
│   ├── repository.py        # Isolated cached JSON reads and normalization
│   └── validate.py          # Catalog models, references and roll-table validation
├── utils/
│   ├── utils.py             # Core game logic: dice rolling, hero building, action system
│   └── pdf_creator.py       # PDF form-filling using pypdf
├── export/
│   └── pdf.py               # Isolated scratch rendering and atomic publication
├── data_base/               # Game data (JSON files)
│   ├── ancestry/            # Per-ancestry: base stats + roll tables (6 ancestries)
│   ├── equipment/           # Equipment store, wealth tables, oddities
│   ├── paths/               # Path definitions with path_description (4 novice, 16 expert, 27+ master)
│   ├── professions/         # Profession roll tables
│   └── spells/              # 30 spell traditions (fire, shadow, necromancy, etc.)
├── templates/
│   └── index.html           # Single-page UI (Jinja2 template)
├── static/
│   ├── css/style.css        # Dark-fantasy theme and responsive layout
│   └── js/
│       ├── wizard.js        # Web component wizard UI (step shells, path picker, spell UI)
│       └── creation_store.js # Client-side state management and API calls
├── pictures/                # Static assets (logo, background, character art)
└── tests/                   # pytest, Node store regressions, Playwright browser flows
```

### Data Models

All game data flows through **Pydantic models** with full type validation:

- **`AncestryHero`** — the mutable character being built (stats, languages, professions, equipment, talents, spells, etc.)
- **`AncestryData`** — the JSON template loaded from ancestry files (base stats + actions/choices to apply)
- **`Action`** — a discriminated union of 10 types that represents any modification to a hero:
  `AddAttribute | AddProfession | AddLanguage | AddItem | GrantLiteracy | AddTalent | AddSpell | AddTradition | AddReligion | UpdateLanguage`
- **`Choice`** — a `list[Action]` where the user (or random roll) picks one
- **`LevelBenefit`** — actions and choices granted at a specific level
- **`CreationState`** — the server-side wizard state machine tracking current level, cursor, selections, and applied actions

### Action System

The character creation and progression process is driven by an **action/choice pipeline**:

1. Ancestry JSON defines base stats + a list of `actions` (always applied) and `choices` (pick one per group)
2. Backstory table rolls can add more actions/choices
3. Wealth rolls add equipment actions/choices
4. Path definitions add level-specific actions and choices (traditions, spells, talents, attributes)
5. In random mode, choices are resolved via `random.choice()`
6. In manual mode, `"any"` placeholders are expanded into concrete choice groups for the wizard UI
7. Dynamic placeholders like `"known_tradition"` expand based on current hero state (e.g. spells from learned traditions)
8. All actions are applied to the hero through `apply_action()`, which dispatches on the `Action` type
9. Undo restores immutable checkpoints without rolling character details again. Undo is a
   new versioned mutation; failed requests cannot partially modify the browser's snapshot.

## Requirements

- Python 3.12+
- Dependencies: `Flask`, `pypdf`, `pydantic`, `reportlab`, `fonttools`, `itsdangerous`
- Development tools: `pytest`, `ruff`, `PyMuPDF`; Node.js 22+ for frontend/browser tests

### Frontend Architecture

The frontend is a single-page app built with **vanilla JavaScript web components**.
Python processes game rules; the browser carries the signed character state. No database is used:

- **`creation_store.js`** — client-side state manager that communicates with Flask API endpoints
  (`/api/creations/...`). Serializes requests and sends a signed `state_token` with each
  command. Per-tab session storage holds the latest token for reload recovery. Home clears
  that draft and preview; there is no server-side saved-character list. Drafts are temporary:
  download the PDF before closing the tab, clearing browser storage or starting another hero.
  PDF export returns bytes directly. One browser Blob is used for both preview and download,
  and is released when the character changes or the user returns Home.
- **`wizard.js`** — web components (`StepShell`, `PathPicker`, `CrossroadsScreen`, `RandomConfigScreen`, etc.)
  that render the step-by-step wizard UI. Includes spell/tradition display with grouped selections.
- **`style.css`** — dark-fantasy theme, responsive layout (breakpoints at 1024px, 768px, 480px),
  mobile bottom-sheet preview, focus states, and step progress indicators.

## Local Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# Run the app
python main.py

# Run tests
pytest tests/ -v
python -m data.validate

# Run linting
ruff check .
ruff format --check .

# Frontend checks (Node.js 22+)
npm ci
npm test
npx playwright install chromium
npm run test:browser
```

`python main.py` uses an unpredictable development signing secret. To run locally through
the Flask CLI, set `APP_ENV=development`. Browser drafts become invalid when the development
process restarts with a new secret. Set `SECRET_KEY` locally if you need drafts across restarts.
Production imports require `SECRET_KEY` to be set to a stable, randomly generated secret;
configure it in the deployment environment and never commit it to this repository.

## Deployment on Vercel

The flow is **create hero → preview the filled PDF → download that PDF**. Neither Vercel
nor local development requires PostgreSQL, SQLite, `DATABASE_URL`, schema initialization
or a cleanup job. The app does not retain characters or exported PDFs on the server.

1. Connect this repository to [Vercel](https://vercel.com/) with the repository root as
   the project root. The existing `vercel.json` targets the Flask `app` in `main.py`;
   `requirements.txt` contains the runtime dependencies. No frontend build is needed.
2. Set a stable, randomly generated `SECRET_KEY` in the deployment environment (Production
   and Preview as appropriate), and never commit it. This authenticates browser-carried
   state; it is not a database credential. Do not set `APP_ENV=development` in production.
3. Deploy a preview and check UI assets, random/manual creation, reload/undo, PDF preview
   and download. Local tests alone do not certify a Vercel deployment.
4. Merge to your configured production branch only after the preview succeeds and the
   production secret is configured. Vercel's Git integration may deploy immediately.

PDF rendering uses isolated `/tmp` scratch files and removes them on success and failure.
Spell templates omit Photoshop editing-only data, share background resources across pages,
and use lossless compression to keep complete multi-page exports within response limits.
The response contains the actual PDF bytes, not a URL to a previous function instance's file.
Any instance with the same secret can resume a browser-carried token. Tokens are signed,
not encrypted; possession grants access to the character, so do not put tokens in URLs/logs.
Versions are local to a draft: replaying a previous token can branch that draft, not acquire
a global lock. Requests are size-limited, validated and operate on detached snapshots.
State format 4 is retained; invalid/incompatible drafts return HTTP 410. Changing the
signing secret invalidates existing drafts. Earlier database-backed saves are not migrated;
existing databases/files are not modified or deleted by this upgrade.

`.github/workflows/checks.yml` runs lint/format, full catalog validation, the Python suite
(including deterministic generation and database-free transport checks), Node regressions,
and desktop/phone Chromium workflows. Browser tests run with `VERCEL=1` and a signing secret,
without any database or cookie-based character ownership.

The PDF form-font integration is isolated in `utils/pdf_creator.py` and uses pypdf's pinned
font/appearance adapter. Re-run the structural and rendered Unicode regressions when bumping
pypdf. Reviewed path descriptions are retained; missing descriptions list existing talent
names rather than introducing new game rules. Independent rulebook-content review and a
visual UI redesign remain separate work.

## Logging

The app logs every step of character creation to stdout (visible in Vercel admin console):

```
13:41:30 [utils.utils] === get_hero: ancestry=human, is_random=True ===
13:41:30 [utils.utils] Building hero: ancestry=human
13:41:30 [utils.utils]   backstory [past]: Przeszedłeś ciężką chorobę.
13:41:30 [utils.utils]   wealth roll: 7
13:41:30 [utils.utils]   choice group 0: options=[...] -> picked=add_language(any)
13:41:30 [utils.utils]   apply: {'type': 'add_attribute', 'name': 'strength', 'value': 1}
13:41:30 [utils.utils] === Hero complete: Człowiek | STR=11 DEX=10... ===
```

## License Disclaimer

This application is an independent, unofficial fan-made tool. It is not affiliated with, supported, sponsored, or
officially authorized by Schwalb Entertainment, LLC or Alis Games. "Shadow of the Demon Lord", "Cień Władcy Demonów",
and all associated logos and trademarks are the exclusive property of Schwalb Entertainment, LLC.

The source code is open-source under the MIT License. See [LICENSE.md](LICENSE.md) for details.

**Proprietary Assets Exception:** The MIT license does NOT apply to graphical assets, illustrations, official icons,
logos, and localized Polish text/data. These are All Rights Reserved and used with permission from Alis Games.

## Credits

- Backend and frontend by Tomasz Guzik | [Guzikologia](https://www.youtube.com/@Guzikologia)
- Logo and translation by [Alis.Games](https://alisgames.pl/pl_PL/)
- RPG game author: [Robert Schwalb](https://schwalbentertainment.com/shadow-of-the-demon-lord/)
