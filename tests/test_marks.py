import numpy as np

from stratagem_caller.marks import RecentRegions, save_mark


def region(value: int) -> np.ndarray:
    return np.full((4, 4, 3), value, np.uint8)


def test_only_the_most_recent_regions_are_kept():
    recent = RecentRegions(keep=2)
    for when in (1.0, 2.0, 3.0):
        recent.add(when, region(int(when)))
    assert [when for when, _ in recent.snapshot()] == [2.0, 3.0]


def test_a_mark_saves_each_region_named_by_its_age_and_the_one_at_the_mark(tmp_path):
    folder = save_mark(tmp_path, 3, 10.0, [(8.75, region(1)), (9.9, region(2))], region(3))
    assert folder.parent == tmp_path and folder.name.endswith("_mark03")
    names = sorted(p.name for p in folder.iterdir())
    assert names == ["at_mark.png", "before_000.10s.png", "before_001.25s.png"]


def test_a_mark_with_no_region_at_the_mark_saves_the_recent_ones(tmp_path):
    folder = save_mark(tmp_path, 1, 5.0, [(4.0, region(1))], None)
    assert [p.name for p in folder.iterdir()] == ["before_001.00s.png"]
