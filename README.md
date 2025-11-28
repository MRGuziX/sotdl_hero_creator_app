SotDL Hero Creator App

Overview
- A small Python utility that helps generate a Shadow of the Demon Lord (SotDL) character using data-driven tables (JSON). It rolls on ancestry tables and assembles a starter "hero" JSON based on the result.

What this repository contains
- main.py — entry point; rolls results, merges them into a hero template, and writes a new file to output/new_human.json.
- utils/utils.py — helper functions for dice rolling, table lookups, and attribute updates.
- data_base/ — JSON data that drives the generation:
  - ancestry/* — ancestry-specific tables and descriptors (e.g., human, automaton, goblin).
  - spells/* — example spell traditions data.
  - new_hero.json — a base template merged with generated data.

Requirements
- Python 3.11+ recommended (uses typing features like | in type hints)
- No external dependencies required (only Python standard library)

Quick start
1) Clone the repository.
2) Ensure you are on Windows or adjust paths to your platform (Windows-style backslashes are used in code and docs).
3) Create the output directory (the script expects it):
   - Create a folder named output at the project root. Example path:
     C:\Users\Tomasz\PycharmProjects\sotdl_hero_creator_app\output
4) Run the script:
   - From your IDE (e.g., PyCharm), run main.py, or
   - From a terminal (PowerShell) at the project root:
     python .\main.py

What happens when you run it
- The program:
  1. Rolls a d20 using utils.roll_dice.
  2. Pulls a matching entry from the ancestry tables (currently using human in main.py via get_from_ancestry).
  3. Loads the base template from data_base/new_hero.json.
  4. Merges the ancestry description and actions into the template.
  5. Writes the resulting character to output/new_human.json.

Project structure (simplified)
- data_base/
  - ancestry/
    - automaton/
      - automaton.json
      - automaton_tables.json
    - goblin/
      - goblin_tables.json
    - human/
      - human.json
      - human_tables.json
  - spells/
    - fire_tradition.json
    - water_tradition.json
  - new_hero.json
- utils/
  - utils.py
- main.py
- README.md

Usage notes and tips
- Output folder: If output does not exist, main.py will fail when trying to write the result. Create the folder first as described above.
- Switching ancestry: In main.py, the ancestry is currently hard-coded to "human". You can switch it to other available ancestries (e.g., "automaton") provided their data files are available and formatted similarly.
- Randomness: Dice results are random each run. For repeatable results during debugging, you can seed the random module in utils or at the start of main.py.
- Data files: The JSON structure under data_base/ drives the generation rules. If you add new ancestries or tables, mirror the structure found in existing examples.

Development notes
- The utils.update_attributes and add_attribute functions outline how to apply user actions (e.g., attribute gains, languages). Parts of add_attribute related to languages are currently scaffolded and may need completion for full language-learning logic.
- Consider adding minimal tests if you plan to extend the project.

License
- No license file is included. If you intend to distribute or contribute, consider adding a LICENSE file appropriate for your needs.

Disclaimer
- Shadow of the Demon Lord and related terms are the property of their respective owners. This project is a fan-made utility for personal use and learning.
