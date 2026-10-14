"""Handler Remotion del worker: disponibilidad del motor y puerta de licencia (ADR 0005)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

from deken_render import remotion
from deken_render.remotion import RemotionSettings, _license, availability, browser_path
from deken_shared.jobs import ErrorCode
from deken_shared.media import VideoSpec
from deken_worker.runtime import JobError


def _settings(tmp_path: Path, **kw: Any) -> RemotionSettings:
    renderer = tmp_path / "cli.js"
    bundle = tmp_path / "bundle"
    defaults: dict[str, Any] = {
        "node_path": sys.executable,  # cualquier ejecutable existente
        "remotion_renderer": renderer,
        "remotion_bundle_dir": bundle,
        "remotion_browser": None,  # independiente de DEKEN_REMOTION_BROWSER del entorno
    }
    return RemotionSettings(**{**defaults, **kw})


def test_availability_reports_each_missing_piece(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    assert availability(_settings(tmp_path, node_path="no-existe-node")) == (
        False,
        "Node.js no encontrado",
    )
    ok, reason = availability(settings)
    assert not ok and "renderer no compilado" in reason
    settings.remotion_renderer.write_text("// cli")
    ok, reason = availability(settings)
    assert not ok and "bundle" in reason
    settings.remotion_bundle_dir.mkdir()
    (settings.remotion_bundle_dir / "index.html").write_text("<html></html>")
    ok, reason = availability(settings)
    assert not ok and "navegador no instalado" in reason
    ok, reason = availability(_settings(tmp_path, remotion_browser=str(tmp_path / "chrome")))
    assert not ok and "navegador no encontrado" in reason
    # Navegador instalado en el paquete del renderer (pnpm … browser): se descubre solo.
    shell = (
        tmp_path
        / "node_modules/.remotion/chrome-headless-shell/linux64"
        / "chrome-headless-shell-linux64/chrome-headless-shell"
    )
    shell.parent.mkdir(parents=True)
    shell.write_text("#!/bin/sh")
    settings.remotion_renderer.rename(tmp_path / "dist.js")
    (tmp_path / "dist").mkdir()
    renderer = tmp_path / "dist" / "cli.js"
    renderer.write_text("// cli")
    found = _settings(tmp_path, remotion_renderer=renderer)
    assert browser_path(found) == str(shell)
    assert availability(found) == (True, "ok")


def test_license_key_only_travels_in_company_mode(tmp_path: Path) -> None:
    evaluation = _settings(tmp_path, remotion_license_key="clave-secreta")
    assert _license(evaluation) == {"mode": "evaluation"}
    company = _settings(tmp_path, remotion_license_mode="company", remotion_license_key="k-123")
    assert _license(company) == {"mode": "company", "key": "k-123"}
    assert "k-123" not in repr(company)  # SecretStr: nunca en logs


def test_describe_engine_when_unavailable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DEKEN_REMOTION_RENDERER", str(tmp_path / "nada.js"))
    engines = remotion.describe_engine()
    assert engines["remotion"].startswith("no disponible")


def test_production_render_refused_without_company_license(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEKEN_REMOTION_LICENSE_MODE", "evaluation")
    monkeypatch.setattr(remotion, "availability", lambda _s=None: (True, "ok"))
    with pytest.raises(JobError) as info:
        remotion._render(
            None,  # type: ignore[arg-type]  # no se llega a usar: la puerta va antes
            composition="DekenTimeline",
            props={},
            purpose="production",
            spec=VideoSpec(duration_s=1),
            inputs=[],
        )
    assert info.value.code == ErrorCode.REMOTION_LICENSE_REQUIRED
    assert info.value.retryable is False


def test_engine_unavailable_is_retryable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(remotion, "availability", lambda _s=None: (False, "sin Node"))
    with pytest.raises(JobError) as info:
        remotion._render(
            None,  # type: ignore[arg-type]
            composition="DekenEvaluation",
            props={},
            purpose="evaluation",
            spec=VideoSpec(duration_s=1),
            inputs=[],
        )
    assert info.value.code == ErrorCode.ENGINE_UNAVAILABLE
    assert info.value.retryable is True
