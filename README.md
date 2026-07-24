# Cień Władcy Demonów - Generator Bohaterów

## Purpose

A web-based character generator for the Shadow of the Demon Lord RPG (Polish edition: "Cień Władcy Demonów").
Automates the full level 0 character creation process — ancestry selection, backstory rolls, profession assignment,
wealth, equipment, and PDF character sheet generation.

Supported ancestries (core book): Human, Automaton, Goblin, Dwarf, Orc, Changeling.

## How It Works

### Character Creation Flow

1. User selects an **ancestry** and a **mode** (random or manual)
2. The app loads ancestry base stats from JSON data files
3. **Backstory** is rolled on ancestry-specific tables (past, personality, age, body, appearance, etc.)
4. **Professions** are assigned — some grant additional abilities (e.g. literacy)
5. **Wealth** is rolled — determines starting money, backpack contents, and equipment choices
6. **Oddity** is rolled — a random curiosity item
7. **Actions** (attribute bonuses, professions, languages) are applied to the hero
8. **Choices** are either resolved randomly or presented to the user as radio buttons
9. A **PDF character sheet** is generated and displayed in-browser

### Random vs Manual Mode

- **Random mode** (default): all choices are resolved automatically using dice rolls. The PDF is generated immediately.
- **Manual mode**: actions with `"any"` targets (e.g. "add any attribute +1") are expanded into choice groups. The user
  picks from radio buttons in the UI, then confirms to generate the PDF.

## Architecture

```
sotdl_hero_creator_app/
├── main.py                  # Flask routes and app entry point
├── models/                  # Pydantic data models
│   ├── action.py            # Action discriminated union (AddAttribute, AddProfession, etc.)
│   ├── ancestry.py          # AncestryData + GeneralStats (for loading ancestry JSONs)
│   ├── base_hero.py         # AncestryHero — the level 0 character model
│   ├── equipment.py         # Weapon, Armor, Shield, Money, Equipment
│   ├── language.py          # Language (name, can_speak, can_write)
│   ├── spell.py             # Spell, Tradition (for future path progression)
│   ├── tables.py            # RollTableEntry, ProfessionEntry, WealthEntry
│   └── talent.py            # Talent (name, description, level)
├── utils/
│   ├── utils.py             # Core game logic: dice rolling, hero building, action system
│   └── pdf_creator.py       # PDF form-filling using pypdf
├── data_base/               # Game data (JSON files)
│   ├── ancestry/            # Per-ancestry: base stats + roll tables
│   ├── equipment/           # Equipment store, wealth tables, oddities
│   ├── professions/         # Profession roll tables
│   └── spells/              # Spell traditions (fire, water)
├── templates/
│   └── index.html           # Single-page UI (Jinja2 + vanilla JS)
├── static/
│   ├── css/style.css        # Dark-fantasy theme and responsive layout
│   └── js/wizard.js          # Progressive wizard and mobile sheet controls
├── pictures/                # Static assets (logo, background, character art)
└── tests/                   # pytest test suite
    ├── test_models.py       # Pydantic model unit tests
    ├── test_utils.py        # Game logic unit tests
    ├── test_pdf.py          # PDF generation + field verification
    └── test_app.py          # Flask route integration tests
```

### Data Models

All game data flows through **Pydantic models** with full type validation:

- **`AncestryHero`** — the mutable character being built (stats, languages, professions, equipment, etc.)
- **`AncestryData`** — the JSON template loaded from ancestry files (base stats + actions/choices to apply)
- **`Action`** — a discriminated union (`AddAttribute | AddProfession | AddLanguage | AddItem | GrantLiteracy`) that
  represents any modification to a hero. Actions use a `type` field for discrimination.
- **`Choice`** — a list of `Action` options the user (or random roll) picks from

### Action System

The character creation process is driven by an **action/choice pipeline**:

1. Ancestry JSON defines base stats + a list of `actions` (always applied) and `choices` (pick one per group)
2. Backstory table rolls can add more actions/choices
3. Wealth rolls add equipment actions/choices
4. In random mode, choices are resolved via `random.choice()`
5. In manual mode, `"any"` actions are expanded into choice groups for the UI
6. All actions are applied to the hero through `apply_action()`, which dispatches on the `Action` type

## Requirements

- Python 3.12+
- Dependencies: `Flask`, `pypdf`, `pydantic`
- Development tools: `pytest`, `ruff`

### Frontend architecture

The page keeps the existing server-authoritative endpoints and legacy DOM contract, while the
presentation layer is progressively enhanced by `static/css/style.css` and `static/js/wizard.js`.
The stylesheet provides the dark-fantasy theme, responsive desktop split view, mobile bottom-sheet
preview, focus states, and step progress indicators. JavaScript adds keyboard-friendly selection tiles,
progress synchronization, mobile preview toggling, and transient feedback without duplicating game rules.

## Local Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the app
python main.py

# Run tests
pytest tests/ -v

# Run linting
ruff check .
```

## Deployment on Vercel

This app is ready to be deployed on Vercel.

1. Connect your GitHub repository to [Vercel](https://vercel.com/).
2. Vercel will automatically detect the `vercel.json` and `requirements.txt` files.
3. The app uses the `/tmp` directory for PDF generation, which is compatible with Vercel's serverless environment.
4. **Note:** Since Vercel functions are stateless, the "Download Current" button may not work reliably if the function
   instance restarts between the generation and the download. Use the download button immediately after generating.

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
