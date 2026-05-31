"""
Test contract untuk engine akuntansi usaha tani padi.
Mengikuti TDD: ditulis SEBELUM implementasi (fase RED).

Angka acuan (sudah diverifikasi manual dari 20 transaksi):
- Total Pendapatan  = 17.500.000
- Total Beban       =  6.000.000
- Laba Bersih       = 11.500.000
- Modal Akhir       = 14.000.000
- Kas akhir         = 14.000.000
- Neraca balance: Aset 14.000.000 = Ekuitas 14.000.000
"""
from decimal import Decimal

import pytest

import accounting as acc
import seed_data


D = Decimal


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def jurnal():
    """Daftar 20 transaksi seed sebagai journal entries."""
    return seed_data.get_jurnal_seed()


@pytest.fixture
def coa():
    """Chart of accounts (bagan akun)."""
    return seed_data.get_chart_of_accounts()


# ---------------------------------------------------------------------------
# S1 - Jurnal Umum: setiap entry balance, seed lengkap
# ---------------------------------------------------------------------------
def test_seed_punya_20_transaksi(jurnal):
    ids = {e["id"] for e in jurnal}
    assert len(jurnal) == 20
    assert ids == {f"T{n:02d}" for n in range(1, 21)}


def test_setiap_entry_jurnal_balance(jurnal):
    for e in jurnal:
        total_d = sum((ln["debit"] for ln in e["lines"]), D("0"))
        total_k = sum((ln["kredit"] for ln in e["lines"]), D("0"))
        assert total_d == total_k, f"{e['id']} tidak balance: {total_d} != {total_k}"


def test_total_jurnal_umum_balance(jurnal):
    td, tk = acc.total_jurnal(jurnal)
    assert td == tk
    assert td == D("52500000")  # total debit semua baris jurnal umum


def test_validasi_entry_tidak_balance_ditolak():
    bad = {
        "id": "TX",
        "tanggal": "2025-01-01",
        "keterangan": "tidak balance",
        "lines": [
            {"kode": "111", "akun": "Kas", "debit": D("100"), "kredit": D("0")},
            {"kode": "311", "akun": "Modal Petani", "debit": D("0"), "kredit": D("90")},
        ],
    }
    with pytest.raises(ValueError):
        acc.validasi_entry(bad)


# ---------------------------------------------------------------------------
# S?? - Buku Besar
# ---------------------------------------------------------------------------
def test_buku_besar_kas_saldo_akhir(jurnal):
    bb = acc.buku_besar(jurnal)
    kas = bb["Kas"]
    assert kas["saldo_akhir"] == D("14000000")


def test_buku_besar_piutang_lunas(jurnal):
    bb = acc.buku_besar(jurnal)
    # piutang muncul di T14 (debit) lalu lunas T15 (kredit) -> 0
    assert bb["Piutang Usaha"]["saldo_akhir"] == D("0")


def test_buku_besar_pendapatan(jurnal):
    bb = acc.buku_besar(jurnal)
    # pendapatan saldo normal kredit -> saldo_akhir negatif (kredit) atau pakai abs
    assert bb["Pendapatan Penjualan Gabah"]["total_kredit"] == D("17500000")


# ---------------------------------------------------------------------------
# S2 - Neraca Saldo (sebelum penyesuaian) balance
# ---------------------------------------------------------------------------
def test_neraca_saldo_balance(jurnal):
    ns = acc.neraca_saldo(jurnal)
    assert ns["total_debit"] == ns["total_kredit"]


def test_neraca_saldo_kas(jurnal):
    ns = acc.neraca_saldo(jurnal)
    baris = {r["akun"]: r for r in ns["rows"]}
    assert baris["Kas"]["debit"] == D("14000000")
    assert baris["Modal Petani"]["kredit"] == D("7000000")


# ---------------------------------------------------------------------------
# S?? - Jurnal Penyesuaian
# ---------------------------------------------------------------------------
def test_jurnal_penyesuaian_perlengkapan():
    ajp = acc.get_jurnal_penyesuaian()
    # AJP: pemakaian perlengkapan (karung) Rp100.000
    total_d = sum((ln["debit"] for e in ajp for ln in e["lines"]), D("0"))
    total_k = sum((ln["kredit"] for e in ajp for ln in e["lines"]), D("0"))
    assert total_d == total_k == D("100000")
    akun_debit = [ln["akun"] for e in ajp for ln in e["lines"] if ln["debit"] > 0]
    assert "Beban Perlengkapan" in akun_debit


# ---------------------------------------------------------------------------
# S5? - Neraca Saldo Setelah Penyesuaian
# ---------------------------------------------------------------------------
def test_nssp_balance(jurnal):
    ajp = acc.get_jurnal_penyesuaian()
    nssp = acc.neraca_saldo(jurnal + ajp)
    assert nssp["total_debit"] == nssp["total_kredit"]
    baris = {r["akun"]: r for r in nssp["rows"]}
    # perlengkapan habis -> 0; beban perlengkapan muncul 100.000
    assert baris.get("Beban Perlengkapan", {}).get("debit") == D("100000")


# ---------------------------------------------------------------------------
# S3 - Laporan Laba Rugi
# ---------------------------------------------------------------------------
def test_laba_rugi(jurnal):
    ajp = acc.get_jurnal_penyesuaian()
    lr = acc.laba_rugi(jurnal + ajp)
    assert lr["total_pendapatan"] == D("17500000")
    assert lr["total_beban"] == D("6000000")
    assert lr["laba_bersih"] == D("11500000")


# ---------------------------------------------------------------------------
# S?? - Laporan Perubahan Ekuitas
# ---------------------------------------------------------------------------
def test_perubahan_ekuitas(jurnal):
    ajp = acc.get_jurnal_penyesuaian()
    eq = acc.perubahan_ekuitas(jurnal + ajp)
    assert eq["modal_awal"] == D("7000000")
    assert eq["laba_bersih"] == D("11500000")
    assert eq["prive"] == D("4500000")
    assert eq["modal_akhir"] == D("14000000")


# ---------------------------------------------------------------------------
# S4 - Laporan Posisi Keuangan (Neraca)
# ---------------------------------------------------------------------------
def test_neraca_balance(jurnal):
    ajp = acc.get_jurnal_penyesuaian()
    nrc = acc.posisi_keuangan(jurnal + ajp)
    assert nrc["total_aset"] == D("14000000")
    assert nrc["total_kewajiban_ekuitas"] == D("14000000")
    assert nrc["total_aset"] == nrc["total_kewajiban_ekuitas"]


# ---------------------------------------------------------------------------
# S5 - Laporan Arus Kas
# ---------------------------------------------------------------------------
def test_arus_kas(jurnal):
    ak = acc.arus_kas(jurnal)
    assert ak["operasi"] == D("11500000")
    assert ak["pendanaan"] == D("2500000")
    assert ak["investasi"] == D("0")
    assert ak["kenaikan_kas"] == D("14000000")
    assert ak["kas_akhir"] == D("14000000")


# ---------------------------------------------------------------------------
# S?? - Jurnal Penutup
# ---------------------------------------------------------------------------
def test_jurnal_penutup_balance(jurnal):
    ajp = acc.get_jurnal_penyesuaian()
    jp = acc.jurnal_penutup(jurnal + ajp)
    td = sum((ln["debit"] for e in jp for ln in e["lines"]), D("0"))
    tk = sum((ln["kredit"] for e in jp for ln in e["lines"]), D("0"))
    assert td == tk


def test_jurnal_penutup_modal(jurnal):
    ajp = acc.get_jurnal_penyesuaian()
    jp = acc.jurnal_penutup(jurnal + ajp)
    # laba 11.5jt masuk modal, prive 4.5jt keluar modal
    bb_setelah = acc.buku_besar(jurnal + ajp + jp)
    assert bb_setelah["Modal Petani"]["saldo_akhir"] == D("-14000000")  # saldo kredit


# ---------------------------------------------------------------------------
# S6 - Neraca Saldo Setelah Penutupan (hanya akun riil)
# ---------------------------------------------------------------------------
def test_neraca_saldo_setelah_penutupan(jurnal):
    ajp = acc.get_jurnal_penyesuaian()
    jp = acc.jurnal_penutup(jurnal + ajp)
    nssp = acc.neraca_saldo_setelah_penutupan(jurnal + ajp + jp)
    assert nssp["total_debit"] == nssp["total_kredit"] == D("14000000")
    akun = {r["akun"] for r in nssp["rows"]}
    # akun nominal tidak boleh muncul
    assert "Pendapatan Penjualan Gabah" not in akun
    assert "Beban Pupuk" not in akun
    assert "Prive" not in akun
    assert "Kas" in akun
    assert "Modal Petani" in akun


# ---------------------------------------------------------------------------
# S8 - format rupiah
# ---------------------------------------------------------------------------
def test_format_rupiah():
    assert acc.format_rupiah(D("17500000")) == "Rp 17.500.000"
    assert acc.format_rupiah(D("0")) == "Rp 0"
    assert acc.format_rupiah(D("-14000000")) == "Rp -14.000.000"
