"""Registro de handlers de render (entry point `deken_worker.handlers`)."""

from __future__ import annotations

from deken_render.selftest import render_selftest
from deken_shared.jobs import JobType
from deken_worker.runtime import Handler

HANDLERS: dict[str, Handler] = {
    JobType.SYSTEM_RENDER_SELFTEST.value: render_selftest,
}
