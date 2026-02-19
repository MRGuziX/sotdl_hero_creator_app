# Cień Władcy Demonów - Generator Bohaterów

## Purpose
- For now you can use only ancestries from main book
- This repository provides a Python utility to automate the character creation process for the Shadow of the Demon Lord (SotDL) RPG.
- It leverages data-driven JSON tables to roll on ancestry tables and assemble a starter "hero" character sheet.

Requirements
- Python 3.11+ recommended (uses typing features like | in type hints)
- No external dependencies required (only Python standard library)

Credits
- Backend and frontend by Tomasz Guzik | [Guzikologia](https://www.youtube.com/@Guzikologia)
- Logo and translation by from [Alis.Games](https://alisgames.pl/pl_PL/)
- RPG game author: [Robert Schwalb](https://schwalbentertainment.com/shadow-of-the-demon-lord/)

License
- Shadow of the Demon Lord and related terms are the property of their respective owners. This project is a fan-made utility for personal use and learning.

## Deployment on Vercel
This app is ready to be deployed on Vercel.
1. Connect your GitHub repository to [Vercel](https://vercel.com/).
2. Vercel will automatically detect the `vercel.json` and `requirements.txt` files.
3. The app uses the `/tmp` directory for PDF generation, which is compatible with Vercel's serverless environment.
4. **Note:** Since Vercel functions are stateless, the "Download Current" button may not work reliably if the function instance restarts between the generation and the download. It is recommended to use the download button immediately after generating the hero.
