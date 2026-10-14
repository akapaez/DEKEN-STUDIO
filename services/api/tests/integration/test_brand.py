"""Sprint 1 — Recursos de marca (S1-06): logos y tipografías analizados de verdad.

Los logos y la tipografía son SINTÉTICOS (franjas de tinta plana y un glifo generado con
fontTools); no son los ficheros oficiales de DEKEN.
"""

from __future__ import annotations

import io
from pathlib import Path

import httpx
import pytest
from PIL import Image

from deken_api.security.rbac import Role
from deken_api.testing import (
    ApiClient,
    ClientFactory,
    UserFactory,
    synthetic_font,
    synthetic_logo,
    upload_brand,
)

pytestmark = [pytest.mark.integration]

GREEN = "#76B82A"
GREY = "#383E42"
WHITE = "#FFFFFF"


async def test_logo_is_measured_not_trusted(admin_client: ApiClient, tmp_path: Path) -> None:
    path = synthetic_logo(tmp_path / "DEKEN-VERDE.png", width=1040, height=200, inks=[(GREEN, 1.0)])
    response = await upload_brand(admin_client, path, name="DEKEN verde (sintético)")
    assert response.status_code == 200, response.text
    logo = response.json()
    assert logo["status"] == "ready"
    assert (logo["width"], logo["height"], logo["aspect_ratio"]) == (1040, 200, 5.2)
    assert logo["family"] == "DEKEN"
    assert logo["has_alpha"] is True
    assert logo["declared_color"] == "verde"
    assert (logo["measured_color_name"], logo["measured_color_hex"]) == ("verde", GREEN)
    assert logo["color_mismatch"] is False
    # Verde sobre blanco solo da 2,42:1 → se recomienda fondo oscuro.
    assert logo["recommended_background"] == "dark"
    assert logo["analysis"]["warnings"] == []

    async with httpx.AsyncClient() as http:
        preview = await http.get(logo["preview_url"])
    assert preview.status_code == 200
    image = Image.open(io.BytesIO(preview.content))
    assert image.format == "PNG" and max(image.size) <= 512
    assert abs(image.size[0] / image.size[1] - 5.2) < 0.05  # vista previa sin deformar

    download = await admin_client.get(f"/api/v1/brand/assets/{logo['id']}/download-url")
    assert download.status_code == 200
    assert download.json()["filename"] == "DEKEN-VERDE.png"


async def test_swapped_file_name_is_flagged(admin_client: ApiClient, tmp_path: Path) -> None:
    # Caso real del kit: el fichero "BLANCO" contiene en realidad la tinta gris.
    path = synthetic_logo(
        tmp_path / "GRUPO-DEKEN-HORIZONTAL-BLANCO.png", width=2200, height=200, inks=[(GREY, 1.0)]
    )
    logo = (await upload_brand(admin_client, path)).json()
    assert logo["family"] == "GRUPO-DEKEN-HORIZONTAL"
    assert logo["declared_color"] == "blanco"
    assert logo["measured_color_name"] == "gris"
    assert logo["color_mismatch"] is True
    assert logo["recommended_background"] == "light"
    assert any("no coincide" in w for w in logo["analysis"]["warnings"])

    fixed = await admin_client.patch(
        f"/api/v1/brand/assets/{logo['id']}",
        json={"declared_color": "gris", "usage_background": "light"},
    )
    assert fixed.status_code == 200
    assert fixed.json()["color_mismatch"] is False
    assert fixed.json()["usage_background"] == "light"
    audit = (await admin_client.get("/api/v1/audit", params={"action": "brand.update"})).json()
    assert audit["items"][0]["details"] == {"usage_background": "light", "declared_color": "gris"}


async def test_two_ink_logo_and_missing_alpha(admin_client: ApiClient, tmp_path: Path) -> None:
    two = synthetic_logo(
        tmp_path / "GD-VERDE-GRIS.png", width=260, height=200, inks=[(GREEN, 0.6), (GREY, 0.4)]
    )
    logo = (await upload_brand(admin_client, two)).json()
    assert logo["family"] == "GD"
    assert logo["measured_color_name"] == "verde-gris"
    assert logo["declared_color"] == "verde-gris"
    assert logo["recommended_background"] == "light"

    flat = synthetic_logo(
        tmp_path / "DEKEN-GRIS.png", width=1040, height=200, inks=[(GREY, 1.0)], alpha=False
    )
    opaque = (await upload_brand(admin_client, flat)).json()
    assert opaque["has_alpha"] is False
    assert "El logo no tiene transparencia" in opaque["analysis"]["warnings"]


async def test_font_upload(admin_client: ApiClient, tmp_path: Path) -> None:
    path = synthetic_font(tmp_path / "Sintetica-Black.ttf")
    response = await upload_brand(admin_client, path, kind="font", name="Tipografía de prueba")
    assert response.status_code == 200, response.text
    font = response.json()
    assert font["status"] == "ready"
    assert (font["font_family"], font["font_style"], font["font_weight"]) == (
        "Sintetica Prueba",
        "Black",
        900,
    )
    assert font["preview_url"] is None
    listed = (await admin_client.get("/api/v1/brand/assets", params={"kind": "font"})).json()
    assert [f["id"] for f in listed] == [font["id"]]


async def test_invalid_brand_files(admin_client: ApiClient, tmp_path: Path) -> None:
    jpeg = tmp_path / "DEKEN.jpg"
    Image.new("RGB", (520, 100), GREEN).save(jpeg)
    refused = await upload_brand(admin_client, jpeg)
    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "unsupported_format"

    fake = tmp_path / "DEKEN-VERDE.png"
    fake.write_text("esto no es una imagen")
    rejected = await upload_brand(admin_client, fake)
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert "no es válida" in rejected.json()["status_reason"]
    assert rejected.json()["preview_url"] is None
    # El fichero rechazado se borra del almacenamiento y no aparece en la galería.
    download = await admin_client.get(f"/api/v1/brand/assets/{rejected.json()['id']}/download-url")
    assert download.status_code == 409
    assert (await admin_client.get("/api/v1/brand/assets")).json() == []

    transparent = tmp_path / "vacio.png"
    Image.new("RGBA", (200, 100), (0, 0, 0, 0)).save(transparent)
    empty = (await upload_brand(admin_client, transparent)).json()
    assert empty["status"] == "rejected"

    font = tmp_path / "falsa.ttf"
    font.write_bytes(b"\x00\x01\x00\x00" + b"\x00" * 64)
    assert (await upload_brand(admin_client, font, kind="font")).json()["status"] == "rejected"


async def test_brand_permissions_and_archive(
    admin_client: ApiClient, client_factory: ClientFactory, make_user: UserFactory, tmp_path: Path
) -> None:
    logo = (
        await upload_brand(
            admin_client,
            synthetic_logo(
                tmp_path / "DEKEN-BLANCO.png", width=1040, height=200, inks=[(WHITE, 1)]
            ),
        )
    ).json()
    assert logo["recommended_background"] == "dark"

    editor = await make_user(Role.EDITOR)
    client = await client_factory()
    await client.login(editor.email)
    assert (await client.get("/api/v1/brand/assets")).status_code == 200
    denied = await upload_brand(
        client, synthetic_logo(tmp_path / "otro.png", width=100, height=100, inks=[(GREEN, 1)])
    )
    assert denied.status_code == 403
    assert (
        await client.patch(f"/api/v1/brand/assets/{logo['id']}", json={"name": "x"})
    ).status_code == 403

    archived = await admin_client.post(f"/api/v1/brand/assets/{logo['id']}/archive")
    assert archived.status_code == 200
    assert (await admin_client.get("/api/v1/brand/assets")).json() == []
