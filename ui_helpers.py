"""
ui_helpers.py
=============
Satu sumber kebenaran alur data laporan + helper render Streamlit.

Modul ini READ-ONLY: tidak pernah menulis ke database. Seluruh perhitungan
akuntansi didelegasikan ke accounting.py; modul ini hanya merangkai data dan
menyajikannya (kartu statistik, badge seimbang, tabel, CSS).

Dipakai oleh seluruh halaman aplikasi (app.py + halaman laporan).
"""
import html
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
# Render: header seksi laporan (.ajp-section)
# ---------------------------------------------------------------------------
def section_header(judul, ikon="", sub=""):
    """Render header seksi laporan berstyle (accent bar / chip ikon + judul).

    - judul : teks judul utama (di-escape).
    - ikon  : emoji opsional; bila kosong dipakai accent bar hijau.
    - sub   : subjudul muted opsional (di-escape); disembunyikan bila kosong.

    Semua nilai teks dilewatkan html.escape() sebagai defense-in-depth meskipun
    pemanggil saat ini hanya mengirim literal.
    """
    judul_safe = html.escape(str(judul))
    if ikon:
        lead = f'<span class="ajp-section-icon">{ikon}</span>'
    else:
        lead = '<span class="ajp-section-bar"></span>'
    sub_html = ""
    if sub:
        sub_safe = html.escape(str(sub))
        sub_html = f'<div class="ajp-section-sub">{sub_safe}</div>'
    st.markdown(
        f"""
        <div class="ajp-section">
            {lead}
            <div class="ajp-section-text">
                <div class="ajp-section-title">{judul_safe}</div>
                {sub_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Render: tabel HTML berstyle (.ajp-table) — pengganti st.dataframe
# ---------------------------------------------------------------------------
def _bersihkan_sel(v):
    """Coerce None/NaN/'None'/'nan' menjadi string kosong; selain itu str(v)."""
    if v is None:
        return ""
    try:
        if isinstance(v, float) and pd.isna(v):
            return ""
    except (TypeError, ValueError):
        pass
    s = str(v)
    if s in ("None", "nan", "NaN", "NaT", "<NA>"):
        return ""
    return s


def tabel_html(rows_or_df, right_cols=None, total_row_label=None, headers=None):
    """Bangun string HTML tabel berstyle dari DataFrame ATAU list-of-dict.

    Parameter:
      rows_or_df      : pandas.DataFrame atau list[dict] berisi baris tabel.
      right_cols      : iterable nama kolom yang dirata-kanan (kolom angka)
                        → mendapat class .ajp-num (tabular-nums, nowrap).
      total_row_label : bila diset, baris yang sel KOLOM PERTAMA-nya sama dengan
                        nilai ini ditandai <tr class="ajp-total"> (tebal).
      headers         : override urutan/nama kolom (opsional).

    KEAMANAN: setiap sel header DAN body dilewatkan html.escape() — kolom
    "Keterangan" memuat teks bebas input manual pengguna (permukaan XSS).
    Nilai uang yang sudah diformat acc.format_rupiah dipakai apa adanya
    (tidak di-parse / di-format ulang).
    """
    right_cols = set(right_cols or [])

    if isinstance(rows_or_df, pd.DataFrame):
        cols = list(headers) if headers is not None else list(rows_or_df.columns)
        records = rows_or_df.to_dict("records")
    else:
        records = list(rows_or_df or [])
        if headers is not None:
            cols = list(headers)
        elif records:
            cols = list(records[0].keys())
        else:
            cols = []

    # thead — header bertanda .ajp-num bila kolom angka (rata kanan konsisten)
    head_cells = []
    for c in cols:
        cls = ' class="ajp-num"' if c in right_cols else ""
        head_cells.append(f"<th{cls}>{html.escape(_bersihkan_sel(c))}</th>")
    thead = "<thead><tr>" + "".join(head_cells) + "</tr></thead>"

    # tbody
    body_rows = []
    first_col = cols[0] if cols else None
    for rec in records:
        is_total = False
        if total_row_label is not None and first_col is not None:
            label_val = _bersihkan_sel(rec.get(first_col, "")) if isinstance(rec, dict) else ""
            if label_val == str(total_row_label):
                is_total = True
        tr_cls = ' class="ajp-total"' if is_total else ""
        cells = []
        for c in cols:
            val = _bersihkan_sel(rec.get(c, "")) if isinstance(rec, dict) else ""
            cls = ' class="ajp-num"' if c in right_cols else ""
            cells.append(f"<td{cls}>{html.escape(val)}</td>")
        body_rows.append(f"<tr{tr_cls}>" + "".join(cells) + "</tr>")
    tbody = "<tbody>" + "".join(body_rows) + "</tbody>"

    return (
        '<div class="ajp-table-wrap"><table class="ajp-table">'
        + thead
        + tbody
        + "</table></div>"
    )


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
    st.markdown(
        tabel_html(df, right_cols=["Debit", "Kredit"], total_row_label=None),
        unsafe_allow_html=True,
    )


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
    st.markdown(
        tabel_html(
            df, right_cols=["Debit", "Kredit"], total_row_label="TOTAL"
        ),
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Inject CSS
# ---------------------------------------------------------------------------
def inject_css():
    """Suntikkan satu stylesheet global: design system light/hijau (#1F7A4D).

    Mengandung sistem desain bersama (token warna/elevasi) + komponen scoped
    (kartu statistik, badge, tabel) + poles komponen native Streamlit lewat
    selektor STABIL (data-testid / data-baseweb saja). Disuntik SEKALI di app.py.
    String CSS bersifat literal statis (tidak ada interpolasi nilai dinamis).
    """
    st.markdown(
        """
        <style>
        /* =====================================================================
           DESIGN TOKENS — light + aksen hijau tani (#1F7A4D)
           ===================================================================== */
        :root {
            --ajp-green: #1F7A4D;
            --ajp-green-strong: #176038;
            --ajp-green-soft: #E7F0EA;
            --ajp-ink: #1A2B23;
            --ajp-muted: #5B6B62;
            --ajp-border: #DCE7E0;
            --ajp-surface: #FFFFFF;
            --ajp-wash: #FBFDFC;
            --ajp-radius: 14px;
            --ajp-shadow-sm: 0 1px 2px rgba(16,24,40,.04), 0 1px 3px rgba(16,24,40,.06);
            --ajp-shadow-lg: 0 6px 16px rgba(16,24,40,.10);
        }

        /* Faint page wash sehingga kartu & sidebar terasa terangkat ----------- */
        [data-testid="stAppViewContainer"] {
            background: var(--ajp-wash);
        }

        /* Lebar konten nyaman + padding atas yang lega ------------------------ */
        .block-container,
        [data-testid="stMainBlockContainer"] {
            max-width: 1160px;
            padding-top: 2.4rem;
            padding-bottom: 3rem;
        }

        /* =====================================================================
           HEADINGS — bobot & warna konsisten
           ===================================================================== */
        .stApp h1, .stApp h2, .stApp h3 {
            color: var(--ajp-ink);
            letter-spacing: -0.01em;
        }
        .stApp h1 { font-weight: 700; font-size: 2.1rem; }
        .stApp h2 { font-weight: 650; font-size: 1.5rem; }
        .stApp h3 { font-weight: 600; font-size: 1.2rem; }

        /* =====================================================================
           METRIC NATIVE — kartu terangkat + hover + aksen hijau
           ===================================================================== */
        [data-testid="stMetric"] {
            background: var(--ajp-surface);
            border: 1px solid var(--ajp-border);
            border-top: 3px solid var(--ajp-green);
            border-radius: var(--ajp-radius);
            padding: 1rem 1.25rem;
            box-shadow: var(--ajp-shadow-sm);
            transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
        }
        [data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            box-shadow: var(--ajp-shadow-lg);
            border-color: var(--ajp-green);
        }
        [data-testid="stMetricLabel"] {
            text-transform: uppercase;
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.5px;
            color: var(--ajp-muted) !important;
        }
        [data-testid="stMetricLabel"] p {
            color: var(--ajp-muted) !important;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.9rem;
            font-weight: 700;
            color: var(--ajp-ink) !important;
        }

        /* =====================================================================
           SIDEBAR — gradien tipis + garis pemisah
           ===================================================================== */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #EDF3EF 0%, #DCE9E1 100%);
            border-right: 1px solid #D3DED7;
        }
        [data-testid="stSidebarUserContent"] {
            padding-top: 0.75rem;
        }

        /* =====================================================================
           KARTU STATISTIK (.stat-card) — dipakai ui_helpers.kartu_statistik
           ===================================================================== */
        .stat-card {
            background: var(--ajp-surface);
            border: 1px solid var(--ajp-border);
            border-top: 3px solid var(--ajp-green);
            border-radius: var(--ajp-radius);
            padding: 1rem 1.25rem;
            box-shadow: var(--ajp-shadow-sm);
            margin-bottom: 12px;
            transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
        }
        .stat-card:hover {
            transform: translateY(-2px);
            box-shadow: var(--ajp-shadow-lg);
            border-color: var(--ajp-green);
        }
        .stat-card-label {
            font-size: 0.72rem;
            font-weight: 600;
            color: var(--ajp-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }
        .stat-card-icon {
            margin-right: 6px;
        }
        .stat-card-value {
            font-size: 1.9rem;
            font-weight: 700;
            color: var(--ajp-ink);
            line-height: 1.2;
        }

        /* =====================================================================
           BADGE KESEIMBANGAN
           ===================================================================== */
        .badge {
            display: inline-block;
            padding: 5px 14px;
            border-radius: 999px;
            font-size: 0.85rem;
            font-weight: 600;
            line-height: 1.4;
        }
        .badge-ok {
            background: var(--ajp-green-soft);
            color: var(--ajp-green);
            border: 1px solid #B6E2C8;
        }
        .badge-bad {
            background: #FDECEA;
            color: #B42318;
            border: 1px solid #F5C4BE;
        }

        /* =====================================================================
           DATAFRAME — bingkai rapi (sel di-render canvas → tak bisa di-CSS)
           ===================================================================== */
        [data-testid="stDataFrame"] {
            border: 1px solid var(--ajp-border);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: var(--ajp-shadow-sm);
        }
        [data-testid="stDataFrame"] table {
            font-size: 0.9rem;
        }

        /* =====================================================================
           BUTTONS — rapi, transisi halus, primary hijau
           ===================================================================== */
        .stButton > button {
            padding: 0.5rem 1.1rem;
            font-weight: 600;
            transition: transform .15s ease, box-shadow .15s ease,
                        background-color .15s ease, border-color .15s ease;
        }
        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: var(--ajp-shadow-sm);
        }
        [data-testid="stBaseButton-primary"] {
            background: var(--ajp-green);
            border-color: var(--ajp-green);
        }
        [data-testid="stBaseButton-primary"]:hover {
            background: var(--ajp-green-strong);
            border-color: var(--ajp-green-strong);
        }

        /* =====================================================================
           TABS — spasi lega, tab aktif aksen hijau
           ===================================================================== */
        .stTabs [data-baseweb="tab-list"] {
            gap: 6px;
            border-bottom: 1px solid var(--ajp-border);
        }
        .stTabs [data-baseweb="tab"] {
            padding: 0.55rem 1.1rem;
            font-weight: 600;
            color: var(--ajp-muted);
        }
        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            color: var(--ajp-green);
        }
        .stTabs [data-baseweb="tab-highlight"] {
            background-color: var(--ajp-green);
        }

        /* =====================================================================
           ALERTS — sudut membulat, lembut
           ===================================================================== */
        [data-testid="stAlert"] {
            border-radius: var(--ajp-radius);
            border: 1px solid var(--ajp-border);
            box-shadow: var(--ajp-shadow-sm);
        }

        /* =====================================================================
           EXPANDER — tampil seperti kartu berbingkai
           ===================================================================== */
        [data-testid="stExpander"] {
            border: 1px solid var(--ajp-border);
            border-radius: var(--ajp-radius);
            box-shadow: var(--ajp-shadow-sm);
            overflow: hidden;
            background: var(--ajp-surface);
        }

        /* =====================================================================
           AUTH HERO — kartu login berbranding (dipakai pages_auth)
           ===================================================================== */
        .ajp-auth-hero {
            text-align: center;
            margin: 0.5rem 0 1.25rem;
        }
        .ajp-auth-logo {
            font-size: 2.6rem;
            line-height: 1;
        }
        .ajp-auth-title {
            margin: 0.45rem 0 0.2rem;
            font-size: 1.7rem;
            font-weight: 700;
            color: var(--ajp-green);
            letter-spacing: -0.01em;
        }
        .ajp-auth-tagline {
            margin: 0;
            font-size: 0.98rem;
            color: var(--ajp-muted);
        }
        .ajp-auth-divider {
            height: 3px;
            width: 64px;
            margin: 0.9rem auto 0;
            border-radius: 999px;
            background: linear-gradient(90deg, #1F7A4D 0%, #4FB07C 100%);
        }

        /* =====================================================================
           SECTION HEADER (.ajp-section) — judul laporan berstyle (Wave 2)
           ===================================================================== */
        .ajp-section {
            display: flex;
            align-items: center;
            gap: 12px;
            margin: 1.6rem 0 0.9rem;
        }
        .ajp-section-bar {
            flex: 0 0 auto;
            width: 4px;
            align-self: stretch;
            min-height: 2.1rem;
            border-radius: 999px;
            background: linear-gradient(180deg, #2E9966 0%, var(--ajp-green) 100%);
        }
        .ajp-section-icon {
            flex: 0 0 auto;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 2.2rem;
            height: 2.2rem;
            border-radius: 10px;
            font-size: 1.15rem;
            background: var(--ajp-green-soft);
            border: 1px solid #B6E2C8;
            box-shadow: var(--ajp-shadow-sm);
        }
        .ajp-section-text {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }
        .ajp-section-title {
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--ajp-ink);
            line-height: 1.2;
            letter-spacing: -0.01em;
        }
        .ajp-section-sub {
            font-size: 0.9rem;
            color: var(--ajp-muted);
            line-height: 1.45;
        }

        /* =====================================================================
           TABEL HTML BERSTYLE (.ajp-table) — pengganti st.dataframe (Wave 2)
           ===================================================================== */
        .ajp-table-wrap {
            border: 1px solid var(--ajp-border);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: var(--ajp-shadow-sm);
            margin-bottom: 1rem;
            background: var(--ajp-surface);
        }
        .ajp-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }
        .ajp-table thead th {
            background: linear-gradient(135deg, #1F7A4D 0%, #2E9966 100%);
            color: #FFFFFF;
            font-weight: 600;
            text-align: left;
            padding: 10px 14px;
            letter-spacing: 0.02em;
            white-space: nowrap;
        }
        .ajp-table thead th.ajp-num {
            text-align: right;
        }
        .ajp-table tbody td {
            padding: 9px 14px;
            border-top: 1px solid #EEF4F0;
            color: var(--ajp-ink);
            vertical-align: top;
        }
        .ajp-table tbody tr:nth-child(even) {
            background: #F7FBF8;
        }
        .ajp-table tbody tr:hover {
            background: #EEF4F0;
        }
        .ajp-table .ajp-num {
            text-align: right;
            font-variant-numeric: tabular-nums;
            white-space: nowrap;
        }
        .ajp-table tr.ajp-total td {
            font-weight: 700;
            border-top: 2px solid var(--ajp-green);
            background: var(--ajp-green-soft);
        }

        /* =====================================================================
           SIDEBAR NAV RAIL (.ajp-sidebar*) — brand + pill menu (Wave 3)
           (background gradient diatur oleh aturan Wave-1; ini MENAMBAH saja)
           ===================================================================== */
        [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
            padding-top: 1rem;
        }

        /* Blok brand di puncak sidebar ---------------------------------------- */
        .ajp-sidebar-brand {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 4px 2px 2px;
            margin-bottom: 10px;
        }
        .ajp-sidebar-brand-icon {
            flex: 0 0 auto;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 2.4rem;
            height: 2.4rem;
            border-radius: 12px;
            font-size: 1.35rem;
            background: var(--ajp-surface);
            border: 1px solid #B6E2C8;
            box-shadow: var(--ajp-shadow-sm);
        }
        .ajp-sidebar-brand-text {
            display: flex;
            flex-direction: column;
            line-height: 1.2;
        }
        .ajp-sidebar-brand-title {
            font-size: 1.02rem;
            font-weight: 700;
            color: var(--ajp-ink);
            letter-spacing: -0.01em;
        }
        .ajp-sidebar-brand-sub {
            font-size: 0.74rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: var(--ajp-muted);
        }

        /* Pill identitas user ------------------------------------------------- */
        .ajp-sidebar-user {
            display: flex;
            align-items: center;
            gap: 7px;
            padding: 7px 12px;
            margin-bottom: 12px;
            border-radius: 999px;
            background: var(--ajp-green-soft);
            border: 1px solid #B6E2C8;
            color: var(--ajp-muted);
            font-size: 0.84rem;
            line-height: 1.3;
        }
        .ajp-sidebar-user-glyph {
            flex: 0 0 auto;
            font-size: 0.95rem;
        }
        .ajp-sidebar-user strong {
            color: var(--ajp-green-strong);
            font-weight: 700;
        }

        /* Divider sidebar sedikit lebih lembut -------------------------------- */
        [data-testid="stSidebar"] hr {
            border-color: #D3DED7;
            margin: 0.6rem 0 0.9rem;
        }

        /* Radio nav → menu pill vertikal (scoped KE SIDEBAR saja) ------------- */
        [data-testid="stSidebar"] [role="radiogroup"] {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label {
            width: 100%;
            padding: 8px 12px;
            border-radius: 10px;
            cursor: pointer;
            color: var(--ajp-ink);
            font-weight: 500;
            font-size: 0.92rem;
            line-height: 1.35;
            border-left: 3px solid transparent;
            transition: background .15s ease, color .15s ease, border-color .15s ease;
        }
        /* Sembunyikan lingkaran radio (dua kemungkinan struktur BaseWeb) ------- */
        [data-testid="stSidebar"] [role="radiogroup"] label > div:first-child {
            display: none;
        }
        [data-testid="stSidebar"] [data-baseweb="radio"] > div:first-child {
            display: none;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label:hover {
            background: rgba(31, 122, 77, .08);
        }
        /* Item aktif: isian hijau-soft + tebal + accent bar kiri hijau -------- */
        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
            background: var(--ajp-green-soft);
            color: var(--ajp-green-strong);
            font-weight: 700;
            border-left-color: var(--ajp-green);
        }

        /* Tombol Keluar di sidebar → gaya ghost; hover memberi sinyal merah --- */
        [data-testid="stSidebar"] .stButton > button {
            background: transparent;
            border: 1px solid var(--ajp-border);
            color: var(--ajp-ink);
            border-radius: 999px;
            font-weight: 600;
        }
        [data-testid="stSidebar"] .stButton > button:hover {
            background: #FDECEA;
            border-color: #F5C4BE;
            color: #B42318;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
