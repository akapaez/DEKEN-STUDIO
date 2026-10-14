"""Registro de handlers de análisis (entry point `deken_worker.handlers`)."""

from __future__ import annotations

from deken_analysis.ingest import media_ingest
from deken_shared.jobs import JobType
from deken_worker.runtime import Handler

HANDLERS: dict[str, Handler] = {
    JobType.MEDIA_INGEST.value: media_ingest,
}
