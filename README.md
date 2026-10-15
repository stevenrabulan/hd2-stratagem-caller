# Stratagem Caller

A companion tool for Helldivers 2. It reads the Stratagem Menu off the screen and lets you call a Stratagem with one key instead of typing its arrow code.

- **Trigger Keys**: press your Call Key, then a digit while the menu is open, to call the Stratagem in that Slot (1 = top of the menu). Codes are read from the screen, so new or temporary Stratagems work without an update.
- **Direct Keys**: one key calls one specific Stratagem (for example PageDown for Reinforce), using a Code you configure by name from [codebook.toml](codebook.toml) or write out yourself.
- **Terminal Key** (in progress): at a Terminal, press your Use Key (`E`), and while the prompt at the bottom centre of the screen reads INTERACT, the Terminal Key (`1` by default) is held back from the game so it no longer switches weapon. The tool then reads the Code on the Terminal's screen and types the directions not yet entered, so you can type some by hand and press `1` to finish. If it cannot read the Code it beeps. While a Code is read, a yellow Key Cap for the Terminal Key followed by ENTER CODE shows right of the Terminal Prompt. Away from a Terminal the key does what it always did.
- **Overlay**: while the tool is ready to act on Trigger Keys (it has seen the menu open), a yellow Key Cap showing each Slot's Trigger Key sits left of that Slot's Icon, in the look of the game's own key hints. Slots on cooldown get one too. When a Trigger Key beeps, that Slot's Key Cap flashes red twice in about 0.6 s (150 ms red, 150 ms normal, twice), each red in step with one of the beep's two short tones; a Slot beyond the end of the menu has no Key Cap, so it only beeps. Pressing the same Trigger Key again restarts the flash and the tones, dropping any tone left over. A heading reading STRATAGEM CALLER READY, in the game's yellow with a soft glow, sits just right of the game's STRATAGEMS header and pulses (about once every 1.2 s) while the Key Caps show. The Key Caps and the heading hide when a Call starts, when you close the menu with the Call Key, when the game loses focus, when you pause, and when the menu closes. Turn it off with `enabled = false` under `[overlay]` in [settings.toml](settings.toml); Trigger Keys work the same either way.

Terms are defined in [GLOSSARY.md](GLOSSARY.md). Design decisions are in [docs/adr](docs/adr).

**Status:** Trigger Keys and Direct Keys are built. The Terminal watch (Use Key, the Terminal Prompt, and the Terminal Key being held back at a Terminal) and the reading and typing of the Code are built and tested on the Terminal fixtures, a Steam screenshot and scripted readings, but have not been confirmed in-game; the Key Cap for the Terminal Key (ENTER CODE, with its red flash) is built and tested on scripted readings and painted onto every Terminal fixture, but not confirmed in-game either. The screen reader is tested against 4K fixtures; sending keys into the game has not been confirmed in a mission yet. The Overlay (Key Caps, their double red flash on a beep, and the pulsing ready heading) is built and tested on its drawing, show/hide rules, flash timing and pulse, but has not been confirmed in-game yet.

## Running

### From the desktop shortcut

Make the shortcut once (and again after moving the repo or rebuilding the virtual environment; it replaces an existing or broken one):

```bash
.venv\Scripts\python.exe tools\make_shortcut.py
```

Then double-click **Stratagem Caller** on the desktop. It opens no terminal window: it runs this repo's `.venv\Scripts\pythonw.exe -m stratagem_caller` from the repo root, so it always runs the current code (nothing is packaged or rebuilt). It runs without administrator rights, so there is no UAC prompt. `tools\make_shortcut.py --dry-run` says what it would make without making it; `--path FILE.lnk` makes the shortcut somewhere else.

- A notification says **Running. Call Key: B** (your Call Key). Startup warnings, such as an untested screen height or the Overlay failing to start, appear as notifications too.
- With no terminal, the other startup lines (Direct Keys, log path, Overlay on or off) and every warning go to `logs/stratagem_caller.log`, along with the full details of anything that goes wrong.
- If an unexpected error ends the tool, the full traceback is written to the log, a **Stratagem Caller stopped: see log** notification appears, and the Tray Icon goes away. Keys go back to the game first.
- **If the game ignores the tool's keys**, the game is probably running as administrator and ignoring keys from a non-elevated program. Right-click the shortcut, choose Properties, then Advanced, and tick **Run as administrator**.
- To quit, use the Tray Icon's **Quit** (below).
- **Only one copy runs at a time** (two would type every Call twice), however it was started. Launching a second copy shows **Stratagem Caller is already running**, beeps once, and exits without touching the keyboard; the first copy carries on. The lock is released when the tool ends, including after a crash or when it is killed, so the next launch starts normally. If the first copy runs as administrator and the second does not, the second is still refused.

### From a terminal

Prints its startup text in the terminal as before and shows the same Tray Icon; leave the terminal open (or use the Tray Icon's Quit to end it):

```bash
.venv\Scripts\python.exe -m stratagem_caller
```

- Press the Call Key, then `1`–`9` or `0` while the menu is open. While the menu is already open the Call starts the moment you press the key. If you press it while the menu is still sliding in, the Call starts as soon as that Slot's Code has been read, which is usually within a quarter of a second or so.
- Two low beeps (and two red flashes of the Key Cap, if the Slot has one) mean that Slot has no Stratagem you can call right now (cooldown, inbound, or empty), or it could not be read in time, or it is beyond the end of the menu.
- **Terminal Key**: each press of the Use Key (`use_key`, `E` by default) makes the tool read the Terminal Prompt, the game's `INTERACT` or `MOVE CURSOR` prompt at the bottom centre of the screen. It gives up if no Terminal Prompt shows within 5 s of the press (the Use Key is also for samples, ammo and pods), and otherwise keeps watching while any Terminal Prompt shows, ending about 1 s after none does, or when the game loses focus, when you pause, or after 120 s. While the prompt reads `INTERACT`, the Terminal Key (`terminal_key`, `1` by default) is swallowed, its key-up too, and the tool reads the Code once, fresh, from the middle of the screen (about 40 ms at 4K) and types the directions that are not yet entered (light grey; the yellow ones are kept by the game) with the Direction Keys at `keystroke_ms` timing, or nothing if all are entered. The Code is read whatever angle the Terminal is seen at, with the pink circle or your hand partly across it, but if any arrow is not clearly there (hidden, cut off, too skewed) it beeps (two low tones, and the Terminal Key's Key Cap flashes red twice, in step with the tones) and types nothing; a shortened Code is never typed. There is no retry: the next press reads afresh. A second press while the first is still being read and typed is held back too (no weapon switch, no second Code). The log says what was read (`Terminal Key: Code LURRDR, 2 entered, typing RRDR`) or why not (`Code unreadable, ...`). One thing it cannot see: an end arrow hidden so completely that nothing of it shows. With the prompt reading `MOVE CURSOR` or absent, or no watch running, the Terminal Key does what it did before: a Trigger Key while the tool is watching the Stratagem Menu (opening the menu with the Call Key wins over a Terminal, so `1` still calls Slot 1), otherwise an ordinary key for the game. The log records the watch starting and ending and each Terminal Key decision. **Key Cap**: while the prompt reads `INTERACT`, the tool also reads the Code four times a second (every 0.25 s; each reading costs about 40 ms at 4K, so about 15% of one core while a Terminal waits), and a yellow Key Cap for the Terminal Key followed by ENTER CODE shows just right of the prompt at its height (about 190 px right of the prompt's box at 4K, clear of everything the Terminal Prompt reader looks at) while a Code is read with directions left to enter. It hides when all are entered, when the Code can no longer be read, when the prompt goes, on focus loss, on pause, while the tool types, and while the Stratagem Menu is being watched (where the key is a Trigger Key); it is drawn only when it changes. When the Terminal Key beeps for want of a Code, the Key Cap flashes red twice in about 0.6 s, appearing for each red step if no Key Cap was up. The log says when it appears and why it goes. The ready heading does not show for it. The Use Key still reaches the game. The two prompt words are matched against templates in `stratagem_caller/assets/`, cut from the fixtures by `tools\make_prompt_templates.py`.
- `Ctrl+Alt+P` pauses and resumes. `Ctrl+C` in the terminal quits.
- **Tray Icon**: while the tool runs, a yellow Key Cap with an up arrow sits in the Windows notification area (it may be under the `^` overflow arrow; drag it out to keep it visible). It is greyed while the tool is paused, and its tooltip says Running or Paused. Right-click it for **Pause** or **Resume** (the same toggle as `Ctrl+Alt+P`, so the icon follows either), **Open log** (opens `logs/stratagem_caller.log` in your default viewer), and **Quit**. Quit and `Ctrl+C` do the same shutdown: the Overlay and the Tray Icon go away and every key goes back to the game. The icon file is [stratagem_caller/assets/stratagem_caller.ico](stratagem_caller/assets/stratagem_caller.ico); `tools\make_icon.py` redraws it from the Overlay's Key Cap drawing.
- `F9` marks something unexpected: it gives a short high beep, writes a `MARK` line to `logs/stratagem_caller.log` with what the tool believed at that moment, and saves the screen regions it read in the last few seconds to `fixtures/raw/marks/`. Press it right after the problem, then share the mark number.
- The Overlay is a click-through window that never takes focus and shows in captures and recordings. Key Caps only appear once the tool has confirmed the menu is open, so they can linger a moment (up to about 0.6 s) after the menu really closes if gunfire was hiding it.
- Keys (including `use_key` and `terminal_key`), timing, the Overlay and Direct Keys are set in [settings.toml](settings.toml).

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
- **At a Terminal, `1` beeps and types nothing.** The Terminal Prompt reads `INTERACT` but the Code could not be read; the log line `Terminal Key: Code unreadable, ...` says why (an arrow hidden by a hand or the pink circle, the Code too skewed, no Code on this step). Press `1` again once it is clear, or type it yourself. To get the weapon switch back, set `terminal_key` in `settings.toml` to a key you do not use. If `1` still switches weapon at a Terminal, check the log for `Terminal watch started` after the Use Key press, and that the screen is 3840×2160 (the prompt is read from fixed positions, tried at that size only; the Code is searched for in the middle of the screen, about half its width and height).
- **The menu opens but the Code isn't typed, or is typed wrong.** Check `[direction_keys]` matches your in-game binds. If only the first direction is lost on a Direct Key, raise `direct_key_pause_ms`. If directions are dropped generally, raise `keystroke_ms`.
- **A Direct Key closes the menu instead of calling.** The menu was open but the tool wasn't watching it (it was paused, the game had lost focus, or the watch hit its 60 s safety limit). Direct Keys skip the Call Key only while the tool is watching a menu you opened with the Call Key; otherwise they press it first and don't look at the screen.
- **No Key Caps or heading appear next to the menu.** Check `[overlay] enabled` is `true` in `settings.toml`, that the startup text says the Overlay is `on`, and that the game is in borderless fullscreen (the Overlay has only been tried over borderless fullscreen). A Key Cap only appears once the tool has seen the menu open; if Trigger Keys do nothing either, see the first item. A warning (a notification, and the terminal if there is one) and a line in `logs/stratagem_caller.log` say if the Overlay failed to start.
- **No ENTER CODE Key Cap at a Terminal.** It shows only while the Terminal Prompt reads `INTERACT` and a Code is read with directions left to enter, so it is not there for a bar, a grid or a Code you have finished. It sits right of the prompt, so check the Overlay is on (see above) and that the log has `Terminal Key Cap shown:` lines after the Use Key press; with none, the Code is not being read (pressing the Terminal Key then beeps and says why in the log). A line `Code reading for the Key Cap failed` means reading stopped for that watch; the Terminal Key itself still works.
- **Nothing is sent to the game at all.** The game may be ignoring synthetic keys from a non-elevated process; try running the terminal as administrator (or, from the desktop shortcut, tick "Run as administrator" on it).
- **Screenshots are 2560×1440 on a 4K monitor, or positions are off by a third.** The process is not DPI-aware. Run `tools\capture_fixtures.py --selftest`; it should print your monitor's true pixel size.
- **Screenshots look washed out or too bright.** HDR. Note it and keep the shots; recognition is meant to rely on shape, not exact colour.
- **Screenshots are black, or show the desktop instead of the game.** The game is in exclusive fullscreen. Switch to borderless.
- **Nothing happens when you press the Call Key in-game.** Check `fixtures/raw/captures.log` after pressing it on the desktop. If it works there but not in-game, the key hook is being blocked while the game is focused; try running the terminal as administrator.
- **The Call Key or Use Key in the script is wrong for you.** Change `CALL_KEY` or `USE_KEY` at the top of `tools/capture_fixtures.py`.
