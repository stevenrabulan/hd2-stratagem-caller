# 04: Remove the Arming Window length setting

**What to build:** The time-limit setting is gone from the settings file and the settings loader, so there is no setting that does nothing. The glossary and README describe the Arming Window as lasting for as long as the tool sees the Stratagem Menu open. See "Settings" and "Watching replaces the time limit" in the spec, and user story 28.

**Blocked by:** 03

**Status:** ready-for-agent

- [ ] The shipped settings file loads and has no Arming Window length setting
- [ ] The loaded settings have no Arming Window length
- [ ] A settings file that still carries the old setting loads without error
- [ ] The glossary definition of Arming Window and of Trigger Key match the new behaviour
- [ ] The README says nothing about a one-second limit
