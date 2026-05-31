"""
seed_data.py
============
Bagan akun (chart of accounts) dan 20 transaksi seed usaha tani padi.

Data ini diturunkan langsung dari hasil wawancara petani + daftar 20 transaksi
yang diberikan klien. Dipakai sebagai data awal aplikasi (boleh ditambah manual).
"""
from decimal import Decimal

D = Decimal


# ---------------------------------------------------------------------------
# Bagan Akun
# ---------------------------------------------------------------------------
# tipe: aset | kewajiban | ekuitas | kontra_ekuitas | pendapatan | beban | ikhtisar
CHART_OF_ACCOUNTS = [
    {"kode": "111", "akun": "Kas", "tipe": "aset", "saldo_normal": "debit"},
    {"kode": "112", "akun": "Piutang Usaha", "tipe": "aset", "saldo_normal": "debit"},
    {"kode": "113", "akun": "Perlengkapan", "tipe": "aset", "saldo_normal": "debit"},
    {"kode": "311", "akun": "Modal Petani", "tipe": "ekuitas", "saldo_normal": "kredit"},
    {"kode": "312", "akun": "Prive", "tipe": "kontra_ekuitas", "saldo_normal": "debit"},
    {"kode": "313", "akun": "Ikhtisar Laba Rugi", "tipe": "ikhtisar", "saldo_normal": "kredit"},
    {"kode": "411", "akun": "Pendapatan Penjualan Gabah", "tipe": "pendapatan", "saldo_normal": "kredit"},
    {"kode": "511", "akun": "Beban Benih", "tipe": "beban", "saldo_normal": "debit"},
    {"kode": "512", "akun": "Beban Pupuk", "tipe": "beban", "saldo_normal": "debit"},
    {"kode": "513", "akun": "Beban Tenaga Kerja", "tipe": "beban", "saldo_normal": "debit"},
    {"kode": "514", "akun": "Beban Pestisida & Obat", "tipe": "beban", "saldo_normal": "debit"},
    {"kode": "515", "akun": "Beban Angkut", "tipe": "beban", "saldo_normal": "debit"},
    {"kode": "516", "akun": "Beban Konsumsi", "tipe": "beban", "saldo_normal": "debit"},
    {"kode": "517", "akun": "Beban Administrasi", "tipe": "beban", "saldo_normal": "debit"},
    {"kode": "518", "akun": "Beban Perlengkapan", "tipe": "beban", "saldo_normal": "debit"},
]

# index cepat: kode -> info akun, nama -> info akun
AKUN_BY_KODE = {a["kode"]: a for a in CHART_OF_ACCOUNTS}
AKUN_BY_NAMA = {a["akun"]: a for a in CHART_OF_ACCOUNTS}


def get_chart_of_accounts():
    """Kembalikan salinan bagan akun."""
    return [dict(a) for a in CHART_OF_ACCOUNTS]


def _line(kode, debit="0", kredit="0"):
    """Helper membuat satu baris jurnal."""
    return {
        "kode": kode,
        "akun": AKUN_BY_KODE[kode]["akun"],
        "debit": D(debit),
        "kredit": D(kredit),
    }


def _entry(id_, tanggal, keterangan, lines):
    return {"id": id_, "tanggal": tanggal, "keterangan": keterangan, "lines": lines}


# ---------------------------------------------------------------------------
# 20 Transaksi seed
# ---------------------------------------------------------------------------
def get_jurnal_seed():
    """Daftar 20 transaksi sebagai journal entries (double entry)."""
    return [
        _entry("T01", "2025-01-05", "Setoran modal awal pemilik ke kas usaha tani",
               [_line("111", debit="7000000"), _line("311", kredit="7000000")]),
        _entry("T02", "2025-01-07", "Pembelian benih padi Mekongga 10 kantong (50 kg)",
               [_line("511", debit="500000"), _line("111", kredit="500000")]),
        _entry("T03", "2025-01-10", "Upah tenaga kerja pembajakan & persiapan lahan 1,5 ha",
               [_line("513", debit="1000000"), _line("111", kredit="1000000")]),
        _entry("T04", "2025-01-12", "Pembelian pupuk Urea Pusri gelombang pertama",
               [_line("512", debit="400000"), _line("111", kredit="400000")]),
        _entry("T05", "2025-01-13", "Pembelian pupuk TSP untuk dasar tanaman",
               [_line("512", debit="300000"), _line("111", kredit="300000")]),
        _entry("T06", "2025-01-14", "Pembelian pupuk ZA sebagai campuran tambahan",
               [_line("512", debit="200000"), _line("111", kredit="200000")]),
        _entry("T07", "2025-01-18", "Upah tenaga kerja persemaian & pencabutan bibit",
               [_line("513", debit="400000"), _line("111", kredit="400000")]),
        _entry("T08", "2025-01-25", "Upah buruh tanam (tandur) manual lahan 1,5 ha",
               [_line("513", debit="800000"), _line("111", kredit="800000")]),
        _entry("T09", "2025-02-05", "Pembelian pestisida tahap pertama (antisipasi hama)",
               [_line("514", debit="200000"), _line("111", kredit="200000")]),
        _entry("T10", "2025-02-15", "Upah tenaga kerja penyiangan (membersihkan gulma)",
               [_line("513", debit="500000"), _line("111", kredit="500000")]),
        _entry("T11", "2025-02-25", "Pembelian obat-obatan tanaman susulan (hama sulit sembuh)",
               [_line("514", debit="200000"), _line("111", kredit="200000")]),
        _entry("T12", "2025-03-10", "Pembelian pestisida/vitamin jelang masa bunting padi",
               [_line("514", debit="100000"), _line("111", kredit="100000")]),
        _entry("T13", "2025-03-20", "Upah buruh harian penyemprotan massal hama",
               [_line("513", debit="300000"), _line("111", kredit="300000")]),
        _entry("T14", "2025-04-20", "Penyerahan gabah 2.500 kg ke tengkulak @Rp7.000 (kredit)",
               [_line("112", debit="17500000"), _line("411", kredit="17500000")]),
        _entry("T15", "2025-04-22", "Penerimaan pelunasan tunai dari tengkulak",
               [_line("111", debit="17500000"), _line("112", kredit="17500000")]),
        _entry("T16", "2025-04-19", "Pembelian karung gabah 50 lembar tunai",
               [_line("113", debit="100000"), _line("111", kredit="100000")]),
        _entry("T17", "2025-04-21", "Upah buruh angkut gabah dari sawah ke pinggir jalan",
               [_line("515", debit="700000"), _line("111", kredit="700000")]),
        _entry("T18", "2025-04-21", "Biaya konsumsi (makan & rokok) buruh selama panen",
               [_line("516", debit="250000"), _line("111", kredit="250000")]),
        _entry("T19", "2025-04-28", "Pengurusan administrasi SPPT/Kartu Tani musim depan",
               [_line("517", debit="50000"), _line("111", kredit="50000")]),
        _entry("T20", "2025-04-30", "Alokasi keuntungan ke tabungan keluarga (prive)",
               [_line("312", debit="4500000"), _line("111", kredit="4500000")]),
    ]
