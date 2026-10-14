"""Configuración común: los tests de integración requieren servicios reales.

Sin DEKEN_TEST_DATABASE_URL se omiten (no se sustituyen por simulaciones).
"""

from __future__ import annotations

import os

import pytest


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if os.environ.get("DEKEN_TEST_DATABASE_URL"):
        return
    skip = pytest.mark.skip(reason="DEKEN_TEST_DATABASE_URL no definida")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)
