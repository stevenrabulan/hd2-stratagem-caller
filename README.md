# Stratagem Caller

A companion tool for Helldivers 2. It reads the Stratagem Menu off the screen and lets you call a Stratagem with one key instead of typing its arrow code.

- **Trigger Keys**: press your Call Key, then a digit while the menu is open, to call the Stratagem in that Slot (1 = top of the menu). Codes are read from the screen, so new or temporary Stratagems work without an update.
- **Direct Keys**: one key calls one specific Stratagem (for example PageDown for Reinforce), using a Code you configure by name from [codebook.toml](codebook.toml) or write out yourself.

Terms are defined in [GLOSSARY.md](GLOSSARY.md). Design decisions are in [docs/adr](docs/adr).

**Status:** Trigger Keys and Direct Keys are built. The screen reader is tested against 4K fixtures; sending keys into the game has not been confirmed in a mission yet. The Overlay is not built.

## Running

Start it before or during a mission, and leave the terminal open:

```bash
.venv\Scripts\python.exe -m stratagem_caller
```

- Press the Call Key, then `1`–`9` or `0` while the menu is open. While the menu is already open the Call starts the moment you press the key. If you press it while the menu is still sliding in, the Call starts as soon as that Slot's Code has been read, which is usually within a quarter of a second or so.
- A low beep means that Slot has no Stratagem you can call right now (cooldown, inbound, or empty).
- `Ctrl+Alt+P` pauses and resumes. `Ctrl+C` in the terminal quits.
- Keys, timing and Direct Keys are set in [settings.toml](settings.toml).

Run the tests with:

```bash
.venv\Scripts\python.exe -m pytest -q
```

**Risk:** the tool only reads screen pixels and sends key presses; it never touches the game process. Arrowhead has not approved macro tools, and Helldivers 2 runs GameGuard anti-cheat. Use at your own risk.

## Setup

Requires Windows and Python 3.11 or newer.

```bash
python -m venv .venv
```

```bash
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Collecting fixtures

The screen reader is developed against real screenshots. To collect them:

```bash
.venv\Scripts\python.exe tools\capture_fixtures.py
```

Then play a mission. Each Call Key press saves three screenshots (100, 250 and 500 ms after the press) to `fixtures/raw/`. `F9` saves a single shot, `Ctrl+Alt+Q` quits. Shots wanted:

1. Stratagem Menu open, everything available.
2. Stratagem Menu open, some Stratagems on cooldown or inbound.
3. Stratagem Menu open with extra mission Stratagems (Hellbomb, SEAF Artillery, an objective).
4. Stratagem Menu closed.

## Reference setup

The tool is built and tested against this setup. If it misbehaves for you, compare yours against it first.

| Setting | Value |
| --- | --- |
| OS | Windows 11 |
| Monitor | Single, 3840×2160 |
| Windows display scaling | 150% (Windows reports 2560×1440 to apps that are not DPI-aware) |
| Game display mode | Borderless fullscreen |
| HDR | On (Windows and in-game) |
| Call Key | `B`, press to toggle |
| Direction Keys | Arrow keys |
| Python | 3.11 |

## Troubleshooting

- **A Trigger Key does nothing and the digit switches weapon.** The tool didn't see a callable Stratagem in the menu. Check the window title in `settings.toml` matches the game's exactly, that the Call Key matches your in-game bind, and that your screen is 3840×2160 (other sizes are untested).
- **The menu opens but the Code isn't typed, or is typed wrong.** Check `[direction_keys]` matches your in-game binds. If only the first direction is lost on a Direct Key, raise `direct_key_pause_ms`. If directions are dropped generally, raise `keystroke_ms`.
- **A Direct Key closes the menu instead of calling.** The menu was already open; Direct Keys always press the Call Key first and don't look at the screen.
- **Nothing is sent to the game at all.** The game may be ignoring synthetic keys from a non-elevated process; try running the terminal as administrator.
- **Screenshots are 2560×1440 on a 4K monitor, or positions are off by a third.** The process is not DPI-aware. Run `tools\capture_fixtures.py --selftest`; it should print your monitor's true pixel size.
- **Screenshots look washed out or too bright.** HDR. Note it and keep the shots; recognition is meant to rely on shape, not exact colour.
- **Screenshots are black, or show the desktop instead of the game.** The game is in exclusive fullscreen. Switch to borderless.
- **Nothing happens when you press the Call Key in-game.** Check `fixtures/raw/captures.log` after pressing it on the desktop. If it works there but not in-game, the key hook is being blocked while the game is focused; try running the terminal as administrator.
- **The Call Key in the script is wrong for you.** Change `CALL_KEY` at the top of `tools/capture_fixtures.py`.
