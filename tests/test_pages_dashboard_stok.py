"""
Test AppTest untuk seksi Ringkasan Stok di Dashboard (T6).

Konvensi:
  - impor langsung dari root (tanpa conftest)
  - AppTest.from_function menjalankan render_dashboard(conn) pada DB temp
    yang sudah di-seed jurnal (seed_database) DAN stok (seed_stok)
  - asserts: label kartu stok BARU + guardrail caption + label keuangan LAMA
  - menulis bukti smoke ke .omo/evidence/task-6-dashboard.txt
"""
import os

from streamlit.testing.v1 import AppTest


def _script(dbpath):
    """Script Streamlit: seed DB temp lalu render dashboard penuh."""
    import database as db
    import pages_dashboard

    conn = db.create_connection(dbpath)
    db.create_tables(conn)
    db.seed_database(conn)   # jurnal -> kartu keuangan
    db.seed_stok(conn)       # stok   -> kartu ringkasan stok
    pages_dashboard.render_dashboard(conn)


def _kumpulkan_teks(at):
    """Gabungkan seluruh teks markdown + caption yang dirender."""
    bagian = []
    for el in at.markdown:
        bagian.append(el.value)
    for el in at.caption:
        bagian.append(el.value)
    return "\n".join(bagian)


def test_dashboard_render_stok_section_smoke(tmp_path):
    dbpath = str(tmp_path / "t6_dashboard.db")
    at = AppTest.from_function(_script, kwargs={"dbpath": dbpath})
    at.run()

    # 1. Tidak ada exception saat render.
    assert not at.exception, f"render_dashboard melempar exception: {at.exception}"

    blob = _kumpulkan_teks(at)

    # 2. Label kartu stok BARU hadir.
    label_stok_baru = ["Jenis Item Stok", "Item Menipis", "Total Nilai Stok"]
    for label in label_stok_baru:
        assert label in blob, f"label stok '{label}' tidak ditemukan"

    # 3. Guardrail caption WAJIB ada (nilai stok BUKAN akun aset).
    assert "bukan akun aset" in blob, "guardrail caption tidak ditemukan"

    # 4. Label keuangan LAMA tetap utuh (tidak ada regresi).
    label_keuangan_lama = [
        "Total Pendapatan",
        "Total Beban",
        "Laba Bersih",
        "Modal Akhir",
        "Kas Akhir",
        "Jumlah Transaksi",
    ]
    for label in label_keuangan_lama:
        assert label in blob, f"label keuangan lama '{label}' hilang (regresi)"

    # 5. Tulis bukti smoke.
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    evidence_dir = os.path.join(repo_root, ".omo", "evidence")
    os.makedirs(evidence_dir, exist_ok=True)
    evidence_path = os.path.join(evidence_dir, "task-6-dashboard.txt")
    with open(evidence_path, "w", encoding="utf-8") as f:
        f.write("=== T6 AppTest smoke: Dashboard Ringkasan Stok ===\n\n")
        f.write("render_dashboard(conn) dijalankan via AppTest.from_function\n")
        f.write("DB temp di-seed: db.seed_database (jurnal) + db.seed_stok (stok)\n")
        f.write(f"at.exception = {at.exception!r}\n\n")
        f.write("Label kartu stok BARU ditemukan:\n")
        for label in label_stok_baru:
            f.write(f"  [OK] {label}\n")
        f.write("\nGuardrail caption ditemukan:\n")
        f.write("  [OK] 'bukan akun aset'\n")
        f.write("\nLabel keuangan LAMA tetap utuh (zero regresi):\n")
        for label in label_keuangan_lama:
            f.write(f"  [OK] {label}\n")
        f.write("\n--- Teks markdown + caption yang dirender ---\n")
        f.write(blob)
        f.write("\n")
