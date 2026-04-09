# Cień Władcy Demonów - Generator Bohaterów

## Purpose

- For now you can use only ancestries from the main book
- This repository provides a Python utility to automate the character creation process for the Shadow of the Demon
  Lord (SotDL) RPG.
- It leverages data-driven JSON tables to roll on ancestry tables and assemble a starter "hero" character sheet.

## Requirements

- Python 3.11+ recommended (uses typing features like | in type hints)
- No external dependencies required (only Python standard library)

## License Disclaimer

This application is an independent, unofficial fan-made tool created to facilitate gameplay. It is not affiliated with,
supported, sponsored, or officially authorized by Schwalb Entertainment, LLC or Alis Games. "Shadow of the Demon
Lord", "Cień Władcy Demonów", and all associated logos and trademarks are the exclusive property of Schwalb
Entertainment, LLC.

Mixed Licensing Information
The source code for this web application (logic, components, and structure) is open-source and released under the MIT
License. See the LICENSE file in the root directory for full details.

⚠️ Proprietary Assets Exception:
The open-source MIT license DOES NOT apply to the graphical assets, illustrations, official icons, logos, and localized
Polish text/data (translations, game mechanics terminology) found within this repository.

Original game mechanics and world building: ©2015 Schwalb Entertainment, LLC.
Polish localization and specific visual assets: © Alis Games.

These proprietary materials are All Rights Reserved and are hosted in this public repository strictly for the functional
purposes of this application, under the direct and explicit permission of the Polish publisher, Alis Games.

You may not extract, clone, modify, redistribute, sublicense, or use these proprietary image and text assets in any
other projects (commercial or non-commercial) without obtaining separate, written consent from Schwalb Entertainment,
LLC and Alis Games.

## Credits

- Backend and frontend by Tomasz Guzik | [Guzikologia](https://www.youtube.com/@Guzikologia)
- Logo and translation by from [Alis.Games](https://alisgames.pl/pl_PL/)
- RPG game author: [Robert Schwalb](https://schwalbentertainment.com/shadow-of-the-demon-lord/)

## Deployment on Vercel

This app is ready to be deployed on Vercel.

1. Connect your GitHub repository to [Vercel](https://vercel.com/).
2. Vercel will automatically detect the `vercel.json` and `requirements.txt` files.
3. The app uses the `/tmp` directory for PDF generation, which is compatible with Vercel's serverless environment.
4. **Note:** Since Vercel functions are stateless, the "Download Current" button may not work reliably if the function
   instance restarts between the generation and the download. It is recommended to use the download button immediately
   after generating the hero.
