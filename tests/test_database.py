"""
Test untuk lapisan database SQLite.
Ditulis sebelum implementasi (TDD - fase RED).
"""
from decimal import Decimal

import pytest

import database as db
import accounting as acc

D = Decimal


@pytest.fixture
def conn(tmp_path):
    path = tmp_path / "test.db"
    c = db.create_connection(str(path))
    db.create_tables(c)
    yield c
    c.close()


# ---------------------------------------------------------------------------
# Tabel & seed
# ---------------------------------------------------------------------------
def test_create_tables_membuat_tabel(conn):
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tabel = {r[0] for r in cur.fetchall()}
    assert {"users", "jurnal", "jurnal_baris"} <= tabel


def test_seed_memasukkan_20_transaksi(conn):
    db.seed_database(conn)
    jurnal = db.get_jurnal_umum(conn)
    assert len(jurnal) == 20


def test_seed_idempoten(conn):
    db.seed_database(conn)
    db.seed_database(conn)  # panggil dua kali tidak menggandakan
    jurnal = db.get_jurnal_umum(conn)
    assert len(jurnal) == 20


# ---------------------------------------------------------------------------
# Roundtrip: data dari DB harus identik dgn engine seed
# ---------------------------------------------------------------------------
def test_roundtrip_balance_dan_angka(conn):
    db.seed_database(conn)
    jurnal = db.get_jurnal_umum(conn)
    td, tk = acc.total_jurnal(jurnal)
    assert td == tk == D("52500000")
    lr = acc.laba_rugi(jurnal + acc.get_jurnal_penyesuaian())
    assert lr["laba_bersih"] == D("11500000")


def test_baris_jurnal_pakai_decimal(conn):
    db.seed_database(conn)
    jurnal = db.get_jurnal_umum(conn)
    for e in jurnal:
        for ln in e["lines"]:
            assert isinstance(ln["debit"], Decimal)
            assert isinstance(ln["kredit"], Decimal)


# ---------------------------------------------------------------------------
# Insert manual
# ---------------------------------------------------------------------------
def test_insert_jurnal_manual(conn):
    db.seed_database(conn)
    lines = [
        {"kode": "111", "akun": "Kas", "debit": D("250000"), "kredit": D("0")},
        {"kode": "411", "akun": "Pendapatan Penjualan Gabah", "debit": D("0"), "kredit": D("250000")},
    ]
    db.insert_jurnal(conn, "2025-05-01", "Penjualan tambahan tunai", lines)
    jurnal = db.get_jurnal_umum(conn)
    assert len(jurnal) == 21


def test_insert_jurnal_tidak_balance_ditolak(conn):
    db.seed_database(conn)
    lines = [
        {"kode": "111", "akun": "Kas", "debit": D("100"), "kredit": D("0")},
        {"kode": "411", "akun": "Pendapatan Penjualan Gabah", "debit": D("0"), "kredit": D("90")},
    ]
    with pytest.raises(ValueError):
        db.insert_jurnal(conn, "2025-05-01", "tidak balance", lines)
    # tidak ada yang tersimpan
    assert len(db.get_jurnal_umum(conn)) == 20


def test_next_kode(conn):
    db.seed_database(conn)
    assert db.next_kode(conn) == "T21"


# ---------------------------------------------------------------------------
# Hapus jurnal
# ---------------------------------------------------------------------------
def test_hapus_jurnal(conn):
    db.seed_database(conn)
    jurnal = db.get_jurnal_umum(conn)
    target = jurnal[-1]["db_id"]
    db.hapus_jurnal(conn, target)
    assert len(db.get_jurnal_umum(conn)) == 19


# ---------------------------------------------------------------------------
# Update jurnal
# ---------------------------------------------------------------------------
def test_update_jurnal_mengubah_data(conn):
    db.seed_database(conn)
    # buat satu entry tambahan (non-seed) lebih dulu
    lines_awal = [
        {"kode": "111", "akun": "Kas", "debit": D("250000"), "kredit": D("0")},
        {"kode": "411", "akun": "Pendapatan Penjualan Gabah", "debit": D("0"), "kredit": D("250000")},
    ]
    db.insert_jurnal(conn, "2025-05-01", "Penjualan tambahan tunai", lines_awal)
    sebelum = db.get_jurnal_umum(conn)
    jumlah_sebelum = len(sebelum)
    target = sebelum[-1]["db_id"]

    lines_baru = [
        {"kode": "111", "akun": "Kas", "debit": D("500000"), "kredit": D("0")},
        {"kode": "411", "akun": "Pendapatan Penjualan Gabah", "debit": D("0"), "kredit": D("500000")},
    ]
    db.update_jurnal(conn, target, "2025-05-02", "Penjualan tambahan diperbarui", lines_baru)

    sesudah = db.get_jurnal_umum(conn)
    # jumlah transaksi tidak berubah
    assert len(sesudah) == jumlah_sebelum
    diubah = next(e for e in sesudah if e["db_id"] == target)
    assert diubah["keterangan"] == "Penjualan tambahan diperbarui"
    assert diubah["tanggal"] == "2025-05-02"
    debit_total = sum((ln["debit"] for ln in diubah["lines"]), D("0"))
    kredit_total = sum((ln["kredit"] for ln in diubah["lines"]), D("0"))
    assert debit_total == D("500000")
    assert kredit_total == D("500000")


def test_update_jurnal_tidak_balance_ditolak(conn):
    db.seed_database(conn)
    lines_awal = [
        {"kode": "111", "akun": "Kas", "debit": D("250000"), "kredit": D("0")},
        {"kode": "411", "akun": "Pendapatan Penjualan Gabah", "debit": D("0"), "kredit": D("250000")},
    ]
    db.insert_jurnal(conn, "2025-05-01", "Penjualan tambahan tunai", lines_awal)
    sebelum = db.get_jurnal_umum(conn)
    target = sebelum[-1]["db_id"]

    lines_tidak_balance = [
        {"kode": "111", "akun": "Kas", "debit": D("100"), "kredit": D("0")},
        {"kode": "411", "akun": "Pendapatan Penjualan Gabah", "debit": D("0"), "kredit": D("90")},
    ]
    with pytest.raises(ValueError):
        db.update_jurnal(conn, target, "2025-05-02", "tidak balance", lines_tidak_balance)

    # data asli harus tetap utuh (tidak ada yang tertulis sebagian)
    sesudah = db.get_jurnal_umum(conn)
    asli = next(e for e in sesudah if e["db_id"] == target)
    assert asli["keterangan"] == "Penjualan tambahan tunai"
    debit_total = sum((ln["debit"] for ln in asli["lines"]), D("0"))
    assert debit_total == D("250000")
