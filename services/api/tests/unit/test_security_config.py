"""Unitarios: contraseñas, tokens, CSRF, RBAC, configuración y claves de almacenamiento."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from pydantic import ValidationError

from deken_api.config import Environment, Settings, load_file_variables
from deken_api.integrations.storage import build_object_key, safe_download_filename
from deken_api.security import passwords
from deken_api.security.rbac import ROLE_PERMISSIONS, Permission, Role, has_permission
from deken_api.security.tokens import (
    csrf_token_for,
    hash_token,
    new_session_token,
    new_worker_token,
)
from deken_api.services.auth import validate_email

SECRET = "x" * 40


@pytest.mark.parametrize(
    ("password", "ok"),
    [
        ("Correcta-Larga-2026", True),
        ("corta", False),
        (" espacios-al-inicio-1", False),
        ("aaaaaaaaaaaaaaa", False),
        ("x" * 257, False),
    ],
)
def test_password_policy(password: str, ok: bool) -> None:
    if ok:
        passwords.validate_password(password)
    else:
        with pytest.raises(passwords.PasswordPolicyError):
            passwords.validate_password(password)


def test_password_cannot_equal_email() -> None:
    with pytest.raises(passwords.PasswordPolicyError):
        passwords.validate_password("persona@deken.es", email="Persona@Deken.es")


def test_password_hash_and_verify() -> None:
    hashed = passwords.hash_password("Correcta-Larga-2026")
    assert hashed.startswith("$argon2id$")
    assert passwords.verify_password(hashed, "Correcta-Larga-2026")
    assert not passwords.verify_password(hashed, "otra")
    assert not passwords.verify_password(None, "Correcta-Larga-2026")
    assert not passwords.verify_password("basura", "x")


def test_tokens_are_random_and_hashed() -> None:
    assert new_session_token() != new_session_token()
    worker = new_worker_token()
    assert worker.startswith("dkw_") and len(worker) > 40
    assert hash_token("a") == hash_token("a") != hash_token("b")
    assert len(hash_token("a")) == 64


def test_csrf_token_is_bound_to_session_and_secret() -> None:
    sid = uuid.uuid4()
    assert csrf_token_for(sid, SECRET) == csrf_token_for(sid, SECRET)
    assert csrf_token_for(sid, SECRET) != csrf_token_for(uuid.uuid4(), SECRET)
    assert csrf_token_for(sid, SECRET) != csrf_token_for(sid, SECRET + "y")


def test_rbac_matrix_invariants() -> None:
    assert ROLE_PERMISSIONS[Role.ADMIN] == frozenset(Permission)
    for role in Role:
        assert has_permission(role, Permission.SYSTEM_READ)
    for role in (Role.EDITOR, Role.REVIEWER, Role.VIEWER):
        for perm in (Permission.USERS_MANAGE, Permission.WORKERS_MANAGE, Permission.AUDIT_READ):
            assert not has_permission(role, perm)
    assert has_permission(Role.EDITOR, Permission.JOBS_MANAGE)
    assert not has_permission(Role.VIEWER, Permission.JOBS_MANAGE)


@pytest.mark.parametrize(
    ("email", "ok"),
    [
        ("Ana@Deken.es", True),
        ("admin@deken.local", True),
        ("sin-arroba.deken.es", False),
        ("a@b", False),
        ("a b@deken.es", False),
    ],
)
def test_email_validation(email: str, ok: bool) -> None:
    if ok:
        assert validate_email(email) == email.lower()
    else:
        with pytest.raises(ValueError, match="Email"):
            validate_email(email)


def test_settings_require_long_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(secret_key="corta")  # type: ignore[arg-type]


def test_settings_production_requires_secure_cookies_and_https() -> None:
    with pytest.raises(ValidationError, match="Secure"):
        Settings(
            secret_key=SECRET,  # type: ignore[arg-type]
            environment=Environment.PRODUCTION,
            cookie_secure=False,
            allowed_origins=["https://studio.deken.es"],
        )
    with pytest.raises(ValidationError, match="HTTPS"):
        Settings(
            secret_key=SECRET,  # type: ignore[arg-type]
            environment=Environment.PRODUCTION,
            allowed_origins=["http://studio.deken.es"],
        )
    prod = Settings(
        secret_key=SECRET,  # type: ignore[arg-type]
        environment=Environment.PRODUCTION,
        allowed_origins=["https://studio.deken.es/"],
    )
    assert prod.secure_cookies is True
    assert prod.allowed_origins == ["https://studio.deken.es"]


def test_settings_origins_from_comma_string(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEKEN_ALLOWED_ORIGINS", "http://a.test, http://b.test/")
    s = Settings(secret_key=SECRET)  # type: ignore[arg-type]
    assert s.allowed_origins == ["http://a.test", "http://b.test"]


def test_ai_configured_requires_provider_and_key() -> None:
    assert not Settings(secret_key=SECRET).ai_configured  # type: ignore[arg-type]
    assert not Settings(secret_key=SECRET, ai_provider="anthropic").ai_configured  # type: ignore[arg-type]
    assert Settings(
        secret_key=SECRET,  # type: ignore[arg-type]
        ai_provider="anthropic",
        ai_api_key="sk-test",  # type: ignore[arg-type]
    ).ai_configured


def test_file_variables_are_loaded(tmp_path: Path) -> None:
    secret_file = tmp_path / "secret"
    secret_file.write_text("valor-desde-fichero\n", encoding="utf-8")
    env = {"DEKEN_SECRET_KEY_FILE": str(secret_file), "DEKEN_OTHER": "x"}
    load_file_variables(env)
    assert env["DEKEN_SECRET_KEY"] == "valor-desde-fichero"
    explicit = {"DEKEN_SECRET_KEY_FILE": str(secret_file), "DEKEN_SECRET_KEY": "explicita"}
    load_file_variables(explicit)
    assert explicit["DEKEN_SECRET_KEY"] == "explicita"


def test_object_keys_never_contain_user_input() -> None:
    job_id = uuid.uuid4()
    key = build_object_key("render", job_id, 2, extension="mp4")
    prefix, jid, attempt, name = key.split("/")
    assert (prefix, jid, attempt) == ("renders", str(job_id), "2")
    assert name.endswith(".mp4") and uuid.UUID(name.removesuffix(".mp4"))
    with pytest.raises(ValueError, match="extensión"):
        build_object_key("render", job_id, extension="../mp4")
    with pytest.raises(ValueError, match="desconocido"):
        build_object_key("../../etc", job_id, extension="mp4")


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("../../etc/passwd", "passwd"),
        ('vídeo "final".mov', "v_deo _final_.mov"),
        ("C:\\Users\\deken\\clip.mp4", "clip.mp4"),
        ("...", "archivo"),
    ],
)
def test_safe_download_filename(name: str, expected: str) -> None:
    assert safe_download_filename(name) == expected
