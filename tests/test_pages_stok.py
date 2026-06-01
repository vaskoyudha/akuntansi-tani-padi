"""
Test AppTest untuk halaman Stok / Persediaan (T5).

Konvensi (sama dengan tests/test_pages_dashboard_stok.py):
  - impor langsung dari root (tanpa conftest)
  - AppTest.from_function menjalankan render_stok(conn) pada DB temp
    yang sudah di-seed jurnal (seed_database) DAN stok (seed_stok)
  - asserts: judul halaman + 4 nama item seed, tanpa exception
  - menulis bukti smoke ke .omo/evidence/task-5-render.txt
"""
import os

from streamlit.testing.v1 import AppTest


def _script(dbpath):
    """Script Streamlit: seed DB temp lalu render halaman stok penuh."""
    import database as db
    import pages_stok

    conn = db.create_connection(dbpath)
    db.create_tables(conn)
    db.seed_database(conn)   # jurnal (agar ref_jurnal seed stok dapat tertaut)
    db.seed_stok(conn)       # 4 item + 8 pergerakan masuk
    pages_stok.render_stok(conn)


def _kumpulkan_teks(at):
    """Gabungkan seluruh teks markdown + caption yang dirender."""
    bagian = []
    for el in at.markdown:
        bagian.append(el.value)
    for el in at.caption:
        bagian.append(el.value)
    return "\n".join(bagian)


def test_pages_stok_render_smoke(tmp_path):
    dbpath = str(tmp_path / "t5_stok.db")
    at = AppTest.from_function(_script, kwargs={"dbpath": dbpath})
    at.run()

    # 1. Tidak ada exception saat render.
    assert not at.exception, f"render_stok melempar exception: {at.exception}"

    blob = _kumpulkan_teks(at)

    # 2. Judul halaman hadir.
    assert "Stok / Persediaan" in blob, "judul halaman tidak ditemukan"

    # 3. Keempat nama item seed hadir (tabel ringkasan + judul expander).
    item_seed = ["Benih", "Pupuk", "Pestisida", "Karung"]
    for nama in item_seed:
        assert nama in blob, f"nama item seed '{nama}' tidak ditemukan"

    # 4. Tulis bukti smoke.
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    evidence_dir = os.path.join(repo_root, ".omo", "evidence")
    os.makedirs(evidence_dir, exist_ok=True)
    evidence_path = os.path.join(evidence_dir, "task-5-render.txt")
    with open(evidence_path, "w", encoding="utf-8") as f:
        f.write("=== T5 AppTest smoke: Halaman Stok / Persediaan ===\n\n")
        f.write("render_stok(conn) dijalankan via AppTest.from_function\n")
        f.write("DB temp di-seed: db.seed_database (jurnal) + db.seed_stok (stok)\n")
        f.write(f"at.exception = {at.exception!r}\n\n")
        f.write("Judul halaman ditemukan:\n")
        f.write("  [OK] 'Stok / Persediaan'\n\n")
        f.write("Nama item seed ditemukan:\n")
        for nama in item_seed:
            f.write(f"  [OK] {nama}\n")
        f.write("\n--- Teks markdown + caption yang dirender ---\n")
        f.write(blob)
        f.write("\n")
