from stratagem_caller.eventlog import EventLog


def test_lines_are_written_with_a_time_once_the_log_is_closed(tmp_path):
    path = tmp_path / "logs" / "stratagem_caller.log"
    log = EventLog(path)
    log.write("trigger key 2 Slot 2: taken, waiting for Reading; latest Reading: none yet")
    log.write("Slot 2: Call DLRDLR; latest Reading: Slots 1,2")
    log.close()
    first, second = path.read_text(encoding="utf-8").splitlines()
    assert first.endswith("trigger key 2 Slot 2: taken, waiting for Reading; latest Reading: none yet")
    assert second.endswith("Slot 2: Call DLRDLR; latest Reading: Slots 1,2")
    assert first[4] == "-" and first[19] == "."  # 2026-10-12 14:03:22.417
