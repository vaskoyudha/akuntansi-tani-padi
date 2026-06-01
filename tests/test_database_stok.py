"""
Test untuk lapisan database stok / persediaan (T4).
Ditulis sebelum implementasi (TDD - fase RED).

Konvensi sama persis dengan tests/test_database.py:
  - impor langsung dari root (tanpa conftest)
  - fixture conn(tmp_path) = create_connection + create_tables
  - D = Decimal; assert isinstance Decimal & nilai eksak D("...")
  - tolak via `with pytest.raises(ValueError)` + assert count tetap (DB utuh)
"""
from decimal import Decimal

import pytest

import database as db
import stok

D = Decimal


@pytest.fixture
def conn(tmp_path):
    path = tmp_path / "test.db"
    c = db.create_connection(str(path))
    db.create_tables(c)
    yield c
    c.close()


def _count_gerakan(conn, item_id=None):
    cur = conn.cursor()
    if item_id is None:
        cur.execute("SELECT COUNT(*) FROM stok_gerakan")
    else:
        cur.execute("SELECT COUNT(*) FROM stok_gerakan WHERE item_id = ?", (item_id,))
    return cur.fetchone()[0]


def _item_id_by_nama(conn, nama):
    items = db.get_stok_items(conn)
    return next(i["id"] for i in items if i["nama"] == nama)


# ---------------------------------------------------------------------------
# Seed idempoten
# ---------------------------------------------------------------------------
def test_seed_stok_memasukkan_4_item(conn):
    db.seed_stok(conn)
    items = db.get_stok_items(conn)
    assert len(items) == 4
    nama = {i["nama"] for i in items}
    assert nama == {"Benih", "Pupuk", "Pestisida", "Karung"}


def test_seed_stok_idempoten(conn):
    db.seed_stok(conn)
    db.seed_stok(conn)  # dua kali tidak menggandakan
    items = db.get_stok_items(conn)
    assert len(items) == 4
    # 8 pergerakan seed juga tidak digandakan
    assert _count_gerakan(conn) == 8


def test_get_stok_items_decimal_stok_min(conn):
    db.seed_stok(conn)
    items = db.get_stok_items(conn)
    for i in items:
        assert isinstance(i["stok_min"], Decimal)
    benih = next(i for i in items if i["nama"] == "Benih")
    assert benih["stok_min"] == D("10")
    assert benih["kategori"] == "Benih"
    assert benih["satuan"] == "kg"


def test_get_stok_gerakan_decimal_dan_urut(conn):
    db.seed_stok(conn)
    gerakan = db.get_stok_gerakan(conn)
    assert len(gerakan) == 8
    for g in gerakan:
        assert isinstance(g["qty"], Decimal)
        assert isinstance(g["harga_satuan"], Decimal)
    # filter by item
    bid = _item_id_by_nama(conn, "Pupuk")
    pupuk = db.get_stok_gerakan(conn, item_id=bid)
    assert len(pupuk) == 3
    assert all(g["item_id"] == bid for g in pupuk)


# ---------------------------------------------------------------------------
# Decimal roundtrip (jebakan float)
# ---------------------------------------------------------------------------
def test_insert_roundtrip_float_jadi_decimal(conn):
    db.seed_stok(conn)
    bid = _item_id_by_nama(conn, "Benih")
    # qty 10.5 sebagai float (seolah dari st.number_input)
    db.insert_stok_gerakan(conn, bid, "2025-06-01", "masuk", 10.5, 12000)
    gerakan = db.get_stok_gerakan(conn, item_id=bid)
    baru = gerakan[-1]
    assert isinstance(baru["qty"], Decimal)
    assert baru["qty"] == D("10.5")  # bukan 10.4999...
    assert baru["harga_satuan"] == D("12000")


def test_insert_mengembalikan_row_id(conn):
    db.seed_stok(conn)
    bid = _item_id_by_nama(conn, "Benih")
    gid = db.insert_stok_gerakan(conn, bid, "2025-06-01", "masuk", "5", "1000")
    assert isinstance(gid, int)
    found = next(g for g in db.get_stok_gerakan(conn, item_id=bid) if g["id"] == gid)
    assert found["qty"] == D("5")


# ---------------------------------------------------------------------------
# ref_jurnal ON DELETE SET NULL
# ---------------------------------------------------------------------------
def test_ref_jurnal_set_null_saat_jurnal_dihapus(conn):
    db.seed_database(conn)  # buat baris jurnal nyata
    jurnal = db.get_jurnal_umum(conn)
    jid = jurnal[0]["db_id"]

    db.seed_stok(conn)
    bid = _item_id_by_nama(conn, "Benih")
    gid = db.insert_stok_gerakan(
        conn, bid, "2025-06-02", "masuk", "3", "1000", ref_jurnal=jid
    )
    # pra-kondisi: ref_jurnal terisi
    before = next(g for g in db.get_stok_gerakan(conn, item_id=bid) if g["id"] == gid)
    assert before["ref_jurnal"] == jid

    db.hapus_jurnal(conn, jid)

    after = next(g for g in db.get_stok_gerakan(conn, item_id=bid) if g["id"] == gid)
    # pergerakan tetap ada, ref_jurnal jadi None
    assert after is not None
    assert after["ref_jurnal"] is None


def test_seed_stok_menautkan_ref_jurnal(conn):
    db.seed_database(conn)
    db.seed_stok(conn)
    bid = _item_id_by_nama(conn, "Benih")
    benih_gerakan = db.get_stok_gerakan(conn, item_id=bid)
    # Benih seed punya ref "T02" -> harus tertaut ke id jurnal kode T02
    cur = conn.cursor()
    cur.execute("SELECT id FROM jurnal WHERE kode = 'T02'")
    t02_id = cur.fetchone()[0]
    assert benih_gerakan[0]["ref_jurnal"] == t02_id


def test_seed_stok_tanpa_jurnal_ref_none(conn):
    # seed_stok tanpa seed_database -> kode tak ditemukan -> ref_jurnal None
    db.seed_stok(conn)
    gerakan = db.get_stok_gerakan(conn)
    assert all(g["ref_jurnal"] is None for g in gerakan)


# ---------------------------------------------------------------------------
# [NEGATIVE] keluar > sisa ditolak, DB utuh
# ---------------------------------------------------------------------------
def test_keluar_lebih_dari_sisa_ditolak(conn):
    db.seed_stok(conn)
    bid = _item_id_by_nama(conn, "Karung")  # mulai dari katalog
    # tambah item bersih sendiri agar terkontrol
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO stok_item (nama, kategori, satuan, stok_min) "
        "VALUES ('UjiKeluar', 'Benih', 'kg', '0')"
    )
    conn.commit()
    iid = cur.lastrowid

    db.insert_stok_gerakan(conn, iid, "2025-07-01", "masuk", "10", "100")
    assert _count_gerakan(conn, iid) == 1

    with pytest.raises(ValueError):
        db.insert_stok_gerakan(conn, iid, "2025-07-02", "keluar", "20", "0")

    # DB utuh: tetap 1 pergerakan untuk item ini
    assert _count_gerakan(conn, iid) == 1


# ---------------------------------------------------------------------------
# [NEGATIVE] hapus masuk yang merusak riwayat ditolak
# ---------------------------------------------------------------------------
def test_hapus_masuk_yang_merusak_riwayat_ditolak(conn):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO stok_item (nama, kategori, satuan, stok_min) "
        "VALUES ('UjiHapus', 'Benih', 'kg', '0')"
    )
    conn.commit()
    iid = cur.lastrowid

    g1 = db.insert_stok_gerakan(conn, iid, "2025-07-01", "masuk", "10", "100")
    db.insert_stok_gerakan(conn, iid, "2025-07-02", "masuk", "10", "100")
    db.insert_stok_gerakan(conn, iid, "2025-07-03", "keluar", "15", "0")
    assert _count_gerakan(conn, iid) == 3

    # hapus masuk pertama -> saldo akan minus di titik keluar -> ditolak
    with pytest.raises(ValueError):
        db.hapus_stok_gerakan(conn, g1)

    assert _count_gerakan(conn, iid) == 3
    masih = next(g for g in db.get_stok_gerakan(conn, item_id=iid) if g["id"] == g1)
    assert masih["qty"] == D("10")


def test_hapus_yang_aman_berhasil(conn):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO stok_item (nama, kategori, satuan, stok_min) "
        "VALUES ('UjiHapusOk', 'Benih', 'kg', '0')"
    )
    conn.commit()
    iid = cur.lastrowid

    db.insert_stok_gerakan(conn, iid, "2025-07-01", "masuk", "10", "100")
    g2 = db.insert_stok_gerakan(conn, iid, "2025-07-02", "masuk", "5", "100")
    assert _count_gerakan(conn, iid) == 2
    # hapus masuk kedua aman (tidak ada keluar) -> berhasil
    db.hapus_stok_gerakan(conn, g2)
    assert _count_gerakan(conn, iid) == 1


# ---------------------------------------------------------------------------
# [NEGATIVE] update yang membuat minus ditolak; update aman berhasil
# ---------------------------------------------------------------------------
def test_update_yang_membuat_minus_ditolak(conn):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO stok_item (nama, kategori, satuan, stok_min) "
        "VALUES ('UjiUpdate', 'Benih', 'kg', '0')"
    )
    conn.commit()
    iid = cur.lastrowid

    g1 = db.insert_stok_gerakan(conn, iid, "2025-07-01", "masuk", "10", "100")
    db.insert_stok_gerakan(conn, iid, "2025-07-02", "keluar", "8", "0")
    assert _count_gerakan(conn, iid) == 2

    # kecilkan masuk jadi 5 -> keluar 8 tak cukup -> ditolak, DB utuh
    with pytest.raises(ValueError):
        db.update_stok_gerakan(conn, g1, iid, "2025-07-01", "masuk", "5", "100")

    asli = next(g for g in db.get_stok_gerakan(conn, item_id=iid) if g["id"] == g1)
    assert asli["qty"] == D("10")


def test_update_yang_aman_berhasil(conn):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO stok_item (nama, kategori, satuan, stok_min) "
        "VALUES ('UjiUpdateOk', 'Benih', 'kg', '0')"
    )
    conn.commit()
    iid = cur.lastrowid

    g1 = db.insert_stok_gerakan(conn, iid, "2025-07-01", "masuk", "10", "100")
    db.update_stok_gerakan(conn, g1, iid, "2025-07-01", "masuk", "12", "150")
    diubah = next(g for g in db.get_stok_gerakan(conn, item_id=iid) if g["id"] == g1)
    assert diubah["qty"] == D("12")
    assert diubah["harga_satuan"] == D("150")


# ---------------------------------------------------------------------------
# Ringkasan
# ---------------------------------------------------------------------------
def test_get_stok_ringkasan_benar(conn):
    db.seed_stok(conn)
    ringkasan = db.get_stok_ringkasan(conn)
    assert len(ringkasan) == 4
    for r in ringkasan:
        assert isinstance(r["qty"], Decimal)
        assert isinstance(r["nilai"], Decimal)
        assert isinstance(r["avg"], Decimal)
        assert isinstance(r["stok_min"], Decimal)
        assert isinstance(r["is_low"], bool)

    # Pupuk: 80@5000 + 50@6000 + 40@5000 = 400000+300000+200000 = 900000 nilai, qty 170
    pupuk = next(r for r in ringkasan if r["nama"] == "Pupuk")
    assert pupuk["qty"] == D("170")
    assert pupuk["nilai"] == D("900000")
    assert pupuk["avg"] == D("900000") / D("170")
    assert pupuk["is_low"] is False  # 170 > stok_min 20

    # cocokkan dengan snapshot langsung
    bid = pupuk["id"]
    movs = [
        {"tanggal": g["tanggal"], "id": g["id"], "tipe": g["tipe"],
         "qty": g["qty"], "harga_satuan": g["harga_satuan"]}
        for g in db.get_stok_gerakan(conn, item_id=bid)
    ]
    snap = stok.snapshot(movs)
    assert pupuk["qty"] == snap["qty"]
    assert pupuk["nilai"] == snap["nilai"]
    assert pupuk["avg"] == snap["avg"]


def test_ringkasan_is_low_true_saat_di_bawah_minimum(conn):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO stok_item (nama, kategori, satuan, stok_min) "
        "VALUES ('UjiLow', 'Benih', 'kg', '10')"
    )
    conn.commit()
    iid = cur.lastrowid
    db.insert_stok_gerakan(conn, iid, "2025-07-01", "masuk", "5", "100")
    ringkasan = db.get_stok_ringkasan(conn)
    low = next(r for r in ringkasan if r["nama"] == "UjiLow")
    assert low["qty"] == D("5")
    assert low["is_low"] is True  # 5 <= 10
