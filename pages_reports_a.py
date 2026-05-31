"""
pages_reports_a.py
==================
Halaman laporan tahap 1-3 siklus akuntansi usaha tani padi:
  1. Jurnal Umum
  2. Buku Besar
  3. Neraca Saldo

Modul READ-ONLY. Seluruh perhitungan didelegasikan ke accounting.py;
data jurnal umum MURNI dipakai (data['jurnal'], sebelum penyesuaian).
Setiap fungsi menerima `data` (hasil ui_helpers.get_data) sebagai argumen.
"""
from decimal import Decimal

import pandas as pd
import streamlit as st

import accounting as acc
import ui_helpers

D = Decimal


# ---------------------------------------------------------------------------
# Helper format uang lokal (blank untuk nilai nol agar tabel bersih)
# ---------------------------------------------------------------------------
def _rp_atau_kosong(nilai):
    """Format rupiah; kembalikan string kosong bila nilai <= 0."""
    if nilai is None:
        return ""
    if D(nilai) > D("0"):
        return acc.format_rupiah(nilai)
    return ""


# ---------------------------------------------------------------------------
# 1. Jurnal Umum
# ---------------------------------------------------------------------------
def render_jurnal_umum(data):
    """Tampilkan jurnal umum murni + badge keseimbangan total debit/kredit."""
    st.subheader("1. Jurnal Umum")
    st.caption(
        "Pencatatan kronologis seluruh transaksi sebelum penyesuaian "
        f"({len(data['jurnal'])} transaksi)."
    )

    ui_helpers.tabel_jurnal(data["jurnal"])

    total_debit, total_kredit = acc.total_jurnal(data["jurnal"])
    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.markdown(
            f"**Total Debit:** {acc.format_rupiah(total_debit)} &nbsp;&nbsp; "
            f"**Total Kredit:** {acc.format_rupiah(total_kredit)}"
        )
    with col_b:
        ui_helpers.badge_seimbang(total_debit, total_kredit)


# ---------------------------------------------------------------------------
# 2. Buku Besar
# ---------------------------------------------------------------------------
def render_buku_besar(data):
    """Tampilkan mutasi & saldo akhir tiap akun (urut by kode), dari engine."""
    st.subheader("2. Buku Besar")
    st.caption("Pengelompokan mutasi per akun beserta saldo berjalan.")

    besar = acc.buku_besar(data["jurnal"])

    # urut akun berdasarkan kode
    for nama in sorted(besar, key=lambda n: besar[n]["kode"]):
        info = besar[nama]
        kode = info.get("kode", "")
        judul = f"{kode} — {nama}" if kode else nama

        with st.expander(judul, expanded=False):
            rows = []
            for m in info["mutasi"]:
                rows.append({
                    "Tanggal": m.get("tanggal", ""),
                    "Keterangan": m.get("keterangan", ""),
                    "Debit": _rp_atau_kosong(m["debit"]),
                    "Kredit": _rp_atau_kosong(m["kredit"]),
                    # saldo berjalan dari engine (D-K kumulatif)
                    "Saldo Berjalan": acc.format_rupiah(m["saldo"]),
                })
            df = pd.DataFrame(
                rows,
                columns=["Tanggal", "Keterangan", "Debit", "Kredit", "Saldo Berjalan"],
            )
            st.dataframe(df, hide_index=True, use_container_width=True)

            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.markdown(f"**Total Debit:** {acc.format_rupiah(info['total_debit'])}")
            with col_b:
                st.markdown(f"**Total Kredit:** {acc.format_rupiah(info['total_kredit'])}")
            with col_c:
                st.markdown(f"**Saldo Akhir:** {acc.format_rupiah(info['saldo_akhir'])}")


# ---------------------------------------------------------------------------
# 3. Neraca Saldo
# ---------------------------------------------------------------------------
def render_neraca_saldo(data):
    """Tampilkan neraca saldo jurnal umum + badge keseimbangan (52.500.000)."""
    st.subheader("3. Neraca Saldo")
    st.caption("Ringkasan saldo seluruh akun; total debit harus sama dengan total kredit.")

    ns = acc.neraca_saldo(data["jurnal"])
    ui_helpers.tabel_neraca_saldo(ns)
    ui_helpers.badge_seimbang(ns["total_debit"], ns["total_kredit"])
