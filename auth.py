"""
auth.py
=======
Autentikasi sederhana berbasis username + password lokal (SQLite).

Password tidak pernah disimpan polos. Memakai PBKDF2-HMAC-SHA256 dengan salt
acak per user (stdlib `hashlib` + `secrets`), tanpa dependensi eksternal.

Format password_hash:  pbkdf2_sha256$<iterasi>$<salt_hex>$<hash_hex>
"""
import hashlib
import secrets
import sqlite3

ITERASI = 200_000


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------
def hash_password(password: str, salt: bytes | None = None, iterasi: int = ITERASI) -> str:
    if salt is None:
        salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterasi)
    return f"pbkdf2_sha256${iterasi}${salt.hex()}${dk.hex()}"


def verifikasi_password(password: str, stored: str) -> bool:
    try:
        algo, iterasi_s, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        iterasi = int(iterasi_s)
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterasi)
        return secrets.compare_digest(dk.hex(), hash_hex)
    except (ValueError, AttributeError):
        return False


# ---------------------------------------------------------------------------
# Registrasi & login
# ---------------------------------------------------------------------------
def register(conn: sqlite3.Connection, username: str, password: str, nama: str = "") -> tuple[bool, str]:
    username = (username or "").strip()
    if not username or not password:
        return False, "Username dan password wajib diisi."
    if len(password) < 6:
        return False, "Password minimal 6 karakter."
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE username = ?", (username,))
    if cur.fetchone():
        return False, "Username sudah terdaftar."
    cur.execute(
        "INSERT INTO users (username, password_hash, nama) VALUES (?, ?, ?)",
        (username, hash_password(password), nama or username),
    )
    conn.commit()
    return True, "Pendaftaran berhasil."


def login(conn: sqlite3.Connection, username: str, password: str) -> tuple[bool, dict | None]:
    cur = conn.cursor()
    cur.execute(
        "SELECT id, username, password_hash, nama FROM users WHERE username = ?",
        ((username or "").strip(),),
    )
    row = cur.fetchone()
    if not row:
        return False, None
    uid, uname, phash, nama = row
    if verifikasi_password(password, phash):
        return True, {"id": uid, "username": uname, "nama": nama}
    return False, None


def seed_default_user(conn: sqlite3.Connection) -> None:
    """Buat akun default 'admin' / 'admin123' bila belum ada (untuk kemudahan demo)."""
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE username = 'admin'")
    if cur.fetchone():
        return
    register(conn, "admin", "admin123", "Administrator")
