# ankiZoo — Claude notes

Gamified Anki add-on (zoo-building over spaced repetition). See `README.md` for
the feature overview and per-file architecture table; this file covers working
in the code.

## Dev workflow
- **This directory IS the installed add-on** (`Anki2/addons21/ankiZoo`). Edits
  modify the live add-on directly — there is no build step.
- **To see changes:** restart Anki (or reload the add-on). No hot reload.
  Exception: `web/*.{html,css,js}` are re-read every time the Zoo dialog opens, so
  UI-only edits just need reopening the dialog. Python changes — including the
  JSON payload built in `zoo_dialog._build_payload` — still need a restart.
- **Code cannot run standalone.** Every module imports `aqt` / `anki`, which only
  exist inside Anki's bundled Python. There is no test suite and `python foo.py`
  will fail on import. Verify by running Anki.
- **Headless checks are still possible** (and faster than launching Anki for
  logic changes):
  - Pure-logic modules that only *lazy*-import aqt (e.g. `animals.py` imports
    `aqt.qt` only inside terrain fns) can be unit-tested by copying them + their
    non-aqt deps (`sprite_render.py`, `sprite_templates.py`) into a throwaway
    package with an empty `__init__.py`, then importing there (the real
    `__init__.py` imports aqt at load).
  - No JS engine (node/jsc) is installed. Verify `web/zoo.js` geometry by porting
    it to Python and asserting, then render the assembled DOM + `zoo.css` via
    `qlmanage -t file.html` (Quick Look renders CSS but **not** JS — pre-build the
    HTML).
- No external dependencies — stdlib + `aqt` only.

## Entry point
`__init__.py` calls `register_hooks()` on `economy`, `deck_browser_widget`, and
`reviewer_widget`. New hook-registering modules must be wired in there too.

## State & persistence (`zoo_data.py`)
- Per-profile JSON at `user_files/zoo_<profile>.json` (gitignored).
- Access via the `get_zoo_data()` singleton; it's reset on `profile_did_open`.
- `ZooState` is a dataclass; `_load()` filters unknown keys, so adding a field is
  safe but **old saves won't have it** — give every field a default.
- `_migrate()` runs one-time save fixups. Two invariants live here:
  - `pretree_animals`: animals owned before the skill tree are grandfathered so
    they don't drain the skill-point budget.
  - Anything in `owned_animals` must also be in `unlocked_animals`.

## Gotchas
- **Two-step animal ownership:** unlock in the skill tree (skill points) →
  `unlocked_animals`; then buy with coins → `owned_animals` (placeable). Don't
  conflate the two lists.
- `config.json` holds all tunable economy constants (rates, curve, loot-box odds,
  widget colors). Prefer adding knobs there over hardcoding.
