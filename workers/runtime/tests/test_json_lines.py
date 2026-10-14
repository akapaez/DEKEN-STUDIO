"""Subprocesos que informan con eventos JSON por líneas (renderer Remotion)."""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import pytest

from deken_worker.process import ProcessCancelledError, ProcessTimeoutError, run_json_lines

EMITTER = """
import json, signal, sys, time
def bye(*_):
    print(json.dumps({"event": "cancelled"}), flush=True)
    sys.exit(130)
signal.signal(signal.SIGTERM, bye)
print("ruido que no es JSON", flush=True)
print("{roto", flush=True)
for i in range(int(sys.argv[1])):
    print(json.dumps({"event": "progress", "progress": i / 10}), flush=True)
    time.sleep(float(sys.argv[2]))
print("aviso en stderr", file=sys.stderr, flush=True)
print(json.dumps({"event": "done"}), flush=True)
sys.exit(int(sys.argv[3]))
"""


def _cmd(tmp_path: Path, count: int, delay: float, code: int = 0) -> list[str]:
    script = tmp_path / "emit.py"
    script.write_text(EMITTER)
    return [sys.executable, str(script), str(count), str(delay), str(code)]


def test_collects_events_and_ignores_noise(tmp_path: Path) -> None:
    seen: list[dict[str, object]] = []
    code, events, stderr = run_json_lines(
        _cmd(tmp_path, 3, 0), cwd=tmp_path, timeout_s=30, on_event=seen.append
    )
    assert code == 0
    assert [e["event"] for e in events] == ["progress", "progress", "progress", "done"]
    assert seen == events
    assert "aviso en stderr" in stderr


def test_returns_exit_code(tmp_path: Path) -> None:
    code, events, _ = run_json_lines(_cmd(tmp_path, 0, 0, code=2), cwd=tmp_path, timeout_s=30)
    assert code == 2
    assert events[-1]["event"] == "done"


def test_cancel_sends_sigterm(tmp_path: Path) -> None:
    cancel = threading.Event()
    threading.Timer(0.5, cancel.set).start()
    started = time.monotonic()
    with pytest.raises(ProcessCancelledError):
        run_json_lines(_cmd(tmp_path, 100, 0.1), cwd=tmp_path, timeout_s=30, cancel=cancel)
    assert time.monotonic() - started < 5


def test_timeout_kills_after_grace(tmp_path: Path) -> None:
    stubborn = tmp_path / "stubborn.py"
    stubborn.write_text(
        "import signal, time\nsignal.signal(signal.SIGTERM, signal.SIG_IGN)\ntime.sleep(60)\n"
    )
    started = time.monotonic()
    with pytest.raises(ProcessTimeoutError):
        run_json_lines([sys.executable, str(stubborn)], cwd=tmp_path, timeout_s=0.5, grace_s=1)
    assert time.monotonic() - started < 10
