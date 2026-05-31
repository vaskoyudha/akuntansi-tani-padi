"""
database.py
===========
Lapisan persistensi SQLite untuk aplikasi akuntansi usaha tani padi.

Skema:
  users(id, username UNIQUE, password_hash, nama)
  jurnal(id, kode, tanggal, keterangan, tipe)         -- tipe: umum|penyesuaian|penutup
  jurnal_baris(id, jurnal_id, kode_akun, akun, debit, kredit)

Nilai uang disimpan sebagai TEXT (string Decimal) agar presisi tetap terjaga;
SQLite tidak punya tipe Decimal asli.
"""
import sqlite3
from decimal import Decimal

import accounting as acc
import seed_data

D = Decimal

DEFAULT_DB = "tani_padi.db"


# ---------------------------------------------------------------------------
# Koneksi & skema
# ---------------------------------------------------------------------------
def create_connection(path: str = DEFAULT_DB) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_tables(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nama          TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS jurnal (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            kode       TEXT NOT NULL,
            tanggal    TEXT NOT NULL,
            keterangan TEXT,
            tipe       TEXT NOT NULL DEFAULT 'umum'
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS jurnal_baris (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            jurnal_id INTEGER NOT NULL,
            kode_akun TEXT NOT NULL,
            akun      TEXT NOT NULL,
            debit     TEXT NOT NULL DEFAULT '0',
            kredit    TEXT NOT NULL DEFAULT '0',
            FOREIGN KEY (jurnal_id) REFERENCES jurnal(id) ON DELETE CASCADE
        )
        """
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------
def seed_database(conn: sqlite3.Connection) -> None:
    """Masukkan 20 transaksi awal. Idempoten: tidak menggandakan jika sudah ada."""
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM jurnal WHERE tipe = 'umum'")
    if cur.fetchone()[0] > 0:
        return
    for e in seed_data.get_jurnal_seed():
        cur.execute(
            "INSERT INTO jurnal (kode, tanggal, keterangan, tipe) VALUES (?, ?, ?, 'umum')",
            (e["id"], e["tanggal"], e["keterangan"]),
        )
        jid = cur.lastrowid
        for ln in e["lines"]:
            cur.execute(
                "INSERT INTO jurnal_baris (jurnal_id, kode_akun, akun, debit, kredit) "
                "VALUES (?, ?, ?, ?, ?)",
                (jid, ln["kode"], ln["akun"], str(ln["debit"]), str(ln["kredit"])),
            )
    conn.commit()


# ---------------------------------------------------------------------------
# Baca jurnal
# ---------------------------------------------------------------------------
def _baca_jurnal(conn: sqlite3.Connection, tipe: str | None = None) -> list[dict]:
    cur = conn.cursor()
    if tipe:
        cur.execute(
            "SELECT id, kode, tanggal, keterangan, tipe FROM jurnal WHERE tipe = ? "
            "ORDER BY id",
            (tipe,),
        )
    else:
        cur.execute("SELECT id, kode, tanggal, keterangan, tipe FROM jurnal ORDER BY id")
    entries = []
    for jid, kode, tanggal, keterangan, jtipe in cur.fetchall():
        bcur = conn.cursor()
        bcur.execute(
            "SELECT kode_akun, akun, debit, kredit FROM jurnal_baris "
            "WHERE jurnal_id = ? ORDER BY id",
            (jid,),
        )
        lines = [
            {"kode": ka, "akun": ak, "debit": D(d), "kredit": D(k)}
            for ka, ak, d, k in bcur.fetchall()
        ]
        entries.append({
            "db_id": jid,
            "id": kode,
            "tanggal": tanggal,
            "keterangan": keterangan,
            "tipe": jtipe,
            "lines": lines,
        })
    return entries


def get_jurnal_umum(conn: sqlite3.Connection) -> list[dict]:
    """Semua jurnal bertipe 'umum' (termasuk yang ditambah manual user)."""
    return _baca_jurnal(conn, tipe="umum")


def get_semua_jurnal(conn: sqlite3.Connection) -> list[dict]:
    return _baca_jurnal(conn, tipe=None)


# ---------------------------------------------------------------------------
# Tulis jurnal
# ---------------------------------------------------------------------------
def next_kode(conn: sqlite3.Connection) -> str:
    """Kode transaksi berikutnya, format T## berdasarkan jumlah jurnal umum."""
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM jurnal WHERE tipe = 'umum'")
    n = cur.fetchone()[0] + 1
    return f"T{n:02d}"


def insert_jurnal(
    conn: sqlite3.Connection,
    tanggal: str,
    keterangan: str,
    lines: list[dict],
    tipe: str = "umum",
    kode: str | None = None,
) -> int:
    """
    Simpan satu transaksi. Validasi balance dulu (debit==kredit, !=0).
    Raise ValueError bila tidak balance -> tidak ada yang tersimpan.
    """
    entry = {"id": kode or "?", "tanggal": tanggal, "keterangan": keterangan, "lines": lines}
    acc.validasi_entry(entry)  # raise ValueError jika tidak balance

    if kode is None:
        kode = next_kode(conn)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO jurnal (kode, tanggal, keterangan, tipe) VALUES (?, ?, ?, ?)",
        (kode, tanggal, keterangan, tipe),
    )
    jid = cur.lastrowid
    if jid is None:
        raise RuntimeError("Gagal menyimpan jurnal: tidak ada row id.")
    for ln in lines:
        cur.execute(
            "INSERT INTO jurnal_baris (jurnal_id, kode_akun, akun, debit, kredit) "
            "VALUES (?, ?, ?, ?, ?)",
            (jid, ln["kode"], ln["akun"], str(D(ln["debit"])), str(D(ln["kredit"]))),
        )
    conn.commit()
    return jid


def hapus_jurnal(conn: sqlite3.Connection, db_id: int) -> None:
    cur = conn.cursor()
    cur.execute("DELETE FROM jurnal_baris WHERE jurnal_id = ?", (db_id,))
    cur.execute("DELETE FROM jurnal WHERE id = ?", (db_id,))
    conn.commit()


def reset_jurnal(conn: sqlite3.Connection) -> None:
    """Kosongkan semua jurnal lalu seed ulang (untuk tombol reset di UI)."""
    cur = conn.cursor()
    cur.execute("DELETE FROM jurnal_baris")
    cur.execute("DELETE FROM jurnal")
    conn.commit()
    seed_database(conn)
