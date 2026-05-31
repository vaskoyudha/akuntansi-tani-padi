"""
pages_reports_c.py
==================
Halaman laporan tahap 7-9 siklus akuntansi usaha tani padi:

  7. Laporan Perubahan Ekuitas
  8. Laporan Posisi Keuangan (Neraca)
  9. Laporan Arus Kas

Modul READ-ONLY: seluruh perhitungan didelegasikan ke accounting.py
(menggunakan jurnal yang SUDAH DISESUAIKAN, yaitu data['disesuaikan']).
Halaman ini hanya menyajikan hasil engine; tidak menulis DB, tidak
menghitung ulang klasifikasi, tidak menyuntik CSS (tugas app.py).
"""
import pandas as pd
import streamlit as st

import accounting as acc
import ui_helpers


# ---------------------------------------------------------------------------
# 7. Laporan Perubahan Ekuitas
# ---------------------------------------------------------------------------
def render_ekuitas(data):
    """Tampilkan laporan perubahan ekuitas bertingkat dari jurnal disesuaikan."""
    st.subheader("7. Laporan Perubahan Ekuitas")
    st.caption("Periode panen 2025 — disusun dari jurnal yang telah disesuaikan.")

    eq = acc.perubahan_ekuitas(data["disesuaikan"])

    rows = [
        {"Keterangan": "Modal Awal", "Jumlah": acc.format_rupiah(eq["modal_awal"])},
        {"Keterangan": "Laba Bersih (+)", "Jumlah": acc.format_rupiah(eq["laba_bersih"])},
        {"Keterangan": "Prive (\u2212)", "Jumlah": acc.format_rupiah(eq["prive"])},
        {"Keterangan": "Modal Akhir", "Jumlah": acc.format_rupiah(eq["modal_akhir"])},
    ]
    df = pd.DataFrame(rows, columns=["Keterangan", "Jumlah"])
    st.dataframe(df, hide_index=True, use_container_width=True)

    st.markdown(
        f"<p style='color:#667085;font-size:0.9rem;'>"
        f"Modal Awal {acc.format_rupiah(eq['modal_awal'])} "
        f"+ Laba Bersih {acc.format_rupiah(eq['laba_bersih'])} "
        f"\u2212 Prive {acc.format_rupiah(eq['prive'])} "
        f"= <strong style='color:#1F7A4D;'>Modal Akhir "
        f"{acc.format_rupiah(eq['modal_akhir'])}</strong></p>",
        unsafe_allow_html=True,
    )
    ui_helpers.kartu_statistik(
        "Modal Akhir", acc.format_rupiah(eq["modal_akhir"]), ikon="\U0001F4B0"
    )


# ---------------------------------------------------------------------------
# 8. Laporan Posisi Keuangan (Neraca)
# ---------------------------------------------------------------------------
def render_posisi_keuangan(data):
    """Tampilkan neraca dua kolom (Aset | Kewajiban + Ekuitas) + badge seimbang."""
    st.subheader("8. Laporan Posisi Keuangan (Neraca)")
    st.caption("Per 30 April 2025 — Aset harus sama dengan Kewajiban + Ekuitas.")

    pk = acc.posisi_keuangan(data["disesuaikan"])

    kol_kiri, kol_kanan = st.columns(2)

    with kol_kiri:
        st.markdown("**Aset**")
        aset = [
            {"Akun": r["akun"], "Jumlah": acc.format_rupiah(r["nilai"])}
            for r in pk["aset_rows"]
        ]
        aset.append(
            {"Akun": "TOTAL ASET", "Jumlah": acc.format_rupiah(pk["total_aset"])}
        )
        df_aset = pd.DataFrame(aset, columns=["Akun", "Jumlah"])
        st.dataframe(df_aset, hide_index=True, use_container_width=True)

    with kol_kanan:
        st.markdown("**Kewajiban & Ekuitas**")
        kanan = [
            {"Akun": r["akun"], "Jumlah": acc.format_rupiah(r["nilai"])}
            for r in pk["kewajiban_rows"]
        ]
        kanan.append(
            {"Akun": "Modal Akhir", "Jumlah": acc.format_rupiah(pk["modal_akhir"])}
        )
        kanan.append(
            {
                "Akun": "TOTAL KEWAJIBAN & EKUITAS",
                "Jumlah": acc.format_rupiah(pk["total_kewajiban_ekuitas"]),
            }
        )
        df_kanan = pd.DataFrame(kanan, columns=["Akun", "Jumlah"])
        st.dataframe(df_kanan, hide_index=True, use_container_width=True)

    st.write("")
    ui_helpers.badge_seimbang(pk["total_aset"], pk["total_kewajiban_ekuitas"])


# ---------------------------------------------------------------------------
# 9. Laporan Arus Kas
# ---------------------------------------------------------------------------
def _seksi_arus(judul, total, rincian):
    """Render satu seksi arus kas (operasi/pendanaan/investasi) + rinciannya."""
    st.markdown(f"**{judul}**")
    rows = [
        {"Keterangan": f"{r['id']} \u2014 {r['keterangan']}", "Jumlah": acc.format_rupiah(r["nilai"])}
        for r in rincian
    ]
    rows.append({"Keterangan": f"Total {judul}", "Jumlah": acc.format_rupiah(total)})
    df = pd.DataFrame(rows, columns=["Keterangan", "Jumlah"])
    st.dataframe(df, hide_index=True, use_container_width=True)


def render_arus_kas(data):
    """Tampilkan arus kas metode langsung (operasi/pendanaan/investasi) apa adanya."""
    st.subheader("9. Laporan Arus Kas")
    st.caption("Metode langsung — klasifikasi mengikuti engine accounting.py.")

    ak = acc.arus_kas(data["disesuaikan"])

    _seksi_arus("Aktivitas Operasi", ak["operasi"], ak["rincian"]["operasi"])
    _seksi_arus("Aktivitas Pendanaan", ak["pendanaan"], ak["rincian"]["pendanaan"])
    _seksi_arus("Aktivitas Investasi", ak["investasi"], ak["rincian"]["investasi"])

    st.write("")
    ringkas = pd.DataFrame(
        [
            {"Keterangan": "Kenaikan (Penurunan) Kas Bersih", "Jumlah": acc.format_rupiah(ak["kenaikan_kas"])},
            {"Keterangan": "Kas Awal Periode", "Jumlah": acc.format_rupiah(ak["kas_awal"])},
            {"Keterangan": "Kas Akhir Periode", "Jumlah": acc.format_rupiah(ak["kas_akhir"])},
        ],
        columns=["Keterangan", "Jumlah"],
    )
    st.dataframe(ringkas, hide_index=True, use_container_width=True)

    ui_helpers.kartu_statistik(
        "Kas Akhir Periode", acc.format_rupiah(ak["kas_akhir"]), ikon="\U0001F3E6"
    )
