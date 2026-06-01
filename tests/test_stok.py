"""
Test untuk modul stok.py — mesin perhitungan stok murni (moving average).
Ditulis sebelum implementasi (TDD - fase RED).

Impor langsung dari root (tests/ tanpa conftest.py), gaya tests/test_database.py.
Semua nilai uang/qty memakai decimal.Decimal.
"""
from decimal import Decimal

import pytest

import stok

D = Decimal


# ---------------------------------------------------------------------------
# Helper pembentuk pergerakan (kontrak dict dengan T2/T4)
# ---------------------------------------------------------------------------
def _g(tanggal, id_, tipe, qty, harga):
    return {
        "tanggal": tanggal,
        "id": id_,
        "tipe": tipe,
        "qty": D(qty),
        "harga_satuan": D(harga),
    }


# ---------------------------------------------------------------------------
# Katalog kategori
# ---------------------------------------------------------------------------
def test_katalog_kategori_lengkap():
    nama = [k["nama"] for k in stok.KATEGORI]
    assert nama == ["Benih", "Pupuk", "Pestisida", "Karung"]
    by_nama = {k["nama"]: k for k in stok.KATEGORI}
    assert by_nama["Benih"]["satuan"] == "kg" and by_nama["Benih"]["desimal"] is True
    assert by_nama["Pupuk"]["satuan"] == "kg" and by_nama["Pupuk"]["desimal"] is True
    assert by_nama["Pestisida"]["satuan"] == "liter" and by_nama["Pestisida"]["desimal"] is True
    assert by_nama["Karung"]["satuan"] == "lembar" and by_nama["Karung"]["desimal"] is False


# ---------------------------------------------------------------------------
# Skenario 1: masuk-avg
# ---------------------------------------------------------------------------
def test_masuk_avg_dua_kali():
    gerakan = [
        _g("2025-01-01", 1, "masuk", "50", "10000"),
        _g("2025-01-02", 2, "masuk", "50", "20000"),
    ]
    snap = stok.snapshot(gerakan)
    assert snap["qty"] == D("100")
    assert snap["avg"] == D("15000")
    assert snap["nilai"] == D("1500000")


# ---------------------------------------------------------------------------
# Skenario 2: keluar-avg
# ---------------------------------------------------------------------------
def test_keluar_avg_mengurangi_pakai_rata_rata():
    gerakan = [
        _g("2025-01-01", 1, "masuk", "50", "10000"),
        _g("2025-01-02", 2, "masuk", "50", "20000"),
        _g("2025-01-03", 3, "keluar", "40", "0"),
    ]
    snap = stok.snapshot(gerakan)
    assert snap["qty"] == D("60")
    assert snap["nilai"] == D("900000")
    assert snap["avg"] == D("15000")

    langkah = stok.replay(gerakan)
    baris_keluar = langkah[-1]
    assert baris_keluar["tipe"] == "keluar"
    assert baris_keluar["nilai_keluar"] == D("600000")


def test_replay_menyertakan_state_per_langkah():
    gerakan = [
        _g("2025-01-01", 1, "masuk", "50", "10000"),
        _g("2025-01-02", 2, "masuk", "50", "20000"),
    ]
    langkah = stok.replay(gerakan)
    assert len(langkah) == 2
    # field input dipertahankan
    assert langkah[0]["id"] == 1 and langkah[0]["tipe"] == "masuk"
    assert langkah[0]["qty"] == D("50") and langkah[0]["harga_satuan"] == D("10000")
    # state berjalan
    assert langkah[0]["qty_saldo"] == D("50")
    assert langkah[0]["nilai_saldo"] == D("500000")
    assert langkah[0]["avg"] == D("10000")
    assert langkah[1]["qty_saldo"] == D("100")
    assert langkah[1]["nilai_saldo"] == D("1500000")
    assert langkah[1]["avg"] == D("15000")


# ---------------------------------------------------------------------------
# Skenario 3: same-date (deterministik & idempoten)
# ---------------------------------------------------------------------------
def test_same_date_urut_by_id_dan_deterministik():
    # sengaja diberikan tidak terurut (id 2 dulu) untuk menguji sort
    gerakan = [
        _g("2025-02-10", 2, "masuk", "10", "2000"),
        _g("2025-02-10", 1, "masuk", "5", "1000"),
    ]
    hasil1 = stok.replay(gerakan)
    hasil2 = stok.replay(gerakan)
    assert hasil1 == hasil2  # idempoten, tak ada cache basi
    # urutan sesuai (tanggal, id): id=1 dulu lalu id=2
    assert [b["id"] for b in hasil1] == [1, 2]
    assert hasil1[0]["qty_saldo"] == D("5")
    assert hasil1[1]["qty_saldo"] == D("15")


# ---------------------------------------------------------------------------
# Skenario 4: replay-delete (buang pergerakan pertama, tak ada cache basi)
# ---------------------------------------------------------------------------
def test_replay_delete_setara_replay_segar():
    g1 = _g("2025-03-01", 1, "masuk", "50", "10000")
    g2 = _g("2025-03-02", 2, "masuk", "50", "20000")
    g3 = _g("2025-03-03", 3, "keluar", "40", "0")
    penuh = [g1, g2, g3]
    _ = stok.replay(penuh)  # jalankan dulu untuk membuktikan tak ada state global

    sisa = [g2, g3]  # buang pergerakan pertama
    hasil_sisa = stok.replay(sisa)
    hasil_segar = stok.replay([g2, g3])
    assert hasil_sisa == hasil_segar
    snap = stok.snapshot(sisa)
    # hanya g2 (masuk 50@20000) lalu keluar 40 @ avg 20000
    assert snap["qty"] == D("10")
    assert snap["avg"] == D("20000")
    assert snap["nilai"] == D("200000")


# ---------------------------------------------------------------------------
# Skenario 5: negatif-keluar (validasi_replay menolak)
# ---------------------------------------------------------------------------
def test_validasi_replay_tolak_keluar_lebih_dari_sisa():
    gerakan = [
        _g("2025-04-01", 1, "masuk", "10", "1000"),
        _g("2025-04-02", 2, "keluar", "20", "0"),
    ]
    with pytest.raises(ValueError):
        stok.validasi_replay(gerakan)


def test_validasi_replay_lolos_jika_cukup():
    gerakan = [
        _g("2025-04-01", 1, "masuk", "10", "1000"),
        _g("2025-04-02", 2, "keluar", "10", "0"),
    ]
    # tidak boleh raise
    assert stok.validasi_replay(gerakan) is None


# ---------------------------------------------------------------------------
# Skenario 6: guards + presisi penuh + is_low
# ---------------------------------------------------------------------------
def test_guard_masuk_qty_nol_ditolak():
    gerakan = [_g("2025-05-01", 1, "masuk", "0", "1000")]
    with pytest.raises(ValueError):
        stok.replay(gerakan)


def test_guard_keluar_qty_nol_ditolak():
    gerakan = [
        _g("2025-05-01", 1, "masuk", "10", "1000"),
        _g("2025-05-02", 2, "keluar", "0", "0"),
    ]
    with pytest.raises(ValueError):
        stok.replay(gerakan)


def test_guard_qty_negatif_ditolak():
    gerakan = [_g("2025-05-01", 1, "masuk", "-5", "1000")]
    with pytest.raises(ValueError):
        stok.replay(gerakan)


def test_guard_juga_lewat_validasi_replay():
    gerakan = [_g("2025-05-01", 1, "masuk", "0", "1000")]
    with pytest.raises(ValueError):
        stok.validasi_replay(gerakan)


def test_is_low_batas_inklusif():
    assert stok.is_low(D("10"), D("10")) is True
    assert stok.is_low(D("11"), D("10")) is False
    assert stok.is_low(D("9"), D("10")) is True


def test_avg_presisi_penuh_tidak_dibulatkan():
    # masuk 3 unit total 500000 -> harga 500000/3 (tak habis dibagi)
    harga = D("500000") / D("3")
    gerakan = [_g("2025-05-01", 1, "masuk", "3", harga)]
    snap = stok.snapshot(gerakan)
    assert snap["qty"] == D("3")
    assert snap["nilai"] == D("3") * harga
    # avg = nilai/qty dihitung tanpa pembulatan internal (round-trip eksak)
    assert snap["avg"] == (D("3") * harga) / D("3")
    # buktikan tidak dibulatkan ke integer rupiah
    assert snap["avg"] != D("166666")
    assert snap["avg"] != D("166667")
    # masih memuat bagian pecahan (presisi penuh dipertahankan)
    assert snap["avg"] != snap["avg"].to_integral_value()


# ---------------------------------------------------------------------------
# Skenario tambahan: kandidat id=None (validasi sebelum INSERT, T4)
# ---------------------------------------------------------------------------
def test_kandidat_id_none_tidak_typeerror_dan_terakhir_di_tanggalnya():
    existing1 = _g("2025-06-01", 1, "masuk", "30", "1000")
    existing2 = _g("2025-06-01", 2, "masuk", "20", "2000")
    kandidat = _g("2025-06-01", None, "keluar", "10", "0")
    gerakan = [existing1, existing2, kandidat]

    # tidak boleh TypeError (None vs int) saat sort
    langkah = stok.replay(gerakan)
    # kandidat (id None) diperlakukan terakhir di tanggalnya
    assert [b["id"] for b in langkah] == [1, 2, None]
    # validasi_replay juga tidak TypeError
    assert stok.validasi_replay(gerakan) is None


def test_kandidat_id_none_keluar_berlebih_ditolak():
    existing = _g("2025-06-01", 1, "masuk", "5", "1000")
    kandidat = _g("2025-06-01", None, "keluar", "10", "0")
    gerakan = [existing, kandidat]
    with pytest.raises(ValueError):
        stok.validasi_replay(gerakan)


# ---------------------------------------------------------------------------
# snapshot kosong
# ---------------------------------------------------------------------------
def test_snapshot_kosong_nol():
    snap = stok.snapshot([])
    assert snap["qty"] == D("0")
    assert snap["nilai"] == D("0")
    assert snap["avg"] == D("0")
    assert isinstance(snap["qty"], Decimal)
    assert isinstance(snap["nilai"], Decimal)
    assert isinstance(snap["avg"], Decimal)


# ---------------------------------------------------------------------------
# Decimal-only di output
# ---------------------------------------------------------------------------
def test_output_replay_pakai_decimal():
    gerakan = [
        _g("2025-07-01", 1, "masuk", "50", "10000"),
        _g("2025-07-02", 2, "keluar", "10", "0"),
    ]
    langkah = stok.replay(gerakan)
    for b in langkah:
        assert isinstance(b["qty_saldo"], Decimal)
        assert isinstance(b["nilai_saldo"], Decimal)
        assert isinstance(b["avg"], Decimal)
    assert isinstance(langkah[-1]["nilai_keluar"], Decimal)
