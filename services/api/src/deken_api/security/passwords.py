"""Hash de contraseñas con argon2id y política mínima."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

MIN_LENGTH = 12
MAX_LENGTH = 256

_hasher = PasswordHasher()  # Parámetros RFC 9106 (perfil de memoria baja) por defecto.
# Hash de una contraseña aleatoria para igualar tiempos cuando el usuario no existe.
_DUMMY_HASH = _hasher.hash("deken-dummy-password-for-timing-equalisation")


class PasswordPolicyError(ValueError):
    pass


def validate_password(password: str, *, email: str | None = None) -> None:
    if len(password) < MIN_LENGTH:
        raise PasswordPolicyError(f"La contraseña debe tener al menos {MIN_LENGTH} caracteres")
    if len(password) > MAX_LENGTH:
        raise PasswordPolicyError(f"La contraseña no puede superar {MAX_LENGTH} caracteres")
    if password.strip() != password:
        raise PasswordPolicyError("La contraseña no puede empezar ni terminar con espacios")
    if email and password.lower() == email.lower():
        raise PasswordPolicyError("La contraseña no puede ser igual al email")
    if len(set(password)) < 5:
        raise PasswordPolicyError("La contraseña es demasiado repetitiva")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    """Verifica en tiempo similar exista o no el usuario."""
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and (
            password_hash is not None
        )
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)
