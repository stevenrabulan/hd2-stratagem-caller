# Stratagem Caller

A companion tool for Helldivers 2. It reads the Stratagem Menu off the screen and lets you call a Stratagem with one key instead of typing its arrow code.

- **Trigger Keys**: press your Call Key, then a digit while the menu is open, to call the Stratagem in that Slot (1 = top of the menu). Codes are read from the screen, so new or temporary Stratagems work without an update.
- **Direct Keys**: one key calls one specific Stratagem (for example PageDown for Reinforce), using a Code you configure by name from [codebook.toml](codebook.toml) or write out yourself.
- **Overlay**: while the tool is ready to act on Trigger Keys (it has seen the menu open), a yellow Key Cap showing each Slot's Trigger Key sits left of that Slot's Icon, in the look of the game's own key hints. Slots on cooldown get one too. When a Trigger Key beeps, that Slot's Key Cap flashes red three times in about 0.6 s (the beep sound is the same; a Slot beyond the end of the menu has no Key Cap, so it only beeps). The Key Caps hide when a Call starts, when you close the menu with the Call Key, when the game loses focus, when you pause, and when the menu closes. Turn it off with `enabled = false` under `[overlay]` in [settings.toml](settings.toml); Trigger Keys work the same either way.

Terms are defined in [GLOSSARY.md](GLOSSARY.md). Design decisions are in [docs/adr](docs/adr).

**Status:** Trigger Keys and Direct Keys are built. The screen reader is tested against 4K fixtures; sending keys into the game has not been confirmed in a mission yet. The Overlay (Key Caps, and their red flash on a beep) is built and tested on its drawing, show/hide rules and flash timing, but has not been confirmed in-game yet.

## Running

Start it before or during a mission, and leave the terminal open:

```bash
.venv\Scripts\python.exe -m stratagem_caller
```

- Press the Call Key, then `1`–`9` or `0` while the menu is open. While the menu is already open the Call starts the moment you press the key. If you press it while the menu is still sliding in, the Call starts as soon as that Slot's Code has been read, which is usually within a quarter of a second or so.
- A low beep means that Slot has no Stratagem you can call right now (cooldown, inbound, or empty).
- `Ctrl+Alt+P` pauses and resumes. `Ctrl+C` in the terminal quits.
- `F9` marks something unexpected: it gives a short high beep, writes a `MARK` line to `logs/stratagem_caller.log` with what the tool believed at that moment, and saves the screen regions it read in the last few seconds to `fixtures/raw/marks/`. Press it right after the problem, then share the mark number.
- The Overlay is a click-through window that never takes focus and shows in captures and recordings. Key Caps only appear once the tool has confirmed the menu is open, so they can linger a moment (up to about 0.6 s) after the menu really closes if gunfire was hiding it.
- Keys, timing, the Overlay and Direct Keys are set in [settings.toml](settings.toml).

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

Then play a mission. Each Call Key press saves three screenshots (100, 250 and 500 ms after the press) to `fixtures/raw/`, named `..._pressNNN_100ms.png`. Each Use Key press (`E`) saves six (0.5, 1, 1.5, 2, 3 and 4 s after the press, to cover the walk-up to a Terminal and the Code appearing), named `..._useNNN_0500ms.png`. A held key saves one burst, not one per repeat. Most Use Key bursts will be samples, ammo and pods; ignore them. `F9` saves a single shot, `Ctrl+Alt+Q` quits.

Stratagem Menu shots wanted:

1. Stratagem Menu open, everything available.
2. Stratagem Menu open, some Stratagems on cooldown or inbound.
3. Stratagem Menu open with extra mission Stratagems (Hellbomb, SEAF Artillery, an objective).
4. Stratagem Menu closed.

Terminal shots wanted (play one or two missions and use as many kinds of Terminal as you meet; see `.scratch/terminal-codes/spec.md`):

1. Each kind of Terminal with its Code showing (extraction, upload data log-in, ICBM, SEAF artillery, radar, any other).
2. A Code with some directions entered by hand.
3. A Code right after a wrong direction.
4. A Terminal whose next step is not a Code (digits, grid, dial).
5. The same kind of Terminal from two different approach angles.

Crop the useful frames into `fixtures/terminal/` as PNG, then delete the raw captures (they are large and may show the desktop).

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
- **A Direct Key closes the menu instead of calling.** The menu was open but the tool wasn't watching it (it was paused, the game had lost focus, or the watch hit its 60 s safety limit). Direct Keys skip the Call Key only while the tool is watching a menu you opened with the Call Key; otherwise they press it first and don't look at the screen.
- **No Key Caps appear next to the menu.** Check `[overlay] enabled` is `true` in `settings.toml`, that the startup text says the Overlay is `on`, and that the game is in borderless fullscreen (the Overlay has only been tried over borderless fullscreen). A Key Cap only appears once the tool has seen the menu open; if Trigger Keys do nothing either, see the first item. A warning in the terminal and a line in `logs/stratagem_caller.log` say if the Overlay failed to start.
- **Nothing is sent to the game at all.** The game may be ignoring synthetic keys from a non-elevated process; try running the terminal as administrator.
- **Screenshots are 2560×1440 on a 4K monitor, or positions are off by a third.** The process is not DPI-aware. Run `tools\capture_fixtures.py --selftest`; it should print your monitor's true pixel size.
- **Screenshots look washed out or too bright.** HDR. Note it and keep the shots; recognition is meant to rely on shape, not exact colour.
- **Screenshots are black, or show the desktop instead of the game.** The game is in exclusive fullscreen. Switch to borderless.
- **Nothing happens when you press the Call Key in-game.** Check `fixtures/raw/captures.log` after pressing it on the desktop. If it works there but not in-game, the key hook is being blocked while the game is focused; try running the terminal as administrator.
- **The Call Key or Use Key in the script is wrong for you.** Change `CALL_KEY` or `USE_KEY` at the top of `tools/capture_fixtures.py`.
