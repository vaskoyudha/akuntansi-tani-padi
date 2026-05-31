"""
pages_dashboard.py
==================
Halaman Dashboard — ringkasan keuangan usaha tani padi dalam kartu statistik.

Menyajikan ikhtisar singkat (pendapatan, beban, laba, modal, kas, jumlah
transaksi) yang seluruhnya dihitung oleh engine accounting.py dari data
jurnal yang sudah disesuaikan. Tidak ada angka yang di-hardcode dan tidak
ada penulisan ke database di sini.

Entry point: render_dashboard(conn, data=None)
"""
import streamlit as st

import accounting as acc
import ui_helpers


def render_dashboard(conn, data=None):
    """Render halaman dashboard kartu statistik.

    Args:
        conn: koneksi SQLite aktif.
        data: hasil ui_helpers.get_data(conn); diambil sendiri bila None.
    """
    if data is None:
        data = ui_helpers.get_data(conn)

    # Sumber perhitungan: jurnal yang sudah disesuaikan (21 entri pada seed).
    disesuaikan = data["disesuaikan"]
    lr = acc.laba_rugi(disesuaikan)
    eq = acc.perubahan_ekuitas(disesuaikan)
    ak = acc.arus_kas(disesuaikan)
    jumlah_transaksi = len(data["jurnal"])

    # --- Header: sambutan + sub-judul -------------------------------------
    user = st.session_state.get("user") or {}
    nama = user.get("nama") or user.get("username") or "Petani"

    st.markdown(
        f"""
        <div style="margin-bottom:0.35rem;">
            <h1 style="margin:0;font-size:1.9rem;font-weight:800;color:#1A2B23;">
                🌾 Dashboard
            </h1>
            <p style="margin:0.25rem 0 0;font-size:1.02rem;color:#41584C;">
                Selamat datang kembali, <strong style="color:#1F7A4D;">{nama}</strong>.
                Berikut ringkasan keuangan usaha tani padi periode ini.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()

    # --- Baris 1: empat metrik utama --------------------------------------
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ui_helpers.kartu_statistik(
            "Total Pendapatan", acc.format_rupiah(lr["total_pendapatan"]), "🌾"
        )
    with c2:
        ui_helpers.kartu_statistik(
            "Total Beban", acc.format_rupiah(lr["total_beban"]), "💸"
        )
    with c3:
        ui_helpers.kartu_statistik(
            "Laba Bersih", acc.format_rupiah(lr["laba_bersih"]), "📈"
        )
    with c4:
        ui_helpers.kartu_statistik(
            "Modal Akhir", acc.format_rupiah(eq["modal_akhir"]), "💰"
        )

    # --- Baris 2: kas akhir + jumlah transaksi ----------------------------
    d1, d2 = st.columns(2)
    with d1:
        ui_helpers.kartu_statistik(
            "Kas Akhir", acc.format_rupiah(ak["kas_akhir"]), "🏦"
        )
    with d2:
        ui_helpers.kartu_statistik(
            "Jumlah Transaksi", f"{jumlah_transaksi} transaksi", "📋"
        )

    st.caption(
        "Angka dihitung otomatis dari jurnal yang telah disesuaikan "
        "(laba rugi, perubahan ekuitas, dan arus kas)."
    )
