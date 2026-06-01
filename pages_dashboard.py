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
import database as db
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

    # --- Header: banner berbranding + sambutan ----------------------------
    user = st.session_state.get("user") or {}
    nama = user.get("nama") or user.get("username") or "Petani"

    # Banner = HTML literal STATIS (tanpa interpolasi nilai dinamis) demi
    # keamanan: unsafe_allow_html mem-bypass escaping.
    st.markdown(
        """
        <div style="
            background: linear-gradient(120deg, #1F7A4D 0%, #2E9966 55%, #4FB07C 100%);
            border-radius: 16px;
            padding: 1.5rem 1.75rem;
            margin-bottom: 1rem;
            box-shadow: 0 6px 18px rgba(31,122,77,.22);
            color: #FFFFFF;
        ">
            <h1 style="margin:0;font-size:1.9rem;font-weight:700;color:#FFFFFF;">
                🌾 Dashboard
            </h1>
            <p style="margin:0.3rem 0 0;font-size:1.02rem;color:#E8F5EE;">
                Ringkasan keuangan usaha tani padi periode ini.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    # Sambutan personal: markdown polos (auto-escape) — nama TIDAK masuk HTML mentah.
    st.markdown(f"Selamat datang kembali, **{nama}**.")
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

    # --- Ringkasan stok (informasi persediaan, BUKAN akun aset) -----------
    # Data stok diambil langsung dari koneksi (db.get_stok_ringkasan), TIDAK
    # lewat get_data(): alur jurnal/laporan keuangan tetap terpisah dari stok.
    st.divider()
    ui_helpers.section_header("Ringkasan Stok", "📦")

    ringkasan = db.get_stok_ringkasan(conn)
    total_nilai = sum((r["nilai"] for r in ringkasan), acc.NOL)
    menipis = sum(1 for r in ringkasan if r["is_low"])

    s1, s2, s3 = st.columns(3)
    with s1:
        ui_helpers.kartu_statistik(
            "Jenis Item Stok", f"{len(ringkasan)} item", "📦"
        )
    with s2:
        ui_helpers.kartu_statistik(
            "Item Menipis", f"{menipis} item", "⚠️"
        )
    with s3:
        ui_helpers.kartu_statistik(
            "Total Nilai Stok", acc.format_rupiah(total_nilai), "💰"
        )

    st.caption(
        "Nilai stok bersifat informasi persediaan, bukan akun aset di "
        "laporan keuangan."
    )
