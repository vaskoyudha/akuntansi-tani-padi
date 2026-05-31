"""
pages_auth.py
=============
Halaman otentikasi (login + register) untuk aplikasi Akuntansi Usaha Tani Padi.

Modul ini READ-ONLY terhadap backend: ia hanya memanggil fungsi yang sudah ada
di `auth.py` (login/register) dan tidak pernah mengimplementasikan ulang hashing,
validasi, atau menyentuh database secara langsung. Koneksi DB diterima sebagai
argumen `conn` (dibuat & dikelola oleh app.py).

Fungsi entry: `render_auth(conn)` — menampilkan dua tab ("Masuk" / "Daftar").
"""
import streamlit as st

import auth


# ---------------------------------------------------------------------------
# Judul aplikasi (ditampilkan di atas form auth)
# ---------------------------------------------------------------------------
def _judul_aplikasi():
    """Render hero berbranding (logo + judul + tagline) di atas form otentikasi.

    HTML bersifat literal statis (tanpa interpolasi nilai dinamis) dan memakai
    kelas .ajp-auth-* yang didefinisikan di ui_helpers.inject_css().
    """
    st.markdown(
        """
        <div class="ajp-auth-hero">
            <div class="ajp-auth-logo">🌾</div>
            <h1 class="ajp-auth-title">Akuntansi Tani Padi</h1>
            <p class="ajp-auth-tagline">Sistem Informasi Akuntansi Usaha Tani Padi</p>
            <div class="ajp-auth-divider"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Tab Login
# ---------------------------------------------------------------------------
def render_login(conn):
    """
    Render form login. Sukses → simpan info user ke session_state & rerun.

    Hanya info user (id/username/nama) dari `auth.login` yang disimpan ke
    session_state; password polos tidak pernah disimpan.
    """
    with st.form("form_login"):
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        masuk = st.form_submit_button("Masuk", use_container_width=True)

    if masuk:
        ok, info = auth.login(conn, username, password)
        if ok:
            st.session_state.user = info
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Username atau password salah.")

    st.caption("Akun demo: admin / admin123")


# ---------------------------------------------------------------------------
# Tab Register
# ---------------------------------------------------------------------------
def render_register(conn):
    """
    Render form pendaftaran. Memanggil `auth.register` dan menampilkan pesan
    sesuai return tuple `(bool, str)`. Setelah sukses, arahkan user untuk login.
    """
    with st.form("form_register"):
        username = st.text_input("Username", key="register_username")
        password = st.text_input(
            "Password",
            type="password",
            key="register_password",
            help="Minimal 6 karakter.",
        )
        nama = st.text_input("Nama lengkap", key="register_nama")
        daftar = st.form_submit_button("Daftar", use_container_width=True)

    if daftar:
        ok, pesan = auth.register(conn, username, password, nama)
        if ok:
            st.success(f"{pesan} Silakan masuk lewat tab \"Masuk\".")
        else:
            st.error(pesan)


# ---------------------------------------------------------------------------
# Entry point: dipanggil oleh app.py saat belum login
# ---------------------------------------------------------------------------
def render_auth(conn):
    """
    Entry point halaman otentikasi.

    Menampilkan judul aplikasi lalu dua tab ("Masuk" / "Daftar") di kolom tengah.
    Dipanggil oleh app.py ketika `st.session_state.logged_in` bernilai False.
    """
    kiri, tengah, kanan = st.columns([1, 2, 1])
    with tengah:
        _judul_aplikasi()
        with st.container(border=True):
            tab_masuk, tab_daftar = st.tabs(["Masuk", "Daftar"])
            with tab_masuk:
                render_login(conn)
            with tab_daftar:
                render_register(conn)
