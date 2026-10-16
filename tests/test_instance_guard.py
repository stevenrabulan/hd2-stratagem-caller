"""The instance guard, tested for real against the OS with a lock name unique to this test run,
so it never meets a running copy of the tool."""

import subprocess
import sys
import uuid
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="a Win32 named mutex")

if sys.platform == "win32":
    from stratagem_caller.instance_guard import LOCK_NAME, claim

ROOT = Path(__file__).resolve().parent.parent


def kill_with_children(process):
    """A virtual environment's python.exe starts the real interpreter as a child: take both."""
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True)
    process.wait(timeout=10)


@pytest.fixture
def name():
    return f"Global\\StratagemCallerTest-{uuid.uuid4()}"


def test_the_tool_claims_a_machine_wide_name():
    assert LOCK_NAME.startswith("Global\\")  # "Local\" would only see this login session


def test_a_claim_succeeds_when_nothing_holds_the_lock(name):
    held = claim(name)
    assert held is not None
    held.release()


def test_a_second_claim_fails_while_the_first_is_held(name):
    first = claim(name)
    try:
        assert claim(name) is None
    finally:
        first.release()


def test_a_claim_succeeds_again_after_the_first_is_released(name):
    claim(name).release()
    again = claim(name)
    assert again is not None
    again.release()


def test_a_failed_claim_does_not_release_the_lock_the_first_holds(name):
    first = claim(name)
    try:
        assert claim(name) is None
        assert claim(name) is None  # still held, not freed by the refused attempts
    finally:
        first.release()


def test_releasing_twice_is_harmless(name):
    held = claim(name)
    held.release()
    held.release()


def test_a_claim_succeeds_after_the_holder_was_killed(name):
    """Another process holds the lock until it is killed, as in a crash: the OS lets go."""
    code = (
        "import sys; from stratagem_caller.instance_guard import claim;"
        f"held = claim({name!r}); print('held' if held else 'refused', flush=True); sys.stdin.read()"
    )
    holder = subprocess.Popen(
        [sys.executable, "-c", code], cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True
    )
    try:
        assert holder.stdout.readline().strip() == "held"
        assert claim(name) is None  # held by the other process
        kill_with_children(holder)
        after = claim(name)
        assert after is not None
        after.release()
    finally:
        kill_with_children(holder)
        holder.stdin.close()
        holder.stdout.close()
