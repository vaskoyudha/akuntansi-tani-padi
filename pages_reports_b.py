"""
pages_reports_b.py
==================
Halaman laporan tahap 4-6 untuk aplikasi akuntansi usaha tani padi:

  4. Jurnal Penyesuaian
  5. Neraca Saldo Setelah Penyesuaian
  6. Laporan Laba Rugi

Modul READ-ONLY: seluruh perhitungan didelegasikan ke accounting.py dan
penyajian tabel/badge ke ui_helpers.py. Tidak menulis ke database, tidak
menyuntikkan CSS sendiri (app.py yang memanggil ui_helpers.inject_css), dan
tidak membuat koneksi DB. Tema light aksen hijau #1F7A4D.

Setiap fungsi render menerima `data` (hasil ui_helpers.get_data) sebagai
argumen. Tahap 5 & 6 wajib memakai `data["disesuaikan"]` (jurnal + AJP).
"""
import pandas as pd
import streamlit as st

import accounting as acc
import ui_helpers


# ---------------------------------------------------------------------------
# 4. Jurnal Penyesuaian
# ---------------------------------------------------------------------------
def render_jurnal_penyesuaian(data):
    """Tampilkan jurnal penyesuaian akhir periode (AJP) + penjelasannya."""
    ui_helpers.section_header(
        "Jurnal Penyesuaian",
        "\U0001F527",
        "Penyesuaian akhir periode agar saldo akun mencerminkan kondisi riil.",
    )

    ajp = acc.get_jurnal_penyesuaian()
    ui_helpers.tabel_jurnal(ajp)

    st.markdown(
        """
        <div class="ajp-note">
            <strong>AJP1 &mdash; Pemakaian perlengkapan (karung)</strong><br>
            Saat panen, seluruh karung gabah senilai
            <strong>Rp&nbsp;100.000</strong> terpakai habis sehingga perlengkapan
            diakui sebagai beban periode berjalan.<br>
            <span class="ajp-entry">Debit: Beban Perlengkapan &nbsp;Rp&nbsp;100.000</span>
            &nbsp;&middot;&nbsp;
            <span class="ajp-entry">Kredit: Perlengkapan &nbsp;Rp&nbsp;100.000</span>
        </div>
        <style>
        .ajp-note {
            background: #f4f7f5;
            border-left: 4px solid #1F7A4D;
            border-radius: 8px;
            padding: 14px 16px;
            margin-top: 14px;
            color: #1A2B23;
            font-size: 0.92rem;
            line-height: 1.6;
        }
        .ajp-note .ajp-entry {
            display: inline-block;
            font-weight: 600;
            color: #1F7A4D;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# 5. Neraca Saldo Setelah Penyesuaian
# ---------------------------------------------------------------------------
def render_ns_penyesuaian(data):
    """Tampilkan neraca saldo setelah memasukkan jurnal penyesuaian."""
    ui_helpers.section_header(
        "Neraca Saldo Setelah Penyesuaian",
        "\u2696\uFE0F",
        "Saldo seluruh akun setelah jurnal penyesuaian diposting.",
    )

    ns = acc.neraca_saldo(data["disesuaikan"])
    ui_helpers.tabel_neraca_saldo(ns)
    ui_helpers.badge_seimbang(ns["total_debit"], ns["total_kredit"])


# ---------------------------------------------------------------------------
# 6. Laporan Laba Rugi
# ---------------------------------------------------------------------------
def _tabel_lr_section(rows, label_kolom, total):
    """Render satu seksi (pendapatan / beban) sebagai tabel + baris TOTAL."""
    data_rows = []
    for r in rows:
        data_rows.append({
            "Akun": r.get("akun", ""),
            label_kolom: acc.format_rupiah(r.get("nilai", 0)),
        })
    data_rows.append({
        "Akun": "TOTAL",
        label_kolom: acc.format_rupiah(total),
    })
    df = pd.DataFrame(data_rows, columns=["Akun", label_kolom])
    st.markdown(
        ui_helpers.tabel_html(
            df, right_cols=[label_kolom], total_row_label="TOTAL"
        ),
        unsafe_allow_html=True,
    )


def render_laba_rugi(data):
    """Tampilkan laporan laba rugi dari jurnal yang sudah disesuaikan."""
    ui_helpers.section_header(
        "Laporan Laba Rugi",
        "\U0001F4C8",
        "Selisih total pendapatan dan total beban periode berjalan.",
    )

    lr = acc.laba_rugi(data["disesuaikan"])

    st.markdown("##### Pendapatan")
    _tabel_lr_section(lr["pendapatan_rows"], "Jumlah", lr["total_pendapatan"])

    st.markdown("##### Beban")
    _tabel_lr_section(lr["beban_rows"], "Jumlah", lr["total_beban"])

    laba = lr["laba_bersih"]
    laba_str = acc.format_rupiah(laba)
    surplus = laba >= 0
    judul = "Laba Bersih" if surplus else "Rugi Bersih"
    aksen = "#1F7A4D" if surplus else "#b42318"

    st.markdown(
        f"""
        <div class="lr-card" style="--lr-accent: {aksen};">
            <div class="lr-card-label">{judul}</div>
            <div class="lr-card-value">{laba_str}</div>
            <div class="lr-card-sub">
                Pendapatan {acc.format_rupiah(lr["total_pendapatan"])}
                &minus; Beban {acc.format_rupiah(lr["total_beban"])}
            </div>
        </div>
        <style>
        .lr-card {{
            background: linear-gradient(135deg, #e7f6ee 0%, #f4f7f5 100%);
            border: 1px solid #b6e2c8;
            border-left: 6px solid var(--lr-accent);
            border-radius: 12px;
            padding: 20px 24px;
            margin-top: 18px;
            box-shadow: 0 2px 8px rgba(31, 122, 77, 0.10);
        }}
        .lr-card-label {{
            font-size: 0.85rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: #667085;
            margin-bottom: 6px;
        }}
        .lr-card-value {{
            font-size: 2.1rem;
            font-weight: 800;
            color: var(--lr-accent);
            line-height: 1.15;
        }}
        .lr-card-sub {{
            margin-top: 8px;
            font-size: 0.88rem;
            color: #1A2B23;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
