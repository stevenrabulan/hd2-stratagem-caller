from stratagem_caller.arming import ArmingWindow, Outcome

MENU = {2: "DDUR", 5: "DLRDLR"}


def window():
    return ArmingWindow(started=0.0, length=1.0)


def test_trigger_key_calls_once_two_readings_agree():
    w = window()
    assert w.press(5, now=0.05)
    assert w.offer(MENU, now=0.25) is None  # first sight, not yet confirmed
    assert w.offer(MENU, now=0.32) == Outcome("call", "DLRDLR")


def test_trigger_key_pressed_after_menu_settled_calls_on_next_reading():
    w = window()
    w.offer(MENU, now=0.25)
    w.offer(MENU, now=0.32)
    assert w.press(2, now=0.5)
    assert w.offer(MENU, now=0.57) == Outcome("call", "DDUR")


def test_changing_readings_are_not_trusted():
    w = window()
    w.press(5, now=0.05)
    assert w.offer({5: "DLR"}, now=0.2) is None
    assert w.offer(MENU, now=0.27) is None
    assert w.offer(MENU, now=0.34) == Outcome("call", "DLRDLR")


def test_slot_that_cannot_be_called_beeps():
    w = window()
    w.offer(MENU, now=0.25)
    w.offer(MENU, now=0.32)
    w.press(3, now=0.4)
    assert w.offer(MENU, now=0.5) is None  # give the Slot a moment to appear
    assert w.offer(MENU, now=0.8) == Outcome("beep")


def test_trigger_key_is_handed_back_when_no_menu_was_seen():
    w = window()
    w.press(1, now=0.1)
    assert w.offer({}, now=0.3) is None
    assert w.offer({}, now=0.65) == Outcome("pass")


def test_trigger_key_outside_the_window_is_refused():
    w = window()
    assert not w.press(1, now=1.0)


def test_only_the_first_trigger_key_is_accepted():
    w = window()
    assert w.press(2, now=0.1)
    assert not w.press(5, now=0.2)


def test_window_expires_without_a_trigger_key():
    w = window()
    assert w.offer(MENU, now=0.5) is None
    assert w.offer(MENU, now=1.0) == Outcome("expired")
