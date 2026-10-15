from stratagem_caller.app import ROOT, App
from stratagem_caller.settings import load


def make_app():
    tones = []
    app = App(load(ROOT / "settings.toml", ROOT / "codebook.toml"), tone=lambda hz, ms: tones.append(hz))
    return app, tones


def test_pausing_and_resuming_each_play_their_beep_and_tell_the_tray_icon():
    app, tones = make_app()
    told = []
    app.on_pause_change = lambda: told.append(app.router.paused)
    app.toggle_pause()
    app.toggle_pause()
    assert told == [True, False]  # the Tray Icon hears it each time, after the state has changed
    assert tones == [440, 880]  # low to pause, high to resume


def test_stop_is_how_quit_from_the_tray_ends_the_tool():
    app, _ = make_app()
    assert not app.quit_requested
    app.stop()
    assert app.quit_requested
