"""
make_flowchart.py
=================
Render diagram alur (flowchart) aplikasi "Akuntansi Tani Padi" menjadi PNG
memakai Pillow (tanpa graphviz). Diagram menggambarkan alur runtime nyata:

  Mulai -> streamlit run app.py -> set_page_config + inject_css
        -> buka koneksi DB + buat tabel + seed 20 transaksi + user admin
        -> Sudah login?  (tidak -> halaman Login/Daftar -> ulang)
                          (ya   -> sidebar menu)
        -> Pilih menu:  Laporan (11 tahap)  -> accounting.py menghitung -> tampilkan tabel
                        Input Transaksi      -> validasi debit==kredit -> simpan/ubah/hapus ke DB -> rerun
        -> Selesai

Output: docs/guidebook/assets/flowchart.png
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "guidebook" / "assets"
OUT.mkdir(parents=True, exist_ok=True)

# ---- font -----------------------------------------------------------------
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/home/vascosera/.local/share/fonts/JetBrainsMonoNerdFont-Regular.ttf",
]
FONT_BOLD_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/home/vascosera/.local/share/fonts/JetBrainsMonoNerdFont-Bold.ttf",
]


def _first(paths):
    for p in paths:
        if Path(p).exists():
            return p
    return paths[-1]


FONT = _first(FONT_CANDIDATES)
FONT_BOLD = _first(FONT_BOLD_CANDIDATES)


def font(size, bold=False):
    try:
        return ImageFont.truetype(FONT_BOLD if bold else FONT, size)
    except Exception:
        return ImageFont.load_default()


# ---- palet (selaras tema hijau aplikasi #1F7A4D) --------------------------
GREEN = (31, 122, 77)
GREEN_DARK = (23, 96, 56)
GREEN_SOFT = (231, 240, 234)
INK = (26, 43, 35)
MUTED = (91, 107, 98)
WHITE = (255, 255, 255)
AMBER = (255, 189, 46)
AMBER_SOFT = (255, 247, 224)
BLUE = (45, 110, 170)
BLUE_SOFT = (228, 238, 248)
BORDER = (210, 222, 215)
LINE = (120, 140, 128)

# ---- kanvas ---------------------------------------------------------------
W, H = 1500, 2120
SCALE = 2  # render 2x untuk ketajaman
img = Image.new("RGB", (W * SCALE, H * SCALE), WHITE)
d = ImageDraw.Draw(img)

F_TITLE = font(34 * SCALE, bold=True)
F_BOX = font(23 * SCALE, bold=True)
F_SUB = font(19 * SCALE)
F_LABEL = font(19 * SCALE, bold=True)


def _wrap(text, fnt, max_w):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if d.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _center_text(cx, cy, lines, fnt, fill):
    asc, desc = fnt.getmetrics()
    lh = asc + desc + 4 * SCALE
    total = lh * len(lines)
    y = cy - total / 2
    for ln in lines:
        tw = d.textlength(ln, font=fnt)
        d.text((cx - tw / 2, y), ln, font=fnt, fill=fill)
        y += lh


def box(cx, cy, w, h, title, sub="", fill=WHITE, border=GREEN, tcol=INK, radius=18):
    x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
    d.rounded_rectangle([x0, y0, x1, y1], radius=radius * SCALE, fill=fill,
                        outline=border, width=3 * SCALE)
    lines = _wrap(title, F_BOX, w - 40 * SCALE)
    if sub:
        sublines = _wrap(sub, F_SUB, w - 40 * SCALE)
        asc, desc = F_BOX.getmetrics()
        lh = asc + desc + 4 * SCALE
        asc2, desc2 = F_SUB.getmetrics()
        lh2 = asc2 + desc2 + 3 * SCALE
        total = lh * len(lines) + lh2 * len(sublines) + 6 * SCALE
        y = cy - total / 2
        for ln in lines:
            tw = d.textlength(ln, font=F_BOX)
            d.text((cx - tw / 2, y), ln, font=F_BOX, fill=tcol)
            y += lh
        y += 6 * SCALE
        for ln in sublines:
            tw = d.textlength(ln, font=F_SUB)
            d.text((cx - tw / 2, y), ln, font=F_SUB, fill=MUTED)
            y += lh2
    else:
        _center_text(cx, cy, lines, F_BOX, tcol)
    return (cx, y0, x1, cy, cx, y1, x0, cy)  # anchors: top,right,bottom,left (cx/cy pairs)


def stadium(cx, cy, w, h, title, fill, border, tcol=WHITE):
    x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
    d.rounded_rectangle([x0, y0, x1, y1], radius=h / 2, fill=fill,
                        outline=border, width=3 * SCALE)
    _center_text(cx, cy, _wrap(title, F_BOX, w - 30 * SCALE), F_BOX, tcol)
    return (cx, y0, x1, cy, cx, y1, x0, cy)


def diamond(cx, cy, w, h, title, fill=AMBER_SOFT, border=AMBER, tcol=INK):
    pts = [(cx, cy - h / 2), (cx + w / 2, cy), (cx, cy + h / 2), (cx - w / 2, cy)]
    d.polygon(pts, fill=fill, outline=border)
    # tebalkan garis tepi
    d.line(pts + [pts[0]], fill=border, width=3 * SCALE)
    _center_text(cx, cy, _wrap(title, F_LABEL, w - 60 * SCALE), F_LABEL, tcol)
    return {"top": (cx, cy - h / 2), "right": (cx + w / 2, cy),
            "bottom": (cx, cy + h / 2), "left": (cx - w / 2, cy)}


def arrow(p0, p1, label="", color=LINE, lw=3):
    d.line([p0, p1], fill=color, width=lw * SCALE)
    # kepala panah
    import math
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    L = 14 * SCALE
    a1 = ang + math.radians(150)
    a2 = ang - math.radians(150)
    d.polygon([
        p1,
        (p1[0] + L * math.cos(a1), p1[1] + L * math.sin(a1)),
        (p1[0] + L * math.cos(a2), p1[1] + L * math.sin(a2)),
    ], fill=color)
    if label:
        mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
        tw = d.textlength(label, font=F_LABEL)
        pad = 6 * SCALE
        d.rounded_rectangle(
            [mx - tw / 2 - pad, my - 14 * SCALE, mx + tw / 2 + pad, my + 14 * SCALE],
            radius=8 * SCALE, fill=WHITE, outline=BORDER, width=2 * SCALE,
        )
        d.text((mx - tw / 2, my - 11 * SCALE), label, font=F_LABEL, fill=GREEN_DARK)


def poly_arrow(points, color=LINE, lw=3):
    """Gambar jalur ortogonal (segmen siku) dengan kepala panah di titik akhir."""
    import math
    for a, b in zip(points[:-1], points[1:]):
        d.line([a, b], fill=color, width=lw * SCALE)
    p0, p1 = points[-2], points[-1]
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    L = 14 * SCALE
    a1 = ang + math.radians(150)
    a2 = ang - math.radians(150)
    d.polygon([
        p1,
        (p1[0] + L * math.cos(a1), p1[1] + L * math.sin(a1)),
        (p1[0] + L * math.cos(a2), p1[1] + L * math.sin(a2)),
    ], fill=color)


def S(v):
    return v * SCALE


# ---- judul ----------------------------------------------------------------
title = "Diagram Alur Aplikasi Akuntansi Tani Padi"
tw = d.textlength(title, font=F_TITLE)
d.text(((W * SCALE - tw) / 2, S(28)), title, font=F_TITLE, fill=GREEN_DARK)

cx = W * SCALE / 2
BW = S(560)
BH = S(96)
GAP = S(58)

y = S(150)
# 1. Mulai
a_start = stadium(cx, y + BH / 2, S(300), S(78), "Mulai", GREEN, GREEN_DARK)
y += S(78)

def down(prev_bottom_y, next_h, label=""):
    global y
    top_y = prev_bottom_y + GAP
    return top_y

# 2. streamlit run app.py
y2 = y + GAP
box(cx, y2 + BH / 2, BW, BH, "streamlit run app.py",
    "Pengguna menjalankan aplikasi di terminal", fill=WHITE, border=GREEN)
arrow((cx, y), (cx, y2))
y = y2 + BH

# 3. set_page_config + inject_css
y3 = y + GAP
box(cx, y3 + BH / 2, BW, BH, "set_page_config + inject_css()",
    "Konfigurasi halaman & suntik tema hijau", fill=WHITE, border=GREEN)
arrow((cx, y), (cx, y3))
y = y3 + BH

# 4. DB init
y4 = y + GAP
BH4 = S(116)
box(cx, y4 + BH4 / 2, BW, BH4, "Inisialisasi Database (SQLite)",
    "create_tables · seed 20 transaksi (T01–T20) · user admin", fill=GREEN_SOFT, border=GREEN)
arrow((cx, y), (cx, y4))
y = y4 + BH4

# 5. decision: sudah login?
y5 = y + GAP
DW, DH = S(380), S(150)
dia = diamond(cx, y5 + DH / 2, DW, DH, "Sudah login?")
arrow((cx, y), (cx, y5))
# cabang TIDAK ke kiri -> halaman login
login_cx = cx - S(470)
login_cy = y5 + DH / 2
box(login_cx, login_cy, S(300), S(110), "Halaman Login / Daftar",
    "pages_auth: verifikasi password (PBKDF2)", fill=BLUE_SOFT, border=BLUE)
arrow(dia["left"], (login_cx + S(150), login_cy), label="Tidak")
# Loop balik login->decision: jalur ortogonal (siku) di sisi kiri agar tidak
# menyilang diagonal melewati kotak lain.
poly_arrow([
    (login_cx, login_cy - S(55)),
    (login_cx, y5 - S(46)),
    (cx - S(95), y5 - S(46)),
    (cx - S(95), y5 + S(22)),
], color=LINE)
_lbl = "ulang"
_lx = (login_cx + (cx - S(95))) / 2
_lw = d.textlength(_lbl, font=F_LABEL)
d.rounded_rectangle(
    [_lx - _lw / 2 - S(6), y5 - S(46) - S(14), _lx + _lw / 2 + S(6), y5 - S(46) + S(14)],
    radius=S(8), fill=WHITE, outline=BORDER, width=2 * SCALE,
)
d.text((_lx - _lw / 2, y5 - S(46) - S(11)), _lbl, font=F_LABEL, fill=GREEN_DARK)
y = y5 + DH

# 6. sidebar menu (dari cabang YA)
y6 = y + GAP
box(cx, y6 + BH / 2, BW, BH, "Sidebar Menu (st.radio)",
    "Dashboard · 11 tahap laporan · Input Transaksi", fill=WHITE, border=GREEN)
arrow(dia["bottom"], (cx, y6), label="Ya")
y = y6 + BH

# 7. decision pilih menu
y7 = y + GAP
dia2 = diamond(cx, y7 + DH / 2, S(420), DH, "Pilih menu?")
arrow((cx, y), (cx, y7))
y = y7 + DH

# branch kiri: laporan ; branch kanan: input
rep_cx = cx - S(360)
inp_cx = cx + S(360)
yb = y + GAP
# Laporan
box(rep_cx, yb + BH4 / 2, S(560), BH4, "Tampilkan Laporan (11 tahap)",
    "ui_helpers.get_data → accounting.py menghitung", fill=GREEN_SOFT, border=GREEN)
arrow(dia2["left"], (rep_cx + S(280), yb + BH4 / 2), label="Laporan")
# Input
box(inp_cx, yb + BH4 / 2, S(560), BH4, "Input / Edit / Hapus Transaksi",
    "pages_input: form debit & kredit", fill=AMBER_SOFT, border=AMBER)
arrow(dia2["right"], (inp_cx - S(280), yb + BH4 / 2), label="Input")
y = yb + BH4

# 8. dibawah laporan: render tabel
yr = y + GAP
box(rep_cx, yr + BH / 2, S(560), BH, "Render tabel HTML berstyle",
    "tabel_html() / tabel_neraca_saldo()", fill=WHITE, border=GREEN)
arrow((rep_cx, y), (rep_cx, yr))

# 8b. dibawah input: validasi
box(inp_cx, yr + BH / 2, S(560), BH, "Validasi: debit == kredit?",
    "accounting.validasi_entry()", fill=WHITE, border=AMBER)
arrow((inp_cx, y), (inp_cx, yr))
y = yr + BH

# 9. dibawah input validasi: simpan ke DB
ys = y + GAP
box(inp_cx, ys + BH / 2, S(560), BH, "Simpan ke Database + st.rerun()",
    "insert/update/hapus_jurnal()", fill=GREEN_SOFT, border=GREEN)
arrow((inp_cx, y), (inp_cx, ys), label="Ya")

# 10. selesai (gabungan dua cabang)
yend = ys + BH + GAP
end_cy = yend + S(39)
stadium(cx, end_cy, S(320), S(78), "Selesai", GREEN, GREEN_DARK)
# panah dari render tabel (laporan) ke selesai
arrow((rep_cx, yr + BH), (cx - S(120), yend), color=LINE)
# panah dari simpan DB ke selesai
arrow((inp_cx, ys + BH), (cx + S(120), yend), color=LINE)

# ---- simpan (downscale untuk anti-alias) ----------------------------------
final = img.resize((W, int((end_cy + S(80)) / SCALE)), Image.LANCZOS)
fp = OUT / "flowchart.png"
final.save(fp)
print(f"OK  flowchart.png  ({final.width}x{final.height})  -> {fp}")
