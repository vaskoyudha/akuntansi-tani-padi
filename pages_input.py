"""
pages_input.py
==============
Halaman form input transaksi jurnal manual (guardrail-kritis).

Hanya menulis jurnal bertipe 'umum' (debit + kredit, satu baris masing-masing)
melalui db.insert_jurnal yang memvalidasi balance. Akun WAJIB dipilih dari
bagan akun (chart of accounts) sehingga tidak pernah keluar dari 15 akun resmi.
Transaksi seed (T01-T20) read-only; transaksi tambahan bisa dihapus; tersedia
tombol reset ke data awal.
"""
import datetime

import streamlit as st

import accounting as acc
import database as db
import seed_data
import ui_helpers


def _seed_codes():
    """Himpunan kode jurnal seed (T01-T20) untuk membedakan seed vs tambahan."""
    return {e["id"] for e in seed_data.get_jurnal_seed()}


def _total_debit(entry):
    """Total debit satu entry (untuk ditampilkan ringkas)."""
    return sum((ln["debit"] for ln in entry["lines"]), acc.NOL)


def render_input(conn):
    """Render halaman input transaksi manual + kelola/hapus + reset."""
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
    seed_codes = _seed_codes()

    st.markdown("### 📋 Daftar Transaksi")
    ui_helpers.tabel_jurnal(entries)

    # ----------------------------------------------------- kelola tambahan
    st.markdown("### 🗂️ Kelola Transaksi")
    st.caption("Transaksi data awal (T01-T20) terkunci. Hanya transaksi tambahan yang dapat dihapus.")

    for e in entries:
        is_seed = e["id"] in seed_codes
        kol_info, kol_aksi = st.columns([5, 1])
        with kol_info:
            st.markdown(
                f"**{e['id']}** · {e['tanggal']} · {e['keterangan']} "
                f"· {acc.format_rupiah(_total_debit(e))}"
            )
        with kol_aksi:
            if is_seed:
                st.caption("🔒 data awal")
            else:
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
