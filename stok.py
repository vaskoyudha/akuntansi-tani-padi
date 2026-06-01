"""
stok.py
=======
Mesin perhitungan stok MURNI untuk aplikasi "Akuntansi Usaha Tani Padi".

Menghitung kuantitas dan nilai persediaan via harga rata-rata bergerak
(moving average) dengan REPLAY kronologis penuh atas seluruh daftar
pergerakan. Modul ini PURE: tanpa koneksi DB, tanpa Streamlit, hanya Decimal.

Kontrak dict pergerakan (sumber: layer data T4):
    {
        "tanggal": str ISO "YYYY-MM-DD",
        "id": int | None,         # None = kandidat yang divalidasi sebelum INSERT
        "tipe": "masuk" | "keluar",
        "qty": Decimal,           # selalu > 0
        "harga_satuan": Decimal,  # relevan untuk "masuk"; "keluar" pakai avg
    }

Prinsip kunci:
  - Moving average dihitung ULANG dari list penuh setiap kali (NO cache/state).
  - Tidak ada pembulatan internal: Decimal penuh; pembulatan hanya di UI.
  - Sort key tahan-None agar kandidat ber-id None tersortir terakhir pada
    tanggalnya dan tidak melempar TypeError (None vs int).
"""
from decimal import Decimal

D = Decimal
NOL = D("0")


# ---------------------------------------------------------------------------
# Katalog kategori barang persediaan
# ---------------------------------------------------------------------------
KATEGORI = [
    {"nama": "Benih", "satuan": "kg", "desimal": True},
    {"nama": "Pupuk", "satuan": "kg", "desimal": True},
    {"nama": "Pestisida", "satuan": "liter", "desimal": True},
    {"nama": "Karung", "satuan": "lembar", "desimal": False},
]


# ---------------------------------------------------------------------------
# Util internal
# ---------------------------------------------------------------------------
def _sort_gerakan(gerakan):
    """Urutkan deterministik (tanggal, id) dengan id None diperlakukan terakhir.

    Kandidat yang divalidasi SEBELUM INSERT belum punya id (None); pakai
    float("inf") sebagai sentinel agar None tersortir terakhir pada tanggalnya
    dan tidak memicu TypeError saat membandingkan None dengan int.
    """
    return sorted(
        gerakan,
        key=lambda g: (g["tanggal"], g["id"] if g.get("id") is not None else float("inf")),
    )


def _qty(g):
    """Ambil qty sebagai Decimal sambil menjaga guard qty > 0."""
    qty = g["qty"]
    if qty <= NOL:
        raise ValueError(
            f"Qty pergerakan '{g.get('id', '?')}' ({g.get('tipe', '?')}) "
            f"harus > 0, diterima {qty}."
        )
    return qty


# ---------------------------------------------------------------------------
# Replay kronologis penuh
# ---------------------------------------------------------------------------
def replay(gerakan):
    """Replay seluruh pergerakan secara kronologis; kembalikan state per langkah.

    Setiap elemen hasil memuat field input (tanggal, id, tipe, qty,
    harga_satuan) plus state berjalan:
        qty_saldo, nilai_saldo, avg
    dan untuk baris "keluar" juga: nilai_keluar.

    Moving average: avg = nilai_saldo / qty_saldo (0 bila qty_saldo == 0).
      masuk : qty_saldo += qty; nilai_saldo += qty * harga_satuan
      keluar: nilai_keluar = qty * avg; qty_saldo -= qty; nilai_saldo -= nilai_keluar

    Guard: qty masuk/keluar harus > 0 (raise ValueError jika tidak).
    Tidak ada pembulatan internal — Decimal penuh.
    """
    hasil = []
    qty_saldo = NOL
    nilai_saldo = NOL

    for g in _sort_gerakan(gerakan):
        tipe = g["tipe"]
        qty = _qty(g)
        harga = g["harga_satuan"]

        # avg SEBELUM pergerakan (dasar penilaian keluar)
        avg = nilai_saldo / qty_saldo if qty_saldo > NOL else NOL

        baris = {
            "tanggal": g["tanggal"],
            "id": g.get("id"),
            "tipe": tipe,
            "qty": qty,
            "harga_satuan": harga,
        }

        if tipe == "masuk":
            qty_saldo += qty
            nilai_saldo += qty * harga
        elif tipe == "keluar":
            nilai_keluar = qty * avg
            qty_saldo -= qty
            nilai_saldo -= nilai_keluar
            baris["nilai_keluar"] = nilai_keluar
        else:
            raise ValueError(
                f"Tipe pergerakan '{g.get('id', '?')}' tidak dikenal: {tipe!r} "
                f"(harus 'masuk' atau 'keluar')."
            )

        # avg SETELAH pergerakan (state akhir langkah ini)
        baris["qty_saldo"] = qty_saldo
        baris["nilai_saldo"] = nilai_saldo
        baris["avg"] = nilai_saldo / qty_saldo if qty_saldo > NOL else NOL

        hasil.append(baris)

    return hasil


def snapshot(gerakan):
    """Jalankan replay; kembalikan keadaan AKHIR {qty, nilai, avg}.

    Gerakan kosong -> {qty: 0, nilai: 0, avg: 0}.
    """
    langkah = replay(gerakan)
    if not langkah:
        return {"qty": NOL, "nilai": NOL, "avg": NOL}
    akhir = langkah[-1]
    return {
        "qty": akhir["qty_saldo"],
        "nilai": akhir["nilai_saldo"],
        "avg": akhir["avg"],
    }


def validasi_replay(gerakan):
    """Pastikan replay tidak pernah menghasilkan saldo negatif di titik manapun.

    Padanan stok dari accounting.validasi_entry: raise SEBELUM efek samping
    (dipakai T4 untuk menolak keluar > sisa serta edit/hapus yang merusak
    riwayat). Guard qty > 0 dari replay juga turut tertangkap di sini.

    Kembalikan None bila valid; raise ValueError bila ada saldo negatif.
    """
    for baris in replay(gerakan):
        if baris["qty_saldo"] < NOL:
            raise ValueError(
                f"Stok tidak cukup: pergerakan '{baris.get('id', '?')}' "
                f"({baris['tipe']}) qty {baris['qty']} pada {baris['tanggal']} "
                f"membuat saldo menjadi {baris['qty_saldo']} (negatif)."
            )
    return None


def is_low(qty, stok_min):
    """True bila qty berada pada atau di bawah ambang stok minimum (inklusif)."""
    return qty <= stok_min
