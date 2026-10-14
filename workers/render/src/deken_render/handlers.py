"""Registro de handlers de render (entry point `deken_worker.handlers`).

Los handlers de Remotion solo se registran si el motor está disponible en este equipo
(Node, renderer compilado y bundle de composiciones): un worker sin Remotion no
reclama esos trabajos."""

from __future__ import annotations

import logging

from deken_render.remotion import availability, remotion_eval, render_timeline
from deken_render.selftest import render_selftest
from deken_shared.jobs import JobType
from deken_worker.runtime import Handler

HANDLERS: dict[str, Handler] = {
    JobType.SYSTEM_RENDER_SELFTEST.value: render_selftest,
}

_available, _reason = availability()
if _available:
    HANDLERS[JobType.SYSTEM_REMOTION_EVAL.value] = remotion_eval
    HANDLERS[JobType.RENDER_TIMELINE.value] = render_timeline
else:
    logging.getLogger("deken_worker").warning("Remotion no disponible en este worker: %s", _reason)
