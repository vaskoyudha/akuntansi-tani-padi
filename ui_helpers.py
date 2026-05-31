"""
ui_helpers.py
=============
Satu sumber kebenaran alur data laporan + helper render Streamlit.

Modul ini READ-ONLY: tidak pernah menulis ke database. Seluruh perhitungan
akuntansi didelegasikan ke accounting.py; modul ini hanya merangkai data dan
menyajikannya (kartu statistik, badge seimbang, tabel, CSS).

Dipakai oleh seluruh halaman aplikasi (app.py + halaman laporan).
"""
from decimal import Decimal

import pandas as pd
import streamlit as st

import accounting as acc
import database as db

D = Decimal


# ---------------------------------------------------------------------------
# Alur data (satu sumber kebenaran)
# ---------------------------------------------------------------------------
def get_data(conn):
    """
    Bangun seluruh alur data jurnal dari koneksi DB.

    Return dict dengan 4 key:
      jurnal            -> jurnal umum dari DB (20 entri pada data seed)
      disesuaikan       -> jurnal umum + jurnal penyesuaian (21 entri)
      penutup           -> jurnal penutup dari jurnal disesuaikan (4 entri)
      setelah_penutupan -> disesuaikan + penutup
    """
    jurnal = db.get_jurnal_umum(conn)
    disesuaikan = jurnal + acc.get_jurnal_penyesuaian()
    penutup = acc.jurnal_penutup(disesuaikan)
    setelah_penutupan = disesuaikan + penutup
    return {
        "jurnal": jurnal,
        "disesuaikan": disesuaikan,
        "penutup": penutup,
        "setelah_penutupan": setelah_penutupan,
    }


# ---------------------------------------------------------------------------
# Helper format uang
# ---------------------------------------------------------------------------
def _rp_atau_kosong(nilai):
    """Format nilai sebagai rupiah; jika <= 0 kembalikan string kosong."""
    if nilai is None:
        return ""
    if D(nilai) > D("0"):
        return acc.format_rupiah(nilai)
    return ""


# ---------------------------------------------------------------------------
# Render: kartu statistik
# ---------------------------------------------------------------------------
def kartu_statistik(label, nilai_str, ikon=""):
    """Render satu kartu statistik (label kecil + nilai besar) via HTML."""
    ikon_html = f'<span class="stat-card-icon">{ikon}</span>' if ikon else ""
    st.markdown(
        f"""
        <div class="stat-card">
            <div class="stat-card-label">{ikon_html}{label}</div>
            <div class="stat-card-value">{nilai_str}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Render: badge seimbang
# ---------------------------------------------------------------------------
def badge_seimbang(total_debit, total_kredit):
    """Render badge status keseimbangan debit vs kredit."""
    if D(total_debit) == D(total_kredit):
        st.markdown(
            '<span class="badge badge-ok">&#10003; Seimbang</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span class="badge badge-bad">&#10007; Tidak Seimbang</span>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Render: tabel jurnal
# ---------------------------------------------------------------------------
def tabel_jurnal(entries):
    """
    Render daftar jurnal (entries) sebagai tabel flat per baris akun.

    Kolom: Tanggal, Kode, Keterangan, Akun, Debit, Kredit.
    Nilai uang sudah berupa string hasil format_rupiah (bukan Decimal mentah).
    """
    rows = []
    for entry in entries:
        for line in entry["lines"]:
            rows.append({
                "Tanggal": entry.get("tanggal", ""),
                "Kode": entry.get("id", ""),
                "Keterangan": entry.get("keterangan", ""),
                "Akun": line["akun"],
                "Debit": _rp_atau_kosong(line["debit"]),
                "Kredit": _rp_atau_kosong(line["kredit"]),
            })
    df = pd.DataFrame(
        rows,
        columns=["Tanggal", "Kode", "Keterangan", "Akun", "Debit", "Kredit"],
    )
    st.dataframe(df, hide_index=True, use_container_width=True)


# ---------------------------------------------------------------------------
# Render: tabel neraca saldo
# ---------------------------------------------------------------------------
def tabel_neraca_saldo(ns):
    """
    Render neraca saldo sebagai tabel + baris TOTAL.

    `ns` punya keys:
      rows         -> list {kode, akun, debit, kredit}
      total_debit  -> Decimal
      total_kredit -> Decimal
    Nilai uang ditampilkan via format_rupiah.
    """
    rows = []
    for r in ns["rows"]:
        rows.append({
            "Kode": r.get("kode", ""),
            "Akun": r.get("akun", ""),
            "Debit": _rp_atau_kosong(r["debit"]),
            "Kredit": _rp_atau_kosong(r["kredit"]),
        })
    rows.append({
        "Kode": "",
        "Akun": "TOTAL",
        "Debit": acc.format_rupiah(ns["total_debit"]),
        "Kredit": acc.format_rupiah(ns["total_kredit"]),
    })
    df = pd.DataFrame(rows, columns=["Kode", "Akun", "Debit", "Kredit"])
    st.dataframe(df, hide_index=True, use_container_width=True)


# ---------------------------------------------------------------------------
# Inject CSS
# ---------------------------------------------------------------------------
def inject_css():
    """Suntikkan CSS scoped untuk kartu statistik, badge, dan poles tabel."""
    st.markdown(
        """
        <style>
        /* ---- Kartu statistik ---- */
        .stat-card {
            background: #ffffff;
            border: 1px solid #e6e9ec;
            border-left: 4px solid #1F7A4D;
            border-radius: 10px;
            padding: 16px 18px;
            box-shadow: 0 1px 3px rgba(16, 24, 40, 0.06);
            margin-bottom: 12px;
        }
        .stat-card-label {
            font-size: 0.82rem;
            font-weight: 600;
            color: #667085;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            margin-bottom: 6px;
        }
        .stat-card-icon {
            margin-right: 6px;
        }
        .stat-card-value {
            font-size: 1.6rem;
            font-weight: 700;
            color: #1F7A4D;
            line-height: 1.2;
        }

        /* ---- Badge keseimbangan ---- */
        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 999px;
            font-size: 0.85rem;
            font-weight: 600;
            line-height: 1.4;
        }
        .badge-ok {
            background: #e7f6ee;
            color: #1F7A4D;
            border: 1px solid #b6e2c8;
        }
        .badge-bad {
            background: #fdecea;
            color: #b42318;
            border: 1px solid #f5c4be;
        }

        /* ---- Poles tabel & spacing ---- */
        div[data-testid="stDataFrame"] {
            border: 1px solid #e6e9ec;
            border-radius: 8px;
            overflow: hidden;
        }
        div[data-testid="stDataFrame"] table {
            font-size: 0.9rem;
        }
        .block-container {
            padding-top: 2rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
