"""
database.py
===========
Lapisan persistensi SQLite untuk aplikasi akuntansi usaha tani padi.

Skema:
  users(id, username UNIQUE, password_hash, nama)
  jurnal(id, kode, tanggal, keterangan, tipe)         -- tipe: umum|penyesuaian|penutup
  jurnal_baris(id, jurnal_id, kode_akun, akun, debit, kredit)
  stok_item(id, nama UNIQUE, kategori, satuan, stok_min)
  stok_gerakan(id, item_id, tanggal, tipe, qty, harga_satuan, ref_jurnal, keterangan)

Nilai uang disimpan sebagai TEXT (string Decimal) agar presisi tetap terjaga;
SQLite tidak punya tipe Decimal asli.
"""
import sqlite3
from decimal import Decimal

import accounting as acc
import seed_data
import stok

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
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS stok_item (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            nama     TEXT UNIQUE NOT NULL,
            kategori TEXT NOT NULL,
            satuan   TEXT NOT NULL,
            stok_min TEXT NOT NULL DEFAULT '0'
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS stok_gerakan (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id      INTEGER NOT NULL,
            tanggal      TEXT NOT NULL,
            tipe         TEXT NOT NULL,
            qty          TEXT NOT NULL DEFAULT '0',
            harga_satuan TEXT NOT NULL DEFAULT '0',
            ref_jurnal   INTEGER,
            keterangan   TEXT,
            FOREIGN KEY (item_id) REFERENCES stok_item(id) ON DELETE CASCADE,
            FOREIGN KEY (ref_jurnal) REFERENCES jurnal(id) ON DELETE SET NULL
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


def update_jurnal(
    conn: sqlite3.Connection,
    db_id: int,
    tanggal: str,
    keterangan: str,
    lines: list[dict],
    kode: str | None = None,
) -> None:
    """
    Perbarui satu transaksi yang sudah ada (db_id). Validasi balance dulu
    (debit==kredit, !=0). Raise ValueError bila tidak balance -> tidak ada
    yang berubah. Kode & tipe entry tidak diubah; hanya tanggal, keterangan,
    dan baris-baris jurnal yang diganti.
    """
    entry = {"id": kode or "?", "tanggal": tanggal, "keterangan": keterangan, "lines": lines}
    acc.validasi_entry(entry)  # raise ValueError jika tidak balance -> DB utuh

    cur = conn.cursor()
    cur.execute(
        "UPDATE jurnal SET tanggal = ?, keterangan = ? WHERE id = ?",
        (tanggal, keterangan, db_id),
    )
    cur.execute("DELETE FROM jurnal_baris WHERE jurnal_id = ?", (db_id,))
    for ln in lines:
        cur.execute(
            "INSERT INTO jurnal_baris (jurnal_id, kode_akun, akun, debit, kredit) "
            "VALUES (?, ?, ?, ?, ?)",
            (db_id, ln["kode"], ln["akun"], str(D(ln["debit"])), str(D(ln["kredit"]))),
        )
    conn.commit()


def reset_jurnal(conn: sqlite3.Connection) -> None:
    """Kosongkan semua jurnal lalu seed ulang (untuk tombol reset di UI)."""
    cur = conn.cursor()
    cur.execute("DELETE FROM jurnal_baris")
    cur.execute("DELETE FROM jurnal")
    conn.commit()
    seed_database(conn)


# ---------------------------------------------------------------------------
# Stok / Persediaan
# ---------------------------------------------------------------------------
def _ke_gerakan_stok(rows: list[dict]) -> list[dict]:
    """Petakan baris pergerakan DB ke dict kontrak stok.py.

    DB row {id,item_id,tanggal,tipe,qty,harga_satuan,...} ->
    {tanggal, id, tipe, qty: Decimal, harga_satuan: Decimal}.
    """
    return [
        {
            "tanggal": r["tanggal"],
            "id": r["id"],
            "tipe": r["tipe"],
            "qty": r["qty"],
            "harga_satuan": r["harga_satuan"],
        }
        for r in rows
    ]


def seed_stok(conn: sqlite3.Connection) -> None:
    """Masukkan item & pergerakan stok awal. Idempoten via COUNT stok_item.

    Penautan ref_jurnal bersifat best-effort: cari id jurnal berdasarkan kode
    (mis. 'T02'); jika tidak ada, simpan None. Tidak pernah menggagalkan seeding.
    """
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM stok_item")
    if cur.fetchone()[0] > 0:
        return

    nama_ke_id: dict[str, int] = {}
    for item in seed_data.get_stok_item_seed():
        cur.execute(
            "INSERT INTO stok_item (nama, kategori, satuan, stok_min) "
            "VALUES (?, ?, ?, ?)",
            (item["nama"], item["kategori"], item["satuan"], str(D(item["stok_min"]))),
        )
        iid = cur.lastrowid
        if iid is None:
            raise RuntimeError("Gagal menyimpan item stok: tidak ada row id.")
        nama_ke_id[item["nama"]] = iid

    for g in seed_data.get_stok_gerakan_seed():
        item_id = nama_ke_id[g["item"]]
        ref_jurnal = None
        kode = g.get("ref")
        if kode:
            cur.execute("SELECT id FROM jurnal WHERE kode = ?", (kode,))
            row = cur.fetchone()
            if row is not None:
                ref_jurnal = row[0]
        cur.execute(
            "INSERT INTO stok_gerakan "
            "(item_id, tanggal, tipe, qty, harga_satuan, ref_jurnal, keterangan) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                item_id,
                g["tanggal"],
                g["tipe"],
                str(D(g["qty"])),
                str(D(g["harga_satuan"])),
                ref_jurnal,
                g.get("keterangan", ""),
            ),
        )
    conn.commit()


def get_stok_items(conn: sqlite3.Connection) -> list[dict]:
    """Semua item persediaan, urut id. stok_min sebagai Decimal."""
    cur = conn.cursor()
    cur.execute(
        "SELECT id, nama, kategori, satuan, stok_min FROM stok_item ORDER BY id"
    )
    return [
        {
            "id": iid,
            "nama": nama,
            "kategori": kategori,
            "satuan": satuan,
            "stok_min": D(stok_min),
        }
        for iid, nama, kategori, satuan, stok_min in cur.fetchall()
    ]


def get_stok_gerakan(conn: sqlite3.Connection, item_id: int | None = None) -> list[dict]:
    """Pergerakan stok (semua atau per item_id), urut (tanggal, id).

    qty & harga_satuan dikembalikan sebagai Decimal.
    """
    cur = conn.cursor()
    if item_id is None:
        cur.execute(
            "SELECT id, item_id, tanggal, tipe, qty, harga_satuan, ref_jurnal, keterangan "
            "FROM stok_gerakan ORDER BY tanggal, id"
        )
    else:
        cur.execute(
            "SELECT id, item_id, tanggal, tipe, qty, harga_satuan, ref_jurnal, keterangan "
            "FROM stok_gerakan WHERE item_id = ? ORDER BY tanggal, id",
            (item_id,),
        )
    return [
        {
            "id": gid,
            "item_id": iid,
            "tanggal": tanggal,
            "tipe": tipe,
            "qty": D(qty),
            "harga_satuan": D(harga),
            "ref_jurnal": ref_jurnal,
            "keterangan": keterangan,
        }
        for gid, iid, tanggal, tipe, qty, harga, ref_jurnal, keterangan in cur.fetchall()
    ]


def insert_stok_gerakan(
    conn: sqlite3.Connection,
    item_id: int,
    tanggal: str,
    tipe: str,
    qty,
    harga_satuan,
    ref_jurnal: int | None = None,
    keterangan: str = "",
) -> int:
    """Simpan satu pergerakan stok. Validasi replay (tak boleh minus) DULU.

    qty/harga dikonversi via D(str(...)) agar aman dari jebakan float.
    Raise ValueError bila pergerakan membuat saldo negatif -> DB utuh.
    Kembalikan row id baru.
    """
    qty_d = D(str(qty))
    harga_d = D(str(harga_satuan))

    # riwayat kandidat = pergerakan eksisting + kandidat baru (id=None -> sortir terakhir)
    riwayat = _ke_gerakan_stok(get_stok_gerakan(conn, item_id))
    riwayat.append(
        {"tanggal": tanggal, "id": None, "tipe": tipe, "qty": qty_d, "harga_satuan": harga_d}
    )
    stok.validasi_replay(riwayat)  # raise ValueError SEBELUM tulis -> DB utuh

    cur = conn.cursor()
    cur.execute(
        "INSERT INTO stok_gerakan "
        "(item_id, tanggal, tipe, qty, harga_satuan, ref_jurnal, keterangan) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (item_id, tanggal, tipe, str(qty_d), str(harga_d), ref_jurnal, keterangan),
    )
    gid = cur.lastrowid
    if gid is None:
        raise RuntimeError("Gagal menyimpan pergerakan stok: tidak ada row id.")
    conn.commit()
    return gid


def update_stok_gerakan(
    conn: sqlite3.Connection,
    gid: int,
    item_id: int,
    tanggal: str,
    tipe: str,
    qty,
    harga_satuan,
    ref_jurnal: int | None = None,
    keterangan: str = "",
) -> None:
    """Perbarui satu pergerakan stok. Validasi replay pasca-edit DULU.

    Membangun riwayat pasca-edit: baris id==gid diganti nilai baru (id tetap
    gid agar tetap tersortir di tempatnya). Raise ValueError bila edit membuat
    saldo negatif di titik manapun -> DB utuh.
    """
    qty_d = D(str(qty))
    harga_d = D(str(harga_satuan))

    riwayat = []
    for r in _ke_gerakan_stok(get_stok_gerakan(conn, item_id)):
        if r["id"] == gid:
            riwayat.append(
                {"tanggal": tanggal, "id": gid, "tipe": tipe,
                 "qty": qty_d, "harga_satuan": harga_d}
            )
        else:
            riwayat.append(r)
    stok.validasi_replay(riwayat)  # raise -> DB utuh

    cur = conn.cursor()
    cur.execute(
        "UPDATE stok_gerakan SET item_id = ?, tanggal = ?, tipe = ?, qty = ?, "
        "harga_satuan = ?, ref_jurnal = ?, keterangan = ? WHERE id = ?",
        (item_id, tanggal, tipe, str(qty_d), str(harga_d), ref_jurnal, keterangan, gid),
    )
    conn.commit()


def hapus_stok_gerakan(conn: sqlite3.Connection, gid: int) -> None:
    """Hapus satu pergerakan stok. Validasi replay TANPA baris itu DULU.

    Membangun riwayat tanpa baris id==gid. Raise ValueError bila penghapusan
    membuat saldo negatif di titik manapun -> DB utuh.
    """
    cur = conn.cursor()
    cur.execute("SELECT item_id FROM stok_gerakan WHERE id = ?", (gid,))
    row = cur.fetchone()
    if row is None:
        return  # tidak ada -> tidak ada efek
    item_id = row[0]

    riwayat = [
        r for r in _ke_gerakan_stok(get_stok_gerakan(conn, item_id)) if r["id"] != gid
    ]
    stok.validasi_replay(riwayat)  # raise -> DB utuh

    cur.execute("DELETE FROM stok_gerakan WHERE id = ?", (gid,))
    conn.commit()


def get_stok_ringkasan(conn: sqlite3.Connection) -> list[dict]:
    """Ringkasan per item via stok.snapshot atas riwayat penuh.

    Tidak menyimpan kolom turunan; selalu hitung ulang dari pergerakan.
    """
    ringkasan = []
    for item in get_stok_items(conn):
        movs = _ke_gerakan_stok(get_stok_gerakan(conn, item["id"]))
        snap = stok.snapshot(movs)
        ringkasan.append(
            {
                "id": item["id"],
                "nama": item["nama"],
                "kategori": item["kategori"],
                "satuan": item["satuan"],
                "qty": snap["qty"],
                "nilai": snap["nilai"],
                "avg": snap["avg"],
                "stok_min": item["stok_min"],
                "is_low": stok.is_low(snap["qty"], item["stok_min"]),
            }
        )
    return ringkasan


def reset_stok(conn: sqlite3.Connection) -> None:
    """Kosongkan HANYA tabel stok lalu seed ulang. JANGAN menyentuh jurnal."""
    cur = conn.cursor()
    cur.execute("DELETE FROM stok_gerakan")
    cur.execute("DELETE FROM stok_item")
    conn.commit()
    seed_stok(conn)
