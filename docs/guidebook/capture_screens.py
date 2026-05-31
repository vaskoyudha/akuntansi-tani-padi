"""
capture_screens.py
===================
Mengambil screenshot LIVE dari aplikasi Streamlit "Akuntansi Tani Padi"
yang sedang berjalan di http://localhost:8501 untuk Buku Panduan.

Memakai Playwright (Chromium). Login admin/admin123, menyusuri seluruh menu
sidebar (Dashboard + 11 tahap laporan + Input Transaksi), lalu menambah satu
transaksi contoh agar tombol "Edit" muncul dan dapat di-screenshot.

Output: docs/guidebook/assets/screenshots/*.png

Catatan:
  - Aplikasi TIDAK direstart oleh skrip ini; hanya dikendalikan lewat peramban.
  - Skrip menambah 1 transaksi via form (penggunaan normal aplikasi) untuk
    mendemokan fitur Edit, lalu transaksi itu dibiarkan (tidak menghapus DB).
  - Idempoten secukupnya: jika sudah ada transaksi non-seed, langsung pakai itu.
"""
from __future__ import annotations

import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "guidebook" / "assets" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

URL = "http://localhost:8501/"
USER = "admin"
PWD = "admin123"

# Pakai chromium penuh yang sudah terpasang (hindari unduh chrome-headless-shell).
import glob

def _find_chrome() -> str | None:
    pats = [
        str(Path.home() / ".cache/ms-playwright/chromium-*/chrome-linux64/chrome"),
        str(Path.home() / ".cache/ms-playwright/chromium-*/chrome-linux/chrome"),
    ]
    for pat in pats:
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    return None

CHROME_PATH = _find_chrome()

# (label sidebar persis, nama file, teks yang ditunggu muncul)
PAGES = [
    ("🏠 Dashboard", "03-dashboard.png", None),
    ("1. Jurnal Umum", "04-jurnal-umum.png", "Jurnal Umum"),
    ("2. Buku Besar", "05-buku-besar.png", "Buku Besar"),
    ("3. Neraca Saldo", "06-neraca-saldo.png", "Neraca Saldo"),
    ("4. Jurnal Penyesuaian", "07-jurnal-penyesuaian.png", "Penyesuaian"),
    ("5. NS Setelah Penyesuaian", "08-ns-penyesuaian.png", "Penyesuaian"),
    ("6. Laporan Laba Rugi", "09-laba-rugi.png", "Laba Rugi"),
    ("7. Perubahan Ekuitas", "10-ekuitas.png", "Ekuitas"),
    ("8. Posisi Keuangan", "11-posisi-keuangan.png", "Posisi Keuangan"),
    ("9. Arus Kas", "12-arus-kas.png", "Arus Kas"),
    ("10. Jurnal Penutup", "13-jurnal-penutup.png", "Penutup"),
    ("11. NS Setelah Penutupan", "14-ns-penutupan.png", "Penutupan"),
]


def wait_render(page, sleep=1.8):
    """Tunggu Streamlit selesai rerender (indikator status hilang) + jeda."""
    try:
        page.wait_for_selector(
            '[data-testid="stStatusWidget"]', state="detached", timeout=4000
        )
    except Exception:
        pass
    page.wait_for_timeout(int(sleep * 1000))


def nav(page, label):
    """Klik item radio sidebar berdasarkan teks label."""
    sidebar = page.locator('[data-testid="stSidebar"]')
    sidebar.get_by_text(label, exact=True).click()
    wait_render(page)


def shot(page, name):
    fp = OUT / name
    page.screenshot(path=str(fp), full_page=True)
    print(f"OK  {name}")
    return fp


def add_sample_transaction(page) -> bool:
    """Isi form 'Simpan Transaksi' (Kas debit / Pendapatan kredit Rp500.000).
    Return True bila berhasil submit."""
    try:
        # Keterangan
        page.get_by_label("Keterangan").first.fill(
            "Penjualan gabah tunai tambahan (contoh panduan)"
        )
        # Nominal debit & kredit (number_input → input spinbutton)
        page.get_by_label("Nominal Debit").first.fill("500000")
        page.get_by_label("Nominal Kredit").first.fill("500000")

        # Akun Kredit → pilih Pendapatan Penjualan Gabah (selectbox ke-2)
        selects = page.locator('div[data-baseweb="select"]')
        if selects.count() >= 2:
            try:
                selects.nth(1).click()
                page.wait_for_timeout(400)
                page.get_by_text(
                    "411 - Pendapatan Penjualan Gabah", exact=True
                ).first.click()
                page.wait_for_timeout(300)
            except Exception as e:
                print("  (info) tidak bisa ganti akun kredit, pakai default:", e)

        page.get_by_role("button", name="Simpan Transaksi").click()
        wait_render(page, sleep=2.2)
        return True
    except Exception as e:
        print("  (info) gagal menambah transaksi contoh:", e)
        return False


def open_edit_form(page) -> bool:
    """Klik tombol '✏️ Edit' pertama yang tersedia (transaksi non-seed),
    lalu tunggu form '✏️ Edit Transaksi' benar-benar muncul."""
    try:
        edit_btns = page.get_by_role("button", name="✏️ Edit")
        if edit_btns.count() == 0:
            return False
        edit_btns.first.click()
        wait_render(page, sleep=2.0)
        # tunggu heading form edit muncul (mis. "✏️ Edit Transaksi `T21`")
        try:
            page.get_by_text("Edit Transaksi").first.wait_for(timeout=8000)
        except Exception:
            pass
        # tunggu tombol simpan perubahan tampil sebagai bukti form terbuka
        try:
            page.get_by_role(
                "button", name="💾 Simpan Perubahan"
            ).first.wait_for(timeout=8000)
        except Exception:
            return False
        # gulir ke atas agar form (yang ada di puncak halaman) terlihat penuh
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(600)
        return True
    except Exception as e:
        print("  (info) gagal membuka form edit:", e)
        return False


def main():
    missing = []
    with sync_playwright() as p:
        launch_kwargs = {"headless": True}
        if CHROME_PATH:
            launch_kwargs["executable_path"] = CHROME_PATH
            print("Memakai Chromium:", CHROME_PATH)
        browser = p.chromium.launch(**launch_kwargs)
        ctx = browser.new_context(
            viewport={"width": 1600, "height": 1200},
            device_scale_factor=2,
        )
        page = ctx.new_page()
        page.set_default_timeout(20000)

        # ----------------------------------------------------------- login page
        page.goto(URL, wait_until="domcontentloaded")
        wait_render(page, sleep=2.5)
        shot(page, "01-login.png")

        # ----------------------------------------------------------- register tab
        try:
            page.get_by_role("tab", name="Daftar").click()
            wait_render(page, sleep=1.2)
            shot(page, "02-register.png")
            # kembali ke tab Masuk
            page.get_by_role("tab", name="Masuk").click()
            wait_render(page, sleep=1.0)
        except Exception as e:
            print("  (info) tab Daftar tidak ditemukan:", e)
            missing.append("02-register.png")

        # ----------------------------------------------------------- do login
        panel = page.locator('[data-baseweb="tab-panel"]').first
        panel.get_by_role("textbox", name="Username").fill(USER)
        panel.get_by_role("textbox", name="Password").fill(PWD)
        panel.get_by_role("button", name="Masuk").click()
        wait_render(page, sleep=2.8)

        # ----------------------------------------------------------- semua halaman
        for label, name, expect in PAGES:
            try:
                nav(page, label)
                if expect:
                    try:
                        page.get_by_text(expect).first.wait_for(timeout=6000)
                    except Exception:
                        pass
                    wait_render(page, sleep=1.0)
                shot(page, name)
            except Exception as e:
                print(f"  (GAGAL) {name}: {e}")
                missing.append(name)

        # ----------------------------------------------------------- input transaksi
        try:
            nav(page, "✏️ Input Transaksi")
            wait_render(page, sleep=1.5)
            shot(page, "15-input-transaksi.png")
        except Exception as e:
            print("  (GAGAL) 15-input-transaksi.png:", e)
            missing.append("15-input-transaksi.png")

        # ----------------------------------------------------------- edit transaksi
        # Pastikan ada transaksi non-seed (ada tombol Edit). Jika belum, tambah.
        has_edit = open_edit_form(page)
        if not has_edit:
            print("  (info) belum ada transaksi non-seed → menambah contoh...")
            add_sample_transaction(page)
            # halaman rerun; pastikan masih di Input Transaksi
            wait_render(page, sleep=1.5)
            has_edit = open_edit_form(page)

        if has_edit:
            # Form edit berada di TENGAH halaman (di bawah form input). Gulir
            # heading-nya ke puncak viewport lalu ambil screenshot viewport
            # (bukan full_page) agar form tampil utuh & terpotong rapi.
            captured = False
            try:
                heading = page.get_by_text("Edit Transaksi").first
                h = heading.element_handle()
                if h is not None:
                    page.evaluate(
                        "(el) => el.scrollIntoView({block: 'start'})", h
                    )
                    page.wait_for_timeout(800)
                page.screenshot(path=str(OUT / "16-edit-transaksi.png"))
                print("OK  16-edit-transaksi.png (viewport pada form)")
                captured = True
            except Exception as e:
                print("  (info) viewport shot gagal, fallback full_page:", e)
            if not captured:
                shot(page, "16-edit-transaksi.png")
        else:
            print("  (GAGAL) 16-edit-transaksi.png: tidak ada tombol Edit")
            missing.append("16-edit-transaksi.png")

        ctx.close()
        browser.close()

    print("\nSelesai. Screenshot di", OUT)
    if missing:
        print("TIDAK TERAMBIL:", ", ".join(missing))
    else:
        print("Semua screenshot berhasil diambil.")


if __name__ == "__main__":
    main()
