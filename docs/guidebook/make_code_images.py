"""
make_code_images.py
===================
Render potongan kode sumber menjadi gambar PNG bergaya "carbon"
(jendela gelap + traffic-light + syntax highlight) untuk Buku Panduan
Aplikasi Akuntansi Tani Padi.

Output: docs/guidebook/assets/code/*.png

Catatan:
  - Rentang baris pada JOBS sudah DIVERIFIKASI terhadap berkas sumber nyata
    (file dapat bergeser dari draf awal). Setiap job memuat satu blok kode
    utuh (umumnya satu fungsi penuh) agar tidak terpotong di tengah pernyataan.
  - Mendukung rentang ganda (mis. fungsi 'hapus' & 'reset' yang berjauhan)
    dengan menyisipkan pemisah "# ...".
  - Font kode mencoba keluarga JetBrains Mono Nerd Font, lalu jatuh balik ke
    DejaVu Sans Mono (yang pasti dikenali pygments di Linux).
"""
from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pygments import highlight
from pygments.formatters import ImageFormatter
from pygments.lexers import BashLexer, BatchLexer, PythonLexer

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "guidebook" / "assets" / "code"
OUT.mkdir(parents=True, exist_ok=True)

# --- font untuk judul jendela (dimuat langsung lewat path file oleh PIL) -----
MONO_CANDIDATES = [
    "/home/vascosera/.local/share/fonts/JetBrainsMonoNerdFont-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
]
MONO_BOLD_CANDIDATES = [
    "/home/vascosera/.local/share/fonts/JetBrainsMonoNerdFont-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
]


def _first_existing(paths):
    for p in paths:
        if Path(p).exists():
            return p
    return None


MONO = _first_existing(MONO_CANDIDATES) or MONO_CANDIDATES[-1]
MONO_BOLD = _first_existing(MONO_BOLD_CANDIDATES) or MONO

# Keluarga font yang dicoba untuk ImageFormatter pygments (sesuai fontconfig).
CODE_FONT_FAMILIES = ["JetBrainsMono Nerd Font", "DejaVu Sans Mono"]

CHROME = (33, 34, 44)      # warna bar judul jendela (mirip Dracula chrome)
PAD = 28
TITLE_H = 46
RADIUS = 14


def _highlight_to_png(code: str, lexer, fontsize: int) -> bytes:
    """Coba beberapa keluarga font sampai pygments berhasil menemukannya."""
    last_err: Exception | None = None
    for family in CODE_FONT_FAMILIES:
        try:
            formatter = ImageFormatter(
                font_name=family,
                font_size=fontsize,
                line_numbers=True,
                line_number_bg="#21222c",
                line_number_fg="#6272a4",
                line_number_chars=3,
                style="dracula",
                image_pad=PAD,
                line_pad=6,
            )
            return highlight(code.rstrip("\n"), lexer, formatter)
        except Exception as e:  # FontNotFound dsb.
            last_err = e
            continue
    raise RuntimeError(f"Gagal merender kode (font?): {last_err}")


def render_code(code: str, title: str, lexer=None, fontsize: int = 26) -> Image.Image:
    """Bungkus kode ber-highlight dalam 'jendela' gelap dengan judul + traffic-light."""
    lexer = lexer or PythonLexer()
    png_bytes = _highlight_to_png(code, lexer, fontsize)
    code_img = Image.open(io.BytesIO(png_bytes)).convert("RGB")

    w = code_img.width
    h = code_img.height + TITLE_H
    canvas = Image.new("RGB", (w, h), CHROME)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, 0, w, TITLE_H], fill=CHROME)

    # traffic-light (merah / kuning / hijau)
    cy = TITLE_H // 2
    for i, col in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        cx = 24 + i * 26
        draw.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=col)

    # judul jendela (di tengah)
    try:
        tf = ImageFont.truetype(MONO_BOLD, 22)
    except Exception:
        tf = ImageFont.load_default()
    tb = draw.textbbox((0, 0), title, font=tf)
    tw = tb[2] - tb[0]
    draw.text(
        ((w - tw) / 2, (TITLE_H - (tb[3] - tb[1])) / 2 - tb[1]),
        title, fill=(189, 195, 215), font=tf,
    )

    canvas.paste(code_img, (0, TITLE_H))

    # sudut membulat di atas latar putih (agar rapi saat ditempel ke DOCX)
    out = Image.new("RGB", (w, h), (255, 255, 255))
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([0, 0, w - 1, h - 1], radius=RADIUS, fill=255)
    out.paste(canvas, (0, 0), mask)
    return out


def _read_lines(path: str) -> list[str]:
    return (ROOT / path).read_text(encoding="utf-8").splitlines()


def snippet(path: str, ranges: list[tuple[int, int]]) -> str:
    """Ambil satu/lebih rentang baris (1-indexed, inklusif). Sisipkan '# ...'
    di antara rentang yang berjauhan."""
    lines = _read_lines(path)
    parts: list[str] = []
    for i, (start, end) in enumerate(ranges):
        if i > 0:
            parts.append("")
            parts.append("# ...")
            parts.append("")
        parts.extend(lines[start - 1:end])
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# JOBS dari berkas sumber — (path, judul, [rentang], lexer)
# Rentang sudah diverifikasi terhadap berkas nyata.
# ---------------------------------------------------------------------------
JOBS_FILE = [
    ("database.py", "database.py - skema tabel", [(34, 70)], PythonLexer()),
    ("database.py", "database.py - seed_database()", [(76, 94)], PythonLexer()),
    ("database.py", "database.py - get_jurnal_umum & _baca_jurnal", [(100, 135)], PythonLexer()),
    ("database.py", "database.py - next_kode & insert_jurnal()", [(145, 185)], PythonLexer()),
    ("database.py", "database.py - update_jurnal()", [(195, 224)], PythonLexer()),
    ("database.py", "database.py - hapus_jurnal & reset_jurnal", [(188, 192), (227, 233)], PythonLexer()),
    ("accounting.py", "accounting.py - format_rupiah & validasi_entry", [(32, 60)], PythonLexer()),
    ("accounting.py", "accounting.py - laba_rugi()", [(182, 205)], PythonLexer()),
    ("seed_data.py", "seed_data.py - bagan akun", [(18, 43)], PythonLexer()),
    ("auth.py", "auth.py - hash & verifikasi password", [(21, 38)], PythonLexer()),
    ("auth.py", "auth.py - register()", [(44, 59)], PythonLexer()),
    ("app.py", "app.py - konfigurasi & koneksi", [(36, 60)], PythonLexer()),
    ("app.py", "app.py - menu & dispatch", [(66, 80), (117, 149)], PythonLexer()),
    ("app.py", "app.py - alur utama main()", [(154, 172)], PythonLexer()),
    ("pages_auth.py", "pages_auth.py - form login", [(43, 64)], PythonLexer()),
    ("pages_input.py", "pages_input.py - form edit transaksi", [(49, 92)], PythonLexer()),
    ("pages_input.py", "pages_input.py - simpan transaksi", [(135, 190)], PythonLexer()),
    ("pages_input.py", "pages_input.py - tombol edit & hapus", [(219, 240)], PythonLexer()),
    ("ui_helpers.py", "ui_helpers.py - get_data()", [(27, 46)], PythonLexer()),
    ("ui_helpers.py", "ui_helpers.py - tabel_html()", [(115, 175)], PythonLexer()),
]

# ---------------------------------------------------------------------------
# JOBS inline (perintah shell untuk bab Persiapan Lingkungan) — (kode, judul, lexer)
# ---------------------------------------------------------------------------
JOBS_INLINE = [
    (
        "REM 1) Verifikasi Python sudah terpasang dan masuk ke PATH\n"
        "REM    (jalankan di Command Prompt / cmd)\n"
        "py --version\n"
        "python --version",
        "Command Prompt - memeriksa Python (Windows)",
        BatchLexer(),
    ),
    (
        "REM 2) Membuat virtual environment memakai Python launcher (py)\n"
        "py -m venv venv\n\n"
        "REM 3a) Mengaktifkan di Command Prompt (cmd)\n"
        "venv\\Scripts\\activate.bat\n\n"
        "REM 3b) Mengaktifkan di PowerShell\n"
        ".\\venv\\Scripts\\Activate.ps1\n\n"
        "REM     Bila PowerShell memblokir skrip, jalankan dulu perintah ini:\n"
        "Set-ExecutionPolicy -Scope CurrentUser RemoteSigned\n\n"
        "REM     Berhasil bila prompt kini diawali tulisan (venv)",
        "Command Prompt - membuat dan mengaktifkan virtual environment (Windows)",
        BatchLexer(),
    ),
    (
        "REM 4) Memasang pustaka yang dibutuhkan\n"
        "pip install streamlit pandas\n\n"
        "REM     (opsional) memasang dari berkas daftar pustaka\n"
        "pip install -r requirements.txt",
        "Command Prompt - memasang pustaka (Windows)",
        BatchLexer(),
    ),
    (
        "REM 5) Menjalankan aplikasi\n"
        "streamlit run app.py\n\n"
        "REM     Aplikasi akan terbuka otomatis di peramban pada:\n"
        "REM       Local URL:  http://localhost:8501\n"
        "REM     Login awal:  admin / admin123",
        "Command Prompt - menjalankan aplikasi (Windows)",
        BatchLexer(),
    ),
    (
        "# Persiapan setara untuk Linux / macOS (terminal bash)\n"
        "python3 --version\n\n"
        "# Buat lalu aktifkan virtual environment\n"
        "python3 -m venv venv\n"
        "source venv/bin/activate\n\n"
        "# Pasang pustaka lalu jalankan aplikasi\n"
        "pip install streamlit pandas\n"
        "streamlit run app.py",
        "Terminal - persiapan Linux atau macOS",
        BashLexer(),
    ),
]


def _safe_name(title: str) -> str:
    return (
        title.replace(" ", "_").replace("/", "_")
        .replace("(", "").replace(")", "").replace("&", "dan")
        .replace("-", "").replace("__", "_")
    )


def main():
    made = []

    for path, title, ranges, lexer in JOBS_FILE:
        try:
            code = snippet(path, ranges)
        except FileNotFoundError:
            print(f"SKIP (tidak ada): {path}")
            continue
        if not code.strip():
            print(f"SKIP (kosong): {path} {ranges}")
            continue
        img = render_code(code, title, lexer)
        fp = OUT / f"{_safe_name(title)}.png"
        img.save(fp)
        made.append(fp.name)
        print(f"OK  {fp.name}  ({img.width}x{img.height})")

    for code, title, lexer in JOBS_INLINE:
        img = render_code(code, title, lexer)
        fp = OUT / f"{_safe_name(title)}.png"
        img.save(fp)
        made.append(fp.name)
        print(f"OK  {fp.name}  ({img.width}x{img.height})")

    print(f"\nTotal {len(made)} gambar kode di {OUT}")


if __name__ == "__main__":
    main()
