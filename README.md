# ankiZoo

A gamified [Anki](https://apps.ankiweb.net/) add-on that turns spaced-repetition review into a zoo-building game. Answer cards correctly to earn XP and coins, level up to unlock animals, and spend coins to grow a customizable zoo grid.

## How it works

- **XP & coins** — Every card answered correctly earns XP and a coin. Incorrect answers earn nothing, so streaks matter.
- **Leveling & ranks** — XP required per level grows over time (quadratic curve). Leveling up raises your rank, from Trainee up through Master Naturalist, shown as a badge on Anki's deck list page.
- **Animals** — 30 animals across 7 biomes (Savanna, Arctic, Desert, Forest, Jungle, Ocean, Outback). Rarer/bigger animals unlock at higher levels and cost more coins.
- **Zoo grid** — An 11x11 grid you expand and populate with coins, viewable in its own Zoo window alongside your animal Collection and active Quests.
- **Pomodoro bonus** — An in-reviewer Pomodoro timer awards a loot box (20-100 bonus coins, higher amounts rarer) for completing a focused review session.
- **Daily quests** — Up to three quests per day (e.g. review N cards, learn N new cards, get N in a row correct) rewarding coins or animals.

Animals render as hand-authored pixel-art sprites (idle/blink frames) when available, falling back to procedurally generated pixel art for any animal without custom art yet.

## Project layout

| File | Purpose |
|---|---|
| `__init__.py` | Add-on entry point; registers all hooks |
| `zoo_data.py` | Per-profile JSON persistence (`user_files/zoo_<profile>.json`) |
| `economy.py` | XP/coin awarding on card answer |
| `leveling.py` | XP curve, level/rank calculation |
| `quests.py` | Daily quest generation and tracking |
| `animals.py` | Animal catalog (id, biome, unlock cost/level, palette) |
| `sprite_render.py` / `sprite_templates.py` | Procedural pixel-art fallback renderer |
| `zoo_dialog.py` | Zoo / Collection / Quests window |
| `reviewer_widget.py` | In-reviewer level chip + Pomodoro overlay |
| `deck_browser_widget.py` | Deck-list home page widget (level, rank badge) |
| `pomodoro.py` | Pomodoro timer logic |
| `notify.py` | Toast/notification helper |
| `config.py` / `config.json` | Tunable economy constants (XP/coin rates, loot box odds, etc.) |
| `sprites/` | Hand-authored per-animal sprite art |
| `web/` | HTML/CSS/JS for the zoo grid view |

## Installation

Copy (or symlink) this folder into your Anki add-ons directory as `ankiZoo`:

- **macOS**: `~/Library/Application Support/Anki2/addons21/ankiZoo`
- **Windows**: `%APPDATA%\Anki2\addons21\ankiZoo`
- **Linux**: `~/.local/share/Anki2/addons21/ankiZoo`

Restart Anki. No external dependencies are required.

## Configuration

Edit `config.json` to tune the economy: XP/coins per card, level curve steepness, Pomodoro duration, number of daily quests, tile-expansion costs, and loot box odds/ranges.

## Status

Personal project, under active development. Save data (`user_files/*.json`) is per-profile and gitignored.
