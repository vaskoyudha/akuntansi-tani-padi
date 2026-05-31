"""
app.py
======
Titik masuk (entry point) aplikasi Streamlit "Akuntansi Usaha Tani Padi".

Tugas modul ini murni integrasi/routing: mengatur konfigurasi halaman,
membuka satu koneksi database (di-cache), menyuntik CSS sekali, menjaga
gerbang login, lalu mengarahkan pilihan menu sidebar ke fungsi render
halaman yang sesuai. Tidak ada logika akuntansi atau penulisan DB di sini —
semuanya didelegasikan ke modul halaman & backend yang sudah ada.

Alur:
  set_page_config -> inject_css -> get_conn (cached) ->
  gerbang login (render_auth bila belum login) ->
  sidebar (user + logout + menu) -> dispatch ke render halaman terpilih.
"""
import html

import streamlit as st

import auth
import database as db
import pages_auth
import pages_dashboard
import pages_input
import pages_reports_a
import pages_reports_b
import pages_reports_c
import pages_reports_d
import ui_helpers


# ---------------------------------------------------------------------------
# Konfigurasi halaman — WAJIB jadi panggilan Streamlit pertama
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Akuntansi Tani Padi",
    page_icon="🌾",
    layout="wide",
)

# CSS scoped (kartu statistik, badge, poles tabel) — disuntik sekali di awal.
ui_helpers.inject_css()


# ---------------------------------------------------------------------------
# Koneksi database tunggal (cache_resource: dibuat sekali untuk seumur app)
# ---------------------------------------------------------------------------
@st.cache_resource
def get_conn():
    """Buka koneksi, siapkan skema, seed data & user default. Sekali saja.

    create_connection memakai check_same_thread=False sehingga aman dipakai
    lintas thread oleh Streamlit dalam pola cache_resource.
    """
    conn = db.create_connection()
    db.create_tables(conn)
    db.seed_database(conn)
    auth.seed_default_user(conn)
    return conn


# ---------------------------------------------------------------------------
# Urutan menu sidebar (FIXED — jangan diubah/diurut ulang)
# ---------------------------------------------------------------------------
MENU = [
    "🏠 Dashboard",
    "1. Jurnal Umum",
    "2. Buku Besar",
    "3. Neraca Saldo",
    "4. Jurnal Penyesuaian",
    "5. NS Setelah Penyesuaian",
    "6. Laporan Laba Rugi",
    "7. Perubahan Ekuitas",
    "8. Posisi Keuangan",
    "9. Arus Kas",
    "10. Jurnal Penutup",
    "11. NS Setelah Penutupan",
    "✏️ Input Transaksi",
]


def _render_sidebar():
    """Render sidebar (sapaan user + tombol logout + menu) → kembalikan pilihan."""
    user = st.session_state.get("user") or {}
    nama = user.get("nama") or user.get("username") or "Petani"
    nama_safe = html.escape(str(nama))

    with st.sidebar:
        st.markdown(
            f"""
            <div class="ajp-sidebar-brand">
                <span class="ajp-sidebar-brand-icon">🌾</span>
                <span class="ajp-sidebar-brand-text">
                    <span class="ajp-sidebar-brand-title">Akuntansi Tani Padi</span>
                    <span class="ajp-sidebar-brand-sub">Usaha Tani Padi</span>
                </span>
            </div>
            <div class="ajp-sidebar-user">
                <span class="ajp-sidebar-user-glyph">👤</span>
                <span>Masuk sebagai <strong>{nama_safe}</strong></span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("🚪 Keluar", use_container_width=True):
            st.session_state.clear()
            st.rerun()

        st.divider()
        pilihan = st.radio("Navigasi", MENU, label_visibility="collapsed")

    return pilihan


def _dispatch(pilihan, conn, data):
    """Arahkan pilihan menu ke fungsi render halaman yang sesuai.

    Halaman laporan menerima `data` (hasil ui_helpers.get_data); halaman
    Dashboard & Input menerima `conn`.
    """
    if pilihan == "🏠 Dashboard":
        pages_dashboard.render_dashboard(conn, data)
    elif pilihan == "1. Jurnal Umum":
        pages_reports_a.render_jurnal_umum(data)
    elif pilihan == "2. Buku Besar":
        pages_reports_a.render_buku_besar(data)
    elif pilihan == "3. Neraca Saldo":
        pages_reports_a.render_neraca_saldo(data)
    elif pilihan == "4. Jurnal Penyesuaian":
        pages_reports_b.render_jurnal_penyesuaian(data)
    elif pilihan == "5. NS Setelah Penyesuaian":
        pages_reports_b.render_ns_penyesuaian(data)
    elif pilihan == "6. Laporan Laba Rugi":
        pages_reports_b.render_laba_rugi(data)
    elif pilihan == "7. Perubahan Ekuitas":
        pages_reports_c.render_ekuitas(data)
    elif pilihan == "8. Posisi Keuangan":
        pages_reports_c.render_posisi_keuangan(data)
    elif pilihan == "9. Arus Kas":
        pages_reports_c.render_arus_kas(data)
    elif pilihan == "10. Jurnal Penutup":
        pages_reports_d.render_jurnal_penutup(data)
    elif pilihan == "11. NS Setelah Penutupan":
        pages_reports_d.render_ns_penutupan(data)
    elif pilihan == "✏️ Input Transaksi":
        pages_input.render_input(conn)


# ---------------------------------------------------------------------------
# Alur utama
# ---------------------------------------------------------------------------
def main():
    conn = get_conn()

    # Inisialisasi state login.
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    # Gerbang login: belum masuk → hanya halaman auth, lalu berhenti.
    if not st.session_state.get("logged_in"):
        pages_auth.render_auth(conn)
        st.stop()

    # Sudah login: sidebar + halaman terpilih.
    pilihan = _render_sidebar()
    data = ui_helpers.get_data(conn)
    _dispatch(pilihan, conn, data)


main()
