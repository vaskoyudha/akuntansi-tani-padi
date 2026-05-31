"""
accounting.py
=============
Engine akuntansi inti untuk usaha tani padi.

Menghasilkan SELURUH 11 tahap siklus akuntansi dari daftar journal entry:
  1. Jurnal Umum
  2. Buku Besar
  3. Neraca Saldo
  4. Jurnal Penyesuaian
  5. Neraca Saldo Setelah Penyesuaian
  6. Laporan Laba Rugi
  7. Laporan Perubahan Ekuitas
  8. Laporan Posisi Keuangan (Neraca)
  9. Laporan Arus Kas
 10. Jurnal Penutup
 11. Neraca Saldo Setelah Penutupan

Semua nilai uang memakai decimal.Decimal agar tidak ada galat pembulatan.
"""
from decimal import Decimal

import seed_data

D = Decimal
NOL = D("0")


# ---------------------------------------------------------------------------
# Util format
# ---------------------------------------------------------------------------
def format_rupiah(nilai):
    """Format Decimal/int menjadi string rupiah gaya Indonesia: 'Rp 17.500.000'."""
    if nilai is None:
        nilai = NOL
    n = int(D(nilai))
    negatif = n < 0
    angka = f"{abs(n):,}".replace(",", ".")
    return f"Rp {'-' if negatif else ''}{angka}"


def _info_akun(nama):
    return seed_data.AKUN_BY_NAMA.get(nama, {"tipe": "lain", "saldo_normal": "debit", "kode": ""})


# ---------------------------------------------------------------------------
# Validasi & total
# ---------------------------------------------------------------------------
def validasi_entry(entry):
    """Pastikan total debit == total kredit pada satu entry. Raise ValueError jika tidak."""
    td = sum((D(ln["debit"]) for ln in entry["lines"]), NOL)
    tk = sum((D(ln["kredit"]) for ln in entry["lines"]), NOL)
    if td != tk:
        raise ValueError(
            f"Jurnal '{entry.get('id', '?')}' tidak balance: "
            f"debit {td} != kredit {tk}"
        )
    if td == NOL:
        raise ValueError(f"Jurnal '{entry.get('id', '?')}' kosong (nilai nol).")
    return True


def total_jurnal(jurnal):
    """Kembalikan (total_debit, total_kredit) seluruh baris jurnal."""
    td = sum((D(ln["debit"]) for e in jurnal for ln in e["lines"]), NOL)
    tk = sum((D(ln["kredit"]) for e in jurnal for ln in e["lines"]), NOL)
    return td, tk


# ---------------------------------------------------------------------------
# 2. Buku Besar
# ---------------------------------------------------------------------------
def buku_besar(jurnal):
    """
    Kelompokkan mutasi per akun.
    Return: dict[nama_akun] -> {kode, tipe, total_debit, total_kredit,
                                saldo_akhir(=D-K), mutasi:[...]}
    """
    besar = {}
    for e in jurnal:
        for ln in e["lines"]:
            nama = ln["akun"]
            if nama not in besar:
                info = _info_akun(nama)
                besar[nama] = {
                    "kode": info.get("kode", ""),
                    "tipe": info.get("tipe", "lain"),
                    "saldo_normal": info.get("saldo_normal", "debit"),
                    "total_debit": NOL,
                    "total_kredit": NOL,
                    "saldo_akhir": NOL,
                    "mutasi": [],
                }
            d = D(ln["debit"])
            k = D(ln["kredit"])
            besar[nama]["total_debit"] += d
            besar[nama]["total_kredit"] += k
            besar[nama]["mutasi"].append({
                "tanggal": e.get("tanggal", ""),
                "id": e.get("id", ""),
                "keterangan": e.get("keterangan", ""),
                "debit": d,
                "kredit": k,
            })
    for nama, info in besar.items():
        info["saldo_akhir"] = info["total_debit"] - info["total_kredit"]
        # saldo berjalan di tiap mutasi
        run = NOL
        for m in info["mutasi"]:
            run += m["debit"] - m["kredit"]
            m["saldo"] = run
    return besar


# ---------------------------------------------------------------------------
# 3 / 5 / 11. Neraca Saldo (umum)
# ---------------------------------------------------------------------------
def _neraca_saldo_rows(jurnal, tipe_diizinkan=None):
    """Bangun baris neraca saldo dari buku besar. Akun bersaldo nol dilewati."""
    besar = buku_besar(jurnal)
    rows = []
    total_d = NOL
    total_k = NOL
    # urut berdasarkan kode akun
    for nama in sorted(besar, key=lambda n: besar[n]["kode"]):
        info = besar[nama]
        if tipe_diizinkan is not None and info["tipe"] not in tipe_diizinkan:
            continue
        saldo = info["saldo_akhir"]
        if saldo == NOL:
            continue
        if saldo > NOL:
            debit, kredit = saldo, NOL
        else:
            debit, kredit = NOL, -saldo
        rows.append({
            "kode": info["kode"],
            "akun": nama,
            "debit": debit,
            "kredit": kredit,
        })
        total_d += debit
        total_k += kredit
    return {"rows": rows, "total_debit": total_d, "total_kredit": total_k}


def neraca_saldo(jurnal):
    """Neraca saldo seluruh akun (dipakai juga untuk 'setelah penyesuaian')."""
    return _neraca_saldo_rows(jurnal)


def neraca_saldo_setelah_penutupan(jurnal):
    """Hanya akun riil (aset, kewajiban, ekuitas). Akun nominal sudah nol."""
    return _neraca_saldo_rows(jurnal, tipe_diizinkan={"aset", "kewajiban", "ekuitas"})


# ---------------------------------------------------------------------------
# 4. Jurnal Penyesuaian
# ---------------------------------------------------------------------------
def get_jurnal_penyesuaian():
    """
    Jurnal penyesuaian akhir periode.

    AJP1 - Pemakaian perlengkapan (karung):
      2.500 kg gabah dipanen, 1 karung memuat ~50 kg -> 50 karung terpakai.
      Seluruh 50 karung (Rp100.000) terpakai habis pada panen ini,
      sehingga perlengkapan diakui sebagai beban.
    """
    L = seed_data._line
    return [
        seed_data._entry(
            "AJP1", "2025-04-30",
            "Penyesuaian pemakaian perlengkapan (karung) saat panen",
            [L("518", debit="100000"), L("113", kredit="100000")],
        ),
    ]


# ---------------------------------------------------------------------------
# 6. Laporan Laba Rugi
# ---------------------------------------------------------------------------
def laba_rugi(jurnal):
    """Hitung pendapatan, beban, laba bersih dari buku besar (idealnya sudah disesuaikan)."""
    besar = buku_besar(jurnal)
    pendapatan_rows = []
    beban_rows = []
    total_pendapatan = NOL
    total_beban = NOL
    for nama in sorted(besar, key=lambda n: besar[n]["kode"]):
        info = besar[nama]
        if info["tipe"] == "pendapatan":
            nilai = info["total_kredit"] - info["total_debit"]
            pendapatan_rows.append({"akun": nama, "nilai": nilai})
            total_pendapatan += nilai
        elif info["tipe"] == "beban":
            nilai = info["total_debit"] - info["total_kredit"]
            beban_rows.append({"akun": nama, "nilai": nilai})
            total_beban += nilai
    return {
        "pendapatan_rows": pendapatan_rows,
        "beban_rows": beban_rows,
        "total_pendapatan": total_pendapatan,
        "total_beban": total_beban,
        "laba_bersih": total_pendapatan - total_beban,
    }


# ---------------------------------------------------------------------------
# 7. Laporan Perubahan Ekuitas
# ---------------------------------------------------------------------------
def perubahan_ekuitas(jurnal):
    """Modal akhir = modal awal + laba bersih - prive."""
    besar = buku_besar(jurnal)
    modal_awal = NOL
    if "Modal Petani" in besar:
        info = besar["Modal Petani"]
        modal_awal = info["total_kredit"] - info["total_debit"]
    prive = NOL
    if "Prive" in besar:
        info = besar["Prive"]
        prive = info["total_debit"] - info["total_kredit"]
    lr = laba_rugi(jurnal)
    laba = lr["laba_bersih"]
    return {
        "modal_awal": modal_awal,
        "laba_bersih": laba,
        "prive": prive,
        "modal_akhir": modal_awal + laba - prive,
    }


# ---------------------------------------------------------------------------
# 8. Laporan Posisi Keuangan (Neraca)
# ---------------------------------------------------------------------------
def posisi_keuangan(jurnal):
    """Aset di kiri; kewajiban + ekuitas (modal akhir) di kanan. Harus balance."""
    besar = buku_besar(jurnal)
    aset_rows = []
    kewajiban_rows = []
    total_aset = NOL
    total_kewajiban = NOL
    for nama in sorted(besar, key=lambda n: besar[n]["kode"]):
        info = besar[nama]
        saldo = info["saldo_akhir"]
        if info["tipe"] == "aset":
            if saldo != NOL:
                aset_rows.append({"akun": nama, "nilai": saldo})
            total_aset += saldo
        elif info["tipe"] == "kewajiban":
            nilai = -saldo  # saldo normal kredit
            if nilai != NOL:
                kewajiban_rows.append({"akun": nama, "nilai": nilai})
            total_kewajiban += nilai
    eq = perubahan_ekuitas(jurnal)
    modal_akhir = eq["modal_akhir"]
    return {
        "aset_rows": aset_rows,
        "kewajiban_rows": kewajiban_rows,
        "modal_akhir": modal_akhir,
        "total_aset": total_aset,
        "total_kewajiban": total_kewajiban,
        "total_ekuitas": modal_akhir,
        "total_kewajiban_ekuitas": total_kewajiban + modal_akhir,
    }


# ---------------------------------------------------------------------------
# 9. Laporan Arus Kas (metode langsung)
# ---------------------------------------------------------------------------
def _kategori_arus(kode, tipe):
    """Klasifikasi arus kas berdasarkan akun lawan dari Kas."""
    if kode in ("112", "113"):       # piutang usaha, perlengkapan -> operasional
        return "operasi"
    if tipe in ("pendapatan", "beban"):
        return "operasi"
    if tipe in ("ekuitas", "kontra_ekuitas"):
        return "pendanaan"
    if tipe == "kewajiban":
        return "pendanaan"
    return "investasi"


def arus_kas(jurnal):
    """
    Metode langsung. Telusuri tiap entry yang menyentuh Kas,
    klasifikasikan berdasarkan akun lawannya.
    """
    operasi = NOL
    pendanaan = NOL
    investasi = NOL
    rincian = {"operasi": [], "pendanaan": [], "investasi": []}

    for e in jurnal:
        # nilai kas bersih di entry ini (debit = masuk, kredit = keluar)
        kas_masuk = NOL
        kas_keluar = NOL
        lawan = []
        for ln in e["lines"]:
            if ln["akun"] == "Kas":
                kas_masuk += D(ln["debit"])
                kas_keluar += D(ln["kredit"])
            else:
                lawan.append(ln)
        delta = kas_masuk - kas_keluar
        if delta == NOL or not lawan:
            continue
        # asumsi satu akun lawan dominan per transaksi kas
        ln = lawan[0]
        info = _info_akun(ln["akun"])
        kat = _kategori_arus(info.get("kode", ""), info.get("tipe", "lain"))
        if kat == "operasi":
            operasi += delta
        elif kat == "pendanaan":
            pendanaan += delta
        else:
            investasi += delta
        rincian[kat].append({
            "id": e.get("id", ""),
            "keterangan": e.get("keterangan", ""),
            "nilai": delta,
        })

    # kas awal = 0 (usaha baru dimulai musim ini)
    kas_awal = NOL
    kenaikan = operasi + pendanaan + investasi
    return {
        "operasi": operasi,
        "pendanaan": pendanaan,
        "investasi": investasi,
        "kenaikan_kas": kenaikan,
        "kas_awal": kas_awal,
        "kas_akhir": kas_awal + kenaikan,
        "rincian": rincian,
    }


# ---------------------------------------------------------------------------
# 10. Jurnal Penutup
# ---------------------------------------------------------------------------
def jurnal_penutup(jurnal):
    """
    Tutup akun nominal:
      JP1 tutup pendapatan -> Ikhtisar
      JP2 tutup beban      -> Ikhtisar
      JP3 tutup Ikhtisar   -> Modal (laba/rugi)
      JP4 tutup Prive      -> Modal
    Input sebaiknya jurnal yang sudah disesuaikan.
    """
    besar = buku_besar(jurnal)
    entries = []

    def L(kode, debit: "str | Decimal" = "0", kredit: "str | Decimal" = "0"):
        return seed_data._line(kode, debit=str(debit), kredit=str(kredit))

    # JP1 - tutup pendapatan
    lines_p = []
    total_pendapatan = NOL
    for nama, info in besar.items():
        if info["tipe"] == "pendapatan":
            saldo = info["total_kredit"] - info["total_debit"]
            if saldo != NOL:
                lines_p.append(L(info["kode"], debit=saldo))  # debit pendapatan
                total_pendapatan += saldo
    if total_pendapatan != NOL:
        lines_p.append(L("313", kredit=total_pendapatan))     # kredit ikhtisar
        entries.append(seed_data._entry("JP1", "2025-04-30", "Menutup akun pendapatan ke ikhtisar", lines_p))

    # JP2 - tutup beban
    lines_b = []
    total_beban = NOL
    for nama in sorted(besar, key=lambda n: besar[n]["kode"]):
        info = besar[nama]
        if info["tipe"] == "beban":
            saldo = info["total_debit"] - info["total_kredit"]
            if saldo != NOL:
                lines_b.append(L(info["kode"], kredit=saldo))  # kredit beban
                total_beban += saldo
    if total_beban != NOL:
        lines_b = [L("313", debit=total_beban)] + lines_b      # debit ikhtisar
        entries.append(seed_data._entry("JP2", "2025-04-30", "Menutup akun beban ke ikhtisar", lines_b))

    # JP3 - tutup ikhtisar ke modal
    laba = total_pendapatan - total_beban
    if laba > NOL:
        entries.append(seed_data._entry(
            "JP3", "2025-04-30", "Menutup ikhtisar laba rugi ke modal (laba)",
            [L("313", debit=laba), L("311", kredit=laba)],
        ))
    elif laba < NOL:
        rugi = -laba
        entries.append(seed_data._entry(
            "JP3", "2025-04-30", "Menutup ikhtisar laba rugi ke modal (rugi)",
            [L("311", debit=rugi), L("313", kredit=rugi)],
        ))

    # JP4 - tutup prive ke modal
    prive = NOL
    if "Prive" in besar:
        info = besar["Prive"]
        prive = info["total_debit"] - info["total_kredit"]
    if prive != NOL:
        entries.append(seed_data._entry(
            "JP4", "2025-04-30", "Menutup akun prive ke modal",
            [L("311", debit=prive), L("312", kredit=prive)],
        ))

    return entries
