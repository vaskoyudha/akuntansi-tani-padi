"""
pages_reports_d.py
==================
Halaman laporan tahap 10-11 siklus akuntansi usaha tani padi:

  10. Jurnal Penutup
  11. Neraca Saldo Setelah Penutupan

Modul READ-ONLY: tidak menulis ke database, tidak menghitung ulang akuntansi.
Seluruh angka diambil dari `data` (hasil ui_helpers.get_data) dan engine
accounting.py. Render via helper di ui_helpers.py. Tema light aksen hijau
(#1F7A4D); CSS disuntik sekali oleh app.py (bukan di sini).
"""
import streamlit as st

import accounting as acc
import ui_helpers


# ---------------------------------------------------------------------------
# 10. Jurnal Penutup
# ---------------------------------------------------------------------------
def render_jurnal_penutup(data):
    """
    Tahap 10 — tampilkan jurnal penutup (4 entri JP1-JP4) dari data['penutup'].

    Tidak menulis ke DB dan tidak menghitung ulang: data['penutup'] sudah berisi
    hasil acc.jurnal_penutup(disesuaikan).
    """
    st.subheader("10. Jurnal Penutup")
    st.markdown(
        "Jurnal penutup memindahkan saldo **akun nominal** (pendapatan, beban, "
        "dan prive) ke modal pada akhir periode, sehingga akun nominal kembali "
        "bersaldo nol untuk periode berikutnya."
    )

    ui_helpers.tabel_jurnal(data["penutup"])

    laba = acc.format_rupiah("11500000")
    prive = acc.format_rupiah("4500000")
    st.markdown(
        f"""
**Empat langkah penutupan:**

- **JP1 — Tutup pendapatan.** Seluruh akun pendapatan didebit, lawannya
  dikreditkan ke akun **Ikhtisar Laba Rugi**.
- **JP2 — Tutup beban.** Seluruh akun beban dikredit, lawannya didebitkan
  ke akun **Ikhtisar Laba Rugi**.
- **JP3 — Tutup ikhtisar ke modal.** Selisih ikhtisar (laba bersih
  **{laba}**) dipindahkan ke akun **Modal Petani**.
- **JP4 — Tutup prive ke modal.** Saldo prive **{prive}** mengurangi
  **Modal Petani**.
        """
    )


# ---------------------------------------------------------------------------
# 11. Neraca Saldo Setelah Penutupan
# ---------------------------------------------------------------------------
def render_ns_penutupan(data):
    """
    Tahap 11 — neraca saldo setelah penutupan.

    Dihitung oleh engine: acc.neraca_saldo_setelah_penutupan(setelah_penutupan).
    Hanya memuat akun riil (aset, kewajiban, ekuitas); akun nominal sudah
    ditutup ke nol.
    """
    st.subheader("11. Neraca Saldo Setelah Penutupan")
    st.markdown(
        "Setelah jurnal penutup diposting, hanya tersisa **akun riil** "
        "(aset, kewajiban, dan ekuitas). Total debit harus tetap sama dengan "
        "total kredit."
    )

    ns = acc.neraca_saldo_setelah_penutupan(data["setelah_penutupan"])
    ui_helpers.tabel_neraca_saldo(ns)
    ui_helpers.badge_seimbang(ns["total_debit"], ns["total_kredit"])

    st.caption(
        "Catatan: neraca saldo ini hanya berisi akun riil. Akun nominal "
        "(Pendapatan dan Beban) sudah bersaldo nol karena telah ditutup ke "
        "modal pada jurnal penutup, sehingga tidak lagi muncul di sini."
    )
