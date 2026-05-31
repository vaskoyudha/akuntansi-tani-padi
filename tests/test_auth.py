"""
Test untuk modul autentikasi sederhana (username + password lokal).
Ditulis sebelum implementasi (TDD - fase RED).
"""
import pytest

import database as db
import auth


@pytest.fixture
def conn(tmp_path):
    path = tmp_path / "test_auth.db"
    c = db.create_connection(str(path))
    db.create_tables(c)
    yield c
    c.close()


def test_register_user_baru(conn):
    ok, pesan = auth.register(conn, "petani", "rahasia123", "Pak Tani")
    assert ok is True


def test_password_disimpan_ter_hash(conn):
    auth.register(conn, "petani", "rahasia123", "Pak Tani")
    cur = conn.cursor()
    cur.execute("SELECT password_hash FROM users WHERE username = 'petani'")
    h = cur.fetchone()[0]
    # password asli tidak boleh tersimpan polos
    assert h != "rahasia123"
    assert len(h) > 20


def test_register_username_duplikat_ditolak(conn):
    auth.register(conn, "petani", "rahasia123", "Pak Tani")
    ok, pesan = auth.register(conn, "petani", "lain456", "Lain")
    assert ok is False


def test_login_benar(conn):
    auth.register(conn, "petani", "rahasia123", "Pak Tani")
    ok, user = auth.login(conn, "petani", "rahasia123")
    assert ok is True
    assert user["nama"] == "Pak Tani"


def test_login_password_salah(conn):
    auth.register(conn, "petani", "rahasia123", "Pak Tani")
    ok, user = auth.login(conn, "petani", "salah")
    assert ok is False
    assert user is None


def test_login_user_tidak_ada(conn):
    ok, user = auth.login(conn, "hantu", "apa")
    assert ok is False


def test_seed_user_default(conn):
    auth.seed_default_user(conn)
    ok, user = auth.login(conn, "admin", "admin123")
    assert ok is True


def test_seed_user_default_idempoten(conn):
    auth.seed_default_user(conn)
    auth.seed_default_user(conn)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
    assert cur.fetchone()[0] == 1
