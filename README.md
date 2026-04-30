# TavernKeeper

A desktop app for TTRPG Dungeon Masters and Players to manage campaigns, characters, notes, and world lore.

## Stack
- **Electron** — Desktop shell (Windows/Mac/Linux)
- **React + Vite** — Frontend UI
- **SQLite** — Local database (stored in your app data folder)

## Development Setup (on your Windows PC)

### Prerequisites
1. Install [Node.js](https://nodejs.org/) (v18 or later)
2. Install [Git](https://git-scm.com/) (optional but recommended)

### Run in dev mode
```bash
cd TavernKeeper-App
npm install
npm run dev
```
This opens the app window with hot-reload (changes appear instantly without restarting).

### Build a distributable .exe
```bash
npm run build
```
Output goes to `dist-app/` — this is the installer you can share.

## Project Structure
```
TavernKeeper-App/
├── electron/
│   ├── main.js          # Electron entry point (window creation)
│   ├── preload.js       # Bridge between Electron and React (window.tk API)
│   ├── database.js      # SQLite setup and migrations
│   └── handlers.js      # All database logic (auth, campaigns, notes, wiki...)
├── src/
│   ├── App.jsx          # Routing
│   ├── context/
│   │   └── AuthContext.jsx   # Login state
│   ├── pages/
│   │   ├── LoginPage.jsx
│   │   ├── RegisterPage.jsx
│   │   ├── CampaignsPage.jsx   # Campaign list + create/join
│   │   └── CampaignPage.jsx    # Full campaign view (DM dashboard, notes, wiki, character)
│   └── index.css        # All styles (dark tavern theme)
└── package.json
```

## Current Features (v0.1)
- [x] User registration (DM or Player)
- [x] Login / logout
- [x] Create campaigns (DM) with auto-generated invite codes
- [x] Join campaigns via invite code (Player)
- [x] DM dashboard with party member list
- [x] Notes (private, shared with players, DM-only)
- [x] World Atlas (wiki pages by category with visibility control)
- [x] Character sheet (editable stats, ability scores, combat stats, notes)

## Roadmap
- [ ] Spellcasting & spell slots
- [ ] Inventory management
- [ ] Announcements & quest board
- [ ] Character portraits
- [ ] Markdown support in notes/wiki
- [ ] System-agnostic mode
- [ ] Mobile app (React Native)
