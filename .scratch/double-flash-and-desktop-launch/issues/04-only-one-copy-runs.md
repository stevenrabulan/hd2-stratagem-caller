# 04: Only one copy of the tool runs at a time

**What to build:** On startup, the tool claims a machine-wide named lock before it hooks the keyboard. If another copy already holds the lock, the new launch shows an "already running" notification, beeps once, and exits without hooking anything. Two copies would otherwise type every Call twice. The OS releases the lock when the process ends, including after a crash, so a later launch starts normally. This lives in a new instance-guard unit, tested for real against the OS with a lock name unique to the test run. See "Single instance" and user stories 28 and 29 in the spec.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] A claim succeeds when nothing holds the lock
- [ ] A second claim fails while the first is held
- [ ] A claim succeeds again after the first is released
- [ ] A second launch shows the "already running" notification, beeps once, and exits before hooking the keyboard
- [ ] A launch after Quit, or after the process was killed, starts normally
- [ ] (player) Checked on Windows: double-clicking the shortcut twice leaves one Tray Icon, and a Call is typed once
