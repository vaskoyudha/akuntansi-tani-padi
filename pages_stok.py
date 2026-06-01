"""
pages_stok.py
=============
Halaman Stok / Persediaan (guardrail-kritis, read-compute dari pergerakan).

Stok TIDAK disimpan sebagai angka tetap: kuantitas & nilai persediaan selalu
DIHITUNG ULANG dari daftar pergerakan masuk/keluar via mesin moving-average
(stok.py) atas data layer (database.py T4). Halaman ini hanya merangkai &
menyajikan; seluruh matematika stok didelegasikan ke stok.py + database.py.

Struktur (meniru pages_input.py):
  - header + caption
  - peringatan stok menipis (di atas tabel) bila ada item is_low
  - tabel ringkasan stok saat ini (tabel_html, status teks polos)
  - form input pergerakan (masuk/keluar) -> db.insert_stok_gerakan
  - kartu riwayat per item (st.expander) -> stok.replay sebagai tabel_html
  - kelola per pergerakan: edit (modal @st.dialog) + hapus

Tidak menulis jurnal & tidak memanggil fungsi laporan akuntansi apa pun.
"""
import datetime
from decimal import Decimal

import streamlit as st

import accounting as acc
import database as db
import stok
import ui_helpers

D = Decimal

TIPE_PILIHAN = ["masuk", "keluar"]


def fmt_qty(qty, satuan):
    """Format kuantitas sesuai satuan: 2 desimal untuk kg/liter, bulat untuk lembar."""
    q = D(str(qty))
    if satuan == "lembar":
        return f"{int(q)}"
    return f"{q:.2f}"


def _ke_gerakan_replay(rows):
    """Petakan baris DB (get_stok_gerakan) -> dict kontrak stok.replay.

    db.get_stok_gerakan sudah mengembalikan qty/harga_satuan sebagai Decimal
    dan menyertakan id, jadi cukup pilih lima field yang dibutuhkan mesin.
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


@st.dialog("✏️ Edit Pergerakan")
def _dialog_edit_gerakan(conn, row, item):
    """Modal popup untuk edit satu pergerakan stok. Pre-fill dari nilai saat ini.

    Saat simpan: db.update_stok_gerakan memvalidasi replay pasca-edit. Bila
    edit membuat saldo negatif di titik manapun -> ValueError ditangkap dan
    pesan error ditampilkan (dialog tetap terbuka, TANPA st.rerun()); bila
    valid -> dialog ditutup via st.rerun().
    """
    gid = row["id"]
    satuan = item["satuan"]
    try:
        tgl_awal = datetime.date.fromisoformat(row["tanggal"])
    except (ValueError, TypeError):
        tgl_awal = datetime.date.today()
    idx_tipe = TIPE_PILIHAN.index(row["tipe"]) if row["tipe"] in TIPE_PILIHAN else 0
    ref_awal = "" if row.get("ref_jurnal") is None else str(row["ref_jurnal"])

    st.markdown(f"### ✏️ Edit Pergerakan `#{gid}` — {item['nama']} ({satuan})")
    st.caption(
        "Harga satuan hanya bermakna untuk pergerakan 'masuk'; pada 'keluar' "
        "nilai dihitung dari harga rata-rata bergerak."
    )
    with st.form(f"form_edit_stok_{gid}"):
        tanggal = st.date_input("Tanggal", value=tgl_awal, key=f"edit_stok_tanggal_{gid}")
        tipe = st.selectbox(
            "Tipe", TIPE_PILIHAN, index=idx_tipe, key=f"edit_stok_tipe_{gid}"
        )
        qty = st.number_input(
            f"Qty ({satuan})", min_value=0.0, step=1.0,
            value=float(row["qty"]), key=f"edit_stok_qty_{gid}",
        )
        harga = st.number_input(
            "Harga Satuan (Rp)", min_value=0, step=1000,
            value=int(row["harga_satuan"]), key=f"edit_stok_harga_{gid}",
        )
        keterangan = st.text_input(
            "Keterangan", value=row.get("keterangan") or "",
            key=f"edit_stok_keterangan_{gid}",
        )
        ref_str = st.text_input(
            "Ref Jurnal (opsional)", value=ref_awal, key=f"edit_stok_ref_{gid}"
        )

        kol_simpan, kol_batal = st.columns(2)
        with kol_simpan:
            simpan = st.form_submit_button("💾 Simpan Perubahan")
        with kol_batal:
            batal = st.form_submit_button("Batal")

    if batal:
        st.rerun()

    if simpan:
        try:
            ref_clean = ref_str.strip()
            ref_jurnal = int(ref_clean) if ref_clean else None
            db.update_stok_gerakan(
                conn,
                gid,
                item["id"],
                tanggal.isoformat(),
                tipe,
                D(str(qty)),
                D(str(harga)),
                ref_jurnal=ref_jurnal,
                keterangan=keterangan,
            )
        except ValueError as e:
            # Tetap di dalam dialog agar pesan error terlihat (jangan st.rerun()).
            st.error(str(e))
        else:
            st.success("Pergerakan berhasil diperbarui.")
            st.rerun()


def render_stok(conn):
    """Render halaman Stok / Persediaan + form pergerakan + riwayat + kelola."""
    st.markdown("## 📦 Stok / Persediaan")
    st.caption(
        "Stok tidak disimpan sebagai angka tetap — kuantitas dan nilai "
        "persediaan dihitung ulang dari seluruh pergerakan masuk/keluar "
        "dengan metode harga rata-rata bergerak."
    )

    items = db.get_stok_items(conn)
    ringkasan = db.get_stok_ringkasan(conn)

    # --------------------------------------------------- peringatan stok menipis
    menipis = [r["nama"] for r in ringkasan if r["is_low"]]
    if menipis:
        st.warning(
            "⚠️ Stok menipis (sisa ≤ stok minimum): " + ", ".join(menipis) + "."
        )

    # ---------------------------------------------------- tabel ringkasan stok
    st.markdown("### 📊 Stok Saat Ini")
    baris_ringkasan = []
    for r in ringkasan:
        baris_ringkasan.append({
            "Item": r["nama"],
            "Kategori": r["kategori"],
            "Satuan": r["satuan"],
            "Sisa": fmt_qty(r["qty"], r["satuan"]),
            "Nilai": acc.format_rupiah(r["nilai"]),
            "Status": "⚠️ Menipis" if r["is_low"] else "✓ Aman",
        })
    st.markdown(
        ui_helpers.tabel_html(baris_ringkasan, right_cols=["Sisa", "Nilai"]),
        unsafe_allow_html=True,
    )

    st.divider()

    # ------------------------------------------------------- form pergerakan
    st.markdown("### ➕ Catat Pergerakan")
    st.caption(
        "Harga satuan hanya dipakai untuk pergerakan 'masuk'. Pada 'keluar' "
        "nilai keluar dihitung otomatis dari harga rata-rata bergerak."
    )
    with st.form("form_stok", clear_on_submit=True):
        item_sel = st.selectbox(
            "Item",
            items,
            format_func=lambda it: f"{it['nama']} ({it['satuan']})",
            key="stok_item",
        )
        tipe = st.radio("Tipe Pergerakan", TIPE_PILIHAN, horizontal=True, key="stok_tipe")
        tanggal = st.date_input("Tanggal", value=datetime.date.today(), key="stok_tanggal")
        qty = st.number_input(
            "Qty", min_value=0.0, step=1.0, key="stok_qty"
        )
        harga = st.number_input(
            "Harga Satuan (Rp)", min_value=0, step=1000, key="stok_harga",
            help="Hanya bermakna untuk pergerakan 'masuk'.",
        )
        keterangan = st.text_input("Keterangan", key="stok_keterangan")
        ref_str = st.text_input(
            "Ref Jurnal (opsional)", key="stok_ref",
            placeholder="Kosongkan bila tidak terkait jurnal",
        )

        simpan = st.form_submit_button("Simpan Pergerakan")

    if simpan:
        try:
            ref_clean = ref_str.strip()
            ref_jurnal = int(ref_clean) if ref_clean else None
            db.insert_stok_gerakan(
                conn,
                item_sel["id"],
                tanggal.isoformat(),
                tipe,
                D(str(qty)),
                D(str(harga)),
                ref_jurnal=ref_jurnal,
                keterangan=keterangan,
            )
        except ValueError as e:
            st.error(str(e))
        else:
            st.success("Pergerakan berhasil disimpan.")
            st.rerun()

    st.divider()

    # -------------------------------------------------- riwayat per item + kelola
    st.markdown("### 🗂️ Riwayat per Item")
    st.caption(
        "Setiap pergerakan dapat diedit lewat popup atau dihapus. Penghapusan "
        "atau perubahan yang membuat saldo menjadi negatif akan ditolak."
    )

    for item in items:
        satuan = item["satuan"]
        rows = db.get_stok_gerakan(conn, item["id"])
        gerakan = _ke_gerakan_replay(rows)
        snap = stok.snapshot(gerakan)
        judul = f"{item['nama']} — Sisa: {fmt_qty(snap['qty'], satuan)} {satuan}"

        with st.expander(judul):
            if not rows:
                st.caption("Belum ada pergerakan untuk item ini.")
                continue

            langkah = stok.replay(gerakan)
            baris = []
            for s in langkah:
                baris.append({
                    "Tanggal": s["tanggal"],
                    "Tipe": s["tipe"],
                    "Qty": fmt_qty(s["qty"], satuan),
                    "Harga": acc.format_rupiah(s["harga_satuan"]),
                    "Nilai Keluar": (
                        acc.format_rupiah(s["nilai_keluar"])
                        if s["tipe"] == "keluar" else ""
                    ),
                    "Saldo Qty": fmt_qty(s["qty_saldo"], satuan),
                    "Saldo Nilai": acc.format_rupiah(s["nilai_saldo"]),
                })
            st.markdown(
                ui_helpers.tabel_html(
                    baris,
                    right_cols=[
                        "Qty", "Harga", "Nilai Keluar", "Saldo Qty", "Saldo Nilai"
                    ],
                ),
                unsafe_allow_html=True,
            )

            st.markdown("**Kelola Pergerakan**")
            for r in rows:
                gid = r["id"]
                kol_info, kol_edit, kol_hapus = st.columns([5, 1, 1])
                with kol_info:
                    st.markdown(
                        f"`#{gid}` · {r['tanggal']} · {r['tipe']} · "
                        f"{fmt_qty(r['qty'], satuan)} {satuan} · "
                        f"{acc.format_rupiah(r['harga_satuan'])}"
                    )
                with kol_edit:
                    if st.button("✏️ Edit", key=f"edit_stok_{gid}"):
                        _dialog_edit_gerakan(conn, r, item)
                with kol_hapus:
                    if st.button("🗑️ Hapus", key=f"hapus_stok_{gid}"):
                        try:
                            db.hapus_stok_gerakan(conn, gid)
                        except ValueError as e:
                            st.error(str(e))
                        else:
                            st.rerun()
