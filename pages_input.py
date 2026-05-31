"""
pages_input.py
==============
Halaman form input transaksi jurnal manual (guardrail-kritis).

Hanya menulis jurnal bertipe 'umum' (debit + kredit, satu baris masing-masing)
melalui db.insert_jurnal yang memvalidasi balance. Akun WAJIB dipilih dari
bagan akun (chart of accounts) sehingga tidak pernah keluar dari 15 akun resmi.
Semua transaksi (termasuk data contoh) dapat diedit lewat modal popup atau
dihapus; tersedia tombol reset ke data awal untuk mengembalikan 20 transaksi
contoh.
"""
import datetime

import streamlit as st

import accounting as acc
import database as db
import seed_data
import ui_helpers


def _total_debit(entry):
    """Total debit satu entry (untuk ditampilkan ringkas)."""
    return sum((ln["debit"] for ln in entry["lines"]), acc.NOL)


@st.dialog("✏️ Edit Transaksi")
def _dialog_edit_transaksi(conn, entry, chart, label_fn):
    """Modal popup untuk edit satu transaksi. Pre-fill dari nilai saat ini.

    Dipanggil di dalam handler tombol Edit sehingga Streamlit membuka dialog
    mengambang di tengah layar. Saat simpan dengan debit==kredit transaksi
    diperbarui lalu dialog ditutup via st.rerun(); bila debit!=kredit pesan
    error ditampilkan dan dialog tetap terbuka (tanpa st.rerun()).
    """
    # Entry manual selalu 2 baris: satu debit (>0) dan satu kredit (>0).
    debit_line = next(
        (ln for ln in entry["lines"] if ln["debit"] > acc.NOL), entry["lines"][0]
    )
    kredit_line = next(
        (ln for ln in entry["lines"] if ln["kredit"] > acc.NOL), entry["lines"][-1]
    )
    idx_debit = next((i for i, a in enumerate(chart) if a["kode"] == debit_line["kode"]), 0)
    idx_kredit = next((i for i, a in enumerate(chart) if a["kode"] == kredit_line["kode"]), 0)
    try:
        tgl_awal = datetime.date.fromisoformat(entry["tanggal"])
    except (ValueError, TypeError):
        tgl_awal = datetime.date.today()

    did = entry["db_id"]
    st.markdown(f"### ✏️ Edit Transaksi `{entry['id']}`")
    st.caption("Akun dipilih dari bagan akun resmi. Debit harus sama dengan kredit.")
    with st.form("form_edit_transaksi"):
        tanggal = st.date_input("Tanggal", value=tgl_awal, key=f"edit_tanggal_{did}")
        keterangan = st.text_input(
            "Keterangan", value=entry["keterangan"], key=f"edit_keterangan_{did}"
        )

        st.markdown("**Baris Debit**")
        kol_d1, kol_d2 = st.columns([2, 1])
        with kol_d1:
            akun_debit = st.selectbox(
                "Akun Debit", chart, format_func=label_fn,
                index=idx_debit, key=f"edit_akun_debit_{did}",
            )
        with kol_d2:
            nominal_debit = st.number_input(
                "Nominal Debit", min_value=0, step=1000,
                value=int(debit_line["debit"]), key=f"edit_nominal_debit_{did}",
            )

        st.markdown("**Baris Kredit**")
        kol_k1, kol_k2 = st.columns([2, 1])
        with kol_k1:
            akun_kredit = st.selectbox(
                "Akun Kredit", chart, format_func=label_fn,
                index=idx_kredit, key=f"edit_akun_kredit_{did}",
            )
        with kol_k2:
            nominal_kredit = st.number_input(
                "Nominal Kredit", min_value=0, step=1000,
                value=int(kredit_line["kredit"]), key=f"edit_nominal_kredit_{did}",
            )

        kol_simpan, kol_batal = st.columns(2)
        with kol_simpan:
            simpan = st.form_submit_button("💾 Simpan Perubahan")
        with kol_batal:
            batal = st.form_submit_button("Batal")

    if batal:
        # Tutup dialog tanpa perubahan.
        st.rerun()

    if simpan:
        lines = [
            {
                "kode": akun_debit["kode"],
                "akun": akun_debit["akun"],
                "debit": int(nominal_debit),
                "kredit": 0,
            },
            {
                "kode": akun_kredit["kode"],
                "akun": akun_kredit["akun"],
                "debit": 0,
                "kredit": int(nominal_kredit),
            },
        ]
        try:
            db.update_jurnal(conn, did, tanggal.isoformat(), keterangan, lines)
        except ValueError as e:
            # Tetap di dalam dialog agar pesan error terlihat (jangan st.rerun()).
            st.error(str(e))
        else:
            st.success("Transaksi berhasil diperbarui.")
            st.rerun()


def render_input(conn):
    """Render halaman input transaksi manual + kelola/edit/hapus + reset."""
    st.markdown("## ✏️ Input Transaksi")
    st.caption(
        "Setiap transaksi terdiri dari satu baris debit dan satu baris kredit. "
        "Nominal debit harus sama dengan nominal kredit agar jurnal seimbang."
    )

    chart = seed_data.get_chart_of_accounts()

    def _label(a):
        return f"{a['kode']} - {a['akun']}"

    # ----------------------------------------------------------------- form
    with st.form("form_input_transaksi", clear_on_submit=True):
        tanggal = st.date_input("Tanggal", value=datetime.date.today())
        keterangan = st.text_input("Keterangan", placeholder="Contoh: Pembelian benih padi")

        st.markdown("**Baris Debit**")
        kol_d1, kol_d2 = st.columns([2, 1])
        with kol_d1:
            akun_debit = st.selectbox(
                "Akun Debit", chart, format_func=_label, key="akun_debit"
            )
        with kol_d2:
            nominal_debit = st.number_input(
                "Nominal Debit", min_value=0, step=1000, key="nominal_debit"
            )

        st.markdown("**Baris Kredit**")
        kol_k1, kol_k2 = st.columns([2, 1])
        with kol_k1:
            akun_kredit = st.selectbox(
                "Akun Kredit", chart, format_func=_label, key="akun_kredit"
            )
        with kol_k2:
            nominal_kredit = st.number_input(
                "Nominal Kredit", min_value=0, step=1000, key="nominal_kredit"
            )

        simpan = st.form_submit_button("Simpan Transaksi")

    if simpan:
        lines = [
            {
                "kode": akun_debit["kode"],
                "akun": akun_debit["akun"],
                "debit": int(nominal_debit),
                "kredit": 0,
            },
            {
                "kode": akun_kredit["kode"],
                "akun": akun_kredit["akun"],
                "debit": 0,
                "kredit": int(nominal_kredit),
            },
        ]
        try:
            db.insert_jurnal(
                conn,
                tanggal.isoformat(),
                keterangan,
                lines,
                tipe="umum",
            )
        except ValueError as e:
            st.error(str(e))
        else:
            st.success("Transaksi berhasil disimpan.")
            st.rerun()

    st.divider()

    # -------------------------------------------------------- daftar jurnal
    entries = db.get_jurnal_umum(conn)

    st.markdown("### 📋 Daftar Transaksi")
    ui_helpers.tabel_jurnal(entries)

    # ----------------------------------------------------- kelola transaksi
    st.markdown("### 🗂️ Kelola Transaksi")
    st.caption(
        "Semua transaksi (termasuk data contoh) dapat diedit lewat popup atau "
        "dihapus. Gunakan tombol \"Reset ke Data Awal\" di bawah untuk "
        "mengembalikan 20 transaksi contoh."
    )

    for e in entries:
        kol_info, kol_edit, kol_hapus = st.columns([5, 1, 1])
        with kol_info:
            st.markdown(
                f"**{e['id']}** · {e['tanggal']} · {e['keterangan']} "
                f"· {acc.format_rupiah(_total_debit(e))}"
            )
        with kol_edit:
            if st.button("✏️ Edit", key=f"edit_{e['db_id']}"):
                _dialog_edit_transaksi(conn, e, chart, _label)
        with kol_hapus:
            if st.button("🗑️ Hapus", key=f"hapus_{e['db_id']}"):
                db.hapus_jurnal(conn, e["db_id"])
                st.rerun()

    st.divider()

    # ----------------------------------------------------------- reset data
    with st.expander("⚠️ Reset ke Data Awal"):
        st.warning(
            "Tindakan ini menghapus SEMUA transaksi (termasuk tambahan) lalu "
            "mengembalikan 20 transaksi data awal. Tidak dapat dibatalkan."
        )
        konfirmasi = st.checkbox(
            "Saya mengerti, kembalikan ke data awal", key="konfirmasi_reset"
        )
        if st.button("Reset Sekarang", disabled=not konfirmasi, key="tombol_reset"):
            db.reset_jurnal(conn)
            st.rerun()
