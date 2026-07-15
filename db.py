"""
db.py
Lapisan database (SQLite) untuk Aplikasi Penjadwal Sekolah.
Berisi definisi skema tabel, data dummy awal (berdasarkan contoh data
guru/mapel/kelas yang diberikan), dan fungsi-fungsi CRUD yang dipakai
oleh app.py.
"""

import os
import sqlite3
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jadwal.db")


# ---------------------------------------------------------------------------
# Koneksi & inisialisasi
# ---------------------------------------------------------------------------

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS guru (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS kelas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jurusan TEXT NOT NULL,
            tingkat TEXT NOT NULL,
            nama_kelas TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS mapel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kode TEXT NOT NULL UNIQUE,
            nama_mapel TEXT NOT NULL,
            guru_id INTEGER,
            FOREIGN KEY (guru_id) REFERENCES guru(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS beban_ajar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mapel_id INTEGER NOT NULL,
            kelas_id INTEGER NOT NULL,
            jam_per_minggu INTEGER NOT NULL,
            FOREIGN KEY (mapel_id) REFERENCES mapel(id) ON DELETE CASCADE,
            FOREIGN KEY (kelas_id) REFERENCES kelas(id) ON DELETE CASCADE,
            UNIQUE(mapel_id, kelas_id)
        );

        CREATE TABLE IF NOT EXISTS versi_jadwal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT NOT NULL,
            dibuat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_slot INTEGER DEFAULT 0,
            unplaced_slot INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS jadwal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kelas_id INTEGER NOT NULL,
            mapel_id INTEGER NOT NULL,
            hari TEXT NOT NULL,
            jam_ke INTEGER NOT NULL,
            versi_id INTEGER,
            FOREIGN KEY (kelas_id) REFERENCES kelas(id) ON DELETE CASCADE,
            FOREIGN KEY (mapel_id) REFERENCES mapel(id) ON DELETE CASCADE,
            FOREIGN KEY (versi_id) REFERENCES versi_jadwal(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS preferensi_guru (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guru_id INTEGER NOT NULL REFERENCES guru(id) ON DELETE CASCADE,
            preferensi_hari TEXT,
            preferensi_waktu TEXT,
            bobot INTEGER DEFAULT 5
        );

        CREATE TABLE IF NOT EXISTS aturan_mapel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mapel_id INTEGER NOT NULL UNIQUE REFERENCES mapel(id) ON DELETE CASCADE,
            pagi_saja BOOLEAN DEFAULT FALSE,
            max_jam_ke INTEGER
        );

        CREATE TABLE IF NOT EXISTS pengaturan (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """
    )
    conn.commit()

    # Migration: add versi_id column if missing (existing database)
    cur.execute("PRAGMA table_info(jadwal)")
    cols = [r[1] for r in cur.fetchall()]
    if "versi_id" not in cols:
        cur.execute("ALTER TABLE jadwal ADD COLUMN versi_id INTEGER REFERENCES versi_jadwal(id) ON DELETE CASCADE")
        conn.commit()

    cur.execute("SELECT COUNT(*) FROM guru")
    if cur.fetchone()[0] == 0:
        _seed_dummy(conn)

    _ensure_settings(conn)

    conn.close()


def _ensure_settings(conn):
    defaults = {
        "hari_aktif": "Senin,Selasa,Rabu,Kamis,Jumat",
        "jam_per_hari": "8",
        "max_blok": "2",
        "waktu_mulai": "07:00",
        "durasi_jam": "35",
        "durasi_aktivitas_khusus": "35",
        "istirahat": '[{"setelah":3,"durasi":30},{"setelah":6,"durasi":35}]',
        "nama_sekolah": "SD NEGERI .....",
        "tahun_pelajaran": "2025/2026",
        "aktivitas_khusus": '{"Senin":"Upacara","Selasa":"Literasi","Rabu":"Senam","Kamis":"Asmaul Husna","Jumat":"Bersih \\u0026 Sehat","Sabtu":"Numerasi"}',
    }
    for key, value in defaults.items():
        conn.execute(
            "INSERT OR IGNORE INTO pengaturan (key, value) VALUES (?, ?)",
            (key, value),
        )
    conn.commit()


def _seed_dummy(conn):
    """Mengisi data dummy awal berdasarkan contoh data guru/mapel/kelas/beban ajar."""
    cur = conn.cursor()

    guru_list = [
        "Saepudin, S.Pd.I",
        "Muhaemin, S.Pd.I",
        "Sunardi, S.Pd",
        "Jinely, S.Ak",
        "Iis Siti Mukhlisoh, S.Pd",
        "H. Yayah Murtasiah, S.Kom",
        "Tuti Ratnawati, S.Pd",
        "Muhibah, S.Pd",
        "Ari Bagas Setiawan, S.Pd",
        "Jujun, S.Pd",
        "Iin Irna Suherni, S.T",
        "Supardi",
        "Donna Al Hafiedz, S.Pd",
        "Afif Nur Aysah, S.Kom",
    ]
    cur.executemany("INSERT INTO guru (nama) VALUES (?)", [(g,) for g in guru_list])

    kelas_list = [
        ("TKJ", "X", "TKJ X"),
        ("TKJ", "XI", "TKJ XI"),
        ("TKJ", "XII", "TKJ XII-1"),
        ("TKJ", "XII", "TKJ XII-2"),
        ("MPLB", "X", "MPLB X"),
        ("MPLB", "XI", "MPLB XI"),
        ("TSM", "X", "TSM X"),
        ("TSM", "XI", "TSM XI"),
        ("TSM", "XII", "TSM XII"),
        ("AKL", "X", "AKL X"),
    ]
    cur.executemany(
        "INSERT INTO kelas (jurusan, tingkat, nama_kelas) VALUES (?, ?, ?)", kelas_list
    )

    # kode, nama_mapel, nama_guru
    # Catatan: kode "H1" pada gambar sumber tampak dobel (dipakai utk 2 mapel).
    # Di sini dibetulkan menjadi H1 & H2 supaya kode tetap unik.
    mapel_list = [
        ("A", "Baca Tulis Al-Qur'an", "Saepudin, S.Pd.I"),
        ("B1", "Pendidikan Agama dan Budi Pekerti", "Muhaemin, S.Pd.I"),
        ("B2", "Baca Tulis Al-Qur'an", "Muhaemin, S.Pd.I"),
        ("C", "Bahasa Indonesia", "Sunardi, S.Pd"),
        ("D", "Matematika", "Jinely, S.Ak"),
        ("E", "Sejarah Indonesia", "Iis Siti Mukhlisoh, S.Pd"),
        ("F1", "Bahasa Indonesia", "H. Yayah Murtasiah, S.Kom"),
        ("F2", "Informatika", "H. Yayah Murtasiah, S.Kom"),
        ("F3", "Sejarah Indonesia", "H. Yayah Murtasiah, S.Kom"),
        ("G", "Bahasa Inggris", "Tuti Ratnawati, S.Pd"),
        ("H1", "Seni Budaya", "Muhibah, S.Pd"),
        ("H2", "Produk Kreatif dan Kewirausahaan", "Muhibah, S.Pd"),
        ("J", "PJOK", "Ari Bagas Setiawan, S.Pd"),
        ("K", "Pendidikan Pancasila dan Kewarganegaraan", "Jujun, S.Pd"),
        ("L", "Pendidikan Pancasila dan Kewarganegaraan", "Iin Irna Suherni, S.T"),
        ("M", "Pendidikan Pancasila dan Kewarganegaraan", "Supardi"),
        ("N1", "IPAS", "Donna Al Hafiedz, S.Pd"),
        ("N2", "Dasar-Dasar Kejuruan TSM", "Donna Al Hafiedz, S.Pd"),
        ("N3", "Pemeliharaan Listrik Sepeda Motor (Kelas 11)", "Donna Al Hafiedz, S.Pd"),
        ("O1", "Dasar-Dasar Kejuruan TKJ", "Afif Nur Aysah, S.Kom"),
        ("O2", "Koding dan Kecerdasan Artifisial", "Afif Nur Aysah, S.Kom"),
    ]

    guru_id_map = {}
    for row in cur.execute("SELECT id, nama FROM guru"):
        guru_id_map[row[1]] = row[0]

    for kode, nama_mapel, nama_guru in mapel_list:
        cur.execute(
            "INSERT INTO mapel (kode, nama_mapel, guru_id) VALUES (?, ?, ?)",
            (kode, nama_mapel, guru_id_map.get(nama_guru)),
        )

    mapel_id_map = {}
    for row in cur.execute("SELECT id, kode FROM mapel"):
        mapel_id_map[row[1]] = row[0]

    kelas_id_map = {}
    for row in cur.execute("SELECT id, nama_kelas FROM kelas"):
        kelas_id_map[row[1]] = row[0]

    # Beban ajar (jam per minggu) per kode mapel x kelas.
    # Nilai berikut adalah data dummy yang mengikuti pola pada contoh gambar;
    # silakan sesuaikan lagi lewat menu "Beban Ajar" di aplikasi.
    beban_ajar = {
        "A": {"TKJ X": 2, "MPLB X": 2, "TSM X": 2, "AKL X": 2},
        "B1": {"TKJ XI": 2, "MPLB XI": 2, "TSM XII": 2},
        "B2": {
            "TKJ XI": 3, "TKJ XII-1": 3, "TKJ XII-2": 3,
            "MPLB XI": 3, "TSM XI": 3, "TSM XII": 3,
        },
        "C": {"TKJ X": 2, "MPLB X": 2, "TSM X": 2, "AKL X": 2},
        "D": {
            "TKJ X": 4, "TKJ XI": 3, "TKJ XII-1": 3, "TKJ XII-2": 3,
            "MPLB X": 4, "MPLB XI": 3,
            "TSM X": 4, "TSM XI": 3, "TSM XII": 3,
            "AKL X": 4,
        },
        "E": {"TKJ X": 2, "MPLB X": 2, "TSM X": 2, "AKL X": 2},
        "F1": {
            "TKJ XI": 3, "TKJ XII-1": 3, "TKJ XII-2": 3,
            "MPLB XI": 3, "TSM XI": 3, "TSM XII": 3,
        },
        "F2": {"TKJ X": 3, "MPLB X": 3, "TSM X": 3, "AKL X": 3},
        "F3": {
            "TKJ XI": 2, "TKJ XII-1": 2, "TKJ XII-2": 2,
            "MPLB XI": 2, "TSM XI": 2, "TSM XII": 2,
        },
        "G": {
            "TKJ X": 4, "TKJ XI": 4, "TKJ XII-1": 4, "TKJ XII-2": 4,
            "MPLB X": 4, "MPLB XI": 4,
            "TSM X": 4, "TSM XI": 4, "TSM XII": 4,
            "AKL X": 4,
        },
        "H1": {"TKJ X": 2, "MPLB X": 2, "TSM X": 2, "AKL X": 2},
        "H2": {"TKJ XII-1": 5, "TKJ XII-2": 5},
        "J": {
            "TKJ X": 3, "TKJ XI": 2,
            "MPLB X": 3, "MPLB XI": 2,
            "TSM X": 3, "TSM XI": 2,
            "AKL X": 3,
        },
        "K": {"TKJ X": 2, "MPLB X": 2, "TSM X": 2, "AKL X": 2},
        "L": {"TKJ XI": 2, "MPLB XI": 2, "TSM XI": 2},
        "M": {"TKJ XII-1": 2, "TKJ XII-2": 2, "TSM XII": 2},
        "N1": {"TKJ X": 6, "MPLB X": 6, "TSM X": 6, "AKL X": 6},
        "N2": {"TSM X": 12},
        "N3": {"TSM XI": 6},
        "O1": {"TKJ X": 12},
        "O2": {"TKJ XI": 6},
    }

    for kode, kelas_map in beban_ajar.items():
        mapel_id = mapel_id_map.get(kode)
        if not mapel_id:
            continue
        for nama_kelas, jam in kelas_map.items():
            kelas_id = kelas_id_map.get(nama_kelas)
            if not kelas_id:
                continue
            cur.execute(
                "INSERT OR IGNORE INTO beban_ajar (mapel_id, kelas_id, jam_per_minggu) "
                "VALUES (?, ?, ?)",
                (mapel_id, kelas_id, jam),
            )

    conn.commit()


# ---------------------------------------------------------------------------
# Pengaturan (key-value)
# ---------------------------------------------------------------------------

def get_setting(key, default=None):
    conn = get_conn()
    row = conn.execute("SELECT value FROM pengaturan WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row[0] if row else default


def set_setting(key, value):
    conn = get_conn()
    conn.execute(
        "INSERT INTO pengaturan (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# GURU
# ---------------------------------------------------------------------------

def get_guru_df():
    conn = get_conn()
    df = pd.read_sql("SELECT id, nama FROM guru ORDER BY nama", conn)
    conn.close()
    return df


def save_guru_df(df):
    """Menyinkronkan tabel guru dengan isi DataFrame hasil edit di UI."""
    conn = get_conn()
    cur = conn.cursor()
    existing_ids = {r[0] for r in cur.execute("SELECT id FROM guru")}
    kept_ids = set()

    for _, row in df.iterrows():
        nama = str(row.get("nama", "")).strip()
        if not nama:
            continue
        rid = row.get("id")
        if pd.notna(rid) and int(rid) in existing_ids:
            cur.execute("UPDATE guru SET nama = ? WHERE id = ?", (nama, int(rid)))
            kept_ids.add(int(rid))
        else:
            cur.execute("INSERT OR IGNORE INTO guru (nama) VALUES (?)", (nama,))

    to_delete = existing_ids - kept_ids
    for rid in to_delete:
        cur.execute("DELETE FROM guru WHERE id = ?", (rid,))

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# KELAS
# ---------------------------------------------------------------------------

def get_kelas_df():
    conn = get_conn()
    df = pd.read_sql(
        "SELECT id, jurusan, tingkat, nama_kelas FROM kelas ORDER BY jurusan, tingkat, nama_kelas",
        conn,
    )
    conn.close()
    return df


def save_kelas_df(df):
    conn = get_conn()
    cur = conn.cursor()
    existing_ids = {r[0] for r in cur.execute("SELECT id FROM kelas")}
    kept_ids = set()

    for _, row in df.iterrows():
        nama_kelas = str(row.get("nama_kelas", "")).strip()
        jurusan = str(row.get("jurusan", "")).strip()
        tingkat = str(row.get("tingkat", "")).strip()
        if not nama_kelas:
            continue
        rid = row.get("id")
        if pd.notna(rid) and int(rid) in existing_ids:
            cur.execute(
                "UPDATE kelas SET jurusan = ?, tingkat = ?, nama_kelas = ? WHERE id = ?",
                (jurusan, tingkat, nama_kelas, int(rid)),
            )
            kept_ids.add(int(rid))
        else:
            cur.execute(
                "INSERT OR IGNORE INTO kelas (jurusan, tingkat, nama_kelas) VALUES (?, ?, ?)",
                (jurusan, tingkat, nama_kelas),
            )

    to_delete = existing_ids - kept_ids
    for rid in to_delete:
        cur.execute("DELETE FROM kelas WHERE id = ?", (rid,))

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# MAPEL (penugasan kode -> guru -> mata pelajaran)
# ---------------------------------------------------------------------------

def get_mapel_df():
    conn = get_conn()
    df = pd.read_sql(
        """
        SELECT m.id, m.kode, m.nama_mapel, g.nama AS guru,
               COALESCE(a.pagi_saja, 0) AS pagi_saja,
               a.max_jam_ke
        FROM mapel m
        LEFT JOIN guru g ON g.id = m.guru_id
        LEFT JOIN aturan_mapel a ON a.mapel_id = m.id
        ORDER BY m.kode
        """,
        conn,
    )
    conn.close()
    df["pagi_saja"] = df["pagi_saja"].astype(bool)
    df["max_jam_ke"] = df["max_jam_ke"].astype("Int64")
    return df


def save_mapel_df(df):
    conn = get_conn()
    cur = conn.cursor()
    guru_map = {r[1]: r[0] for r in cur.execute("SELECT id, nama FROM guru")}
    existing_ids = {r[0] for r in cur.execute("SELECT id FROM mapel")}
    kept_ids = set()

    for _, row in df.iterrows():
        kode = str(row.get("kode", "")).strip()
        nama_mapel = str(row.get("nama_mapel", "")).strip()
        guru_nama = str(row.get("guru", "")).strip()
        if not kode or not nama_mapel:
            continue
        guru_id = guru_map.get(guru_nama)
        rid = row.get("id")

        if pd.notna(rid) and int(rid) in existing_ids:
            cur.execute(
                "UPDATE mapel SET kode = ?, nama_mapel = ?, guru_id = ? WHERE id = ?",
                (kode, nama_mapel, guru_id, int(rid)),
            )
            kept_ids.add(int(rid))
            mapel_id = int(rid)
        else:
            cur.execute(
                "INSERT OR IGNORE INTO mapel (kode, nama_mapel, guru_id) VALUES (?, ?, ?)",
                (kode, nama_mapel, guru_id),
            )
            mapel_id = cur.lastrowid

        pagi_saja = bool(row.get("pagi_saja", False))
        max_jam_ke = row.get("max_jam_ke")
        if pd.isna(max_jam_ke) or max_jam_ke is None:
            max_jam_ke = None
        else:
            max_jam_ke = int(max_jam_ke)

        cur.execute(
            "INSERT INTO aturan_mapel (mapel_id, pagi_saja, max_jam_ke) VALUES (?, ?, ?) "
            "ON CONFLICT(mapel_id) DO UPDATE SET pagi_saja = excluded.pagi_saja, max_jam_ke = excluded.max_jam_ke",
            (mapel_id, pagi_saja, max_jam_ke),
        )

    to_delete = existing_ids - kept_ids
    for rid in to_delete:
        cur.execute("DELETE FROM aturan_mapel WHERE mapel_id = ?", (rid,))
        cur.execute("DELETE FROM mapel WHERE id = ?", (rid,))

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# PREFERENSI GURU (hari & waktu favorit)
# ---------------------------------------------------------------------------

def get_preferensi_guru_df():
    conn = get_conn()
    df = pd.read_sql(
        """
        SELECT p.id, p.guru_id, g.nama AS guru, p.preferensi_hari,
               p.preferensi_waktu, p.bobot
        FROM preferensi_guru p
        JOIN guru g ON g.id = p.guru_id
        ORDER BY g.nama
        """,
        conn,
    )
    conn.close()
    return df


def save_preferensi_guru_df(df):
    conn = get_conn()
    cur = conn.cursor()
    existing_ids = {r[0] for r in cur.execute("SELECT id FROM preferensi_guru")}
    kept_ids = set()

    for _, row in df.iterrows():
        guru_id = row.get("guru_id")
        if pd.isna(guru_id) or guru_id is None:
            continue
        guru_id = int(guru_id)
        preferensi_hari = str(row.get("preferensi_hari", "")).strip() or None
        preferensi_waktu = str(row.get("preferensi_waktu", "")).strip() or None
        bobot = int(row.get("bobot", 5)) if pd.notna(row.get("bobot")) else 5

        rid = row.get("id")
        if pd.notna(rid) and int(rid) in existing_ids:
            cur.execute(
                "UPDATE preferensi_guru SET preferensi_hari = ?, preferensi_waktu = ?, bobot = ? WHERE id = ?",
                (preferensi_hari, preferensi_waktu, bobot, int(rid)),
            )
            kept_ids.add(int(rid))
        else:
            # Check if entry for this guru already exists
            existing = cur.execute(
                "SELECT id FROM preferensi_guru WHERE guru_id = ?", (guru_id,)
            ).fetchone()
            if existing:
                cur.execute(
                    "UPDATE preferensi_guru SET preferensi_hari = ?, preferensi_waktu = ?, bobot = ? WHERE id = ?",
                    (preferensi_hari, preferensi_waktu, bobot, existing[0]),
                )
                kept_ids.add(existing[0])
            else:
                cur.execute(
                    "INSERT INTO preferensi_guru (guru_id, preferensi_hari, preferensi_waktu, bobot) VALUES (?, ?, ?, ?)",
                    (guru_id, preferensi_hari, preferensi_waktu, bobot),
                )

    to_delete = existing_ids - kept_ids
    for rid in to_delete:
        cur.execute("DELETE FROM preferensi_guru WHERE id = ?", (rid,))

    conn.commit()
    conn.close()


def get_preferensi_guru_dict():
    """Returns {guru_id: {"hari": [...], "waktu": "...", "bobot": N}} for scheduler."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT guru_id, preferensi_hari, preferensi_waktu, bobot FROM preferensi_guru"
    ).fetchall()
    conn.close()
    result = {}
    for guru_id, hari_str, waktu, bobot in rows:
        hari_list = [h.strip() for h in hari_str.split(",")] if hari_str else []
        result[guru_id] = {"hari": hari_list, "waktu": waktu or "", "bobot": bobot}
    return result


def get_aturan_mapel_dict():
    """Returns {mapel_id: {"pagi_saja": bool, "max_jam_ke": int}} for scheduler."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT mapel_id, pagi_saja, max_jam_ke FROM aturan_mapel"
    ).fetchall()
    conn.close()
    return {r[0]: {"pagi_saja": bool(r[1]), "max_jam_ke": r[2]} for r in rows}


# ---------------------------------------------------------------------------
# BEBAN AJAR (matriks mapel x kelas -> jam/minggu)
# ---------------------------------------------------------------------------

def get_beban_ajar_pivot():
    """Mengembalikan tabel pivot: baris = kode+nama mapel, kolom = nama kelas."""
    conn = get_conn()
    mapel_df = pd.read_sql("SELECT id, kode, nama_mapel FROM mapel ORDER BY kode", conn)
    kelas_df = pd.read_sql(
        "SELECT id, nama_kelas FROM kelas ORDER BY jurusan, tingkat, nama_kelas", conn
    )
    beban_df = pd.read_sql(
        "SELECT mapel_id, kelas_id, jam_per_minggu FROM beban_ajar", conn
    )
    conn.close()

    mapel_df["label"] = mapel_df["kode"] + " - " + mapel_df["nama_mapel"]
    pivot = pd.DataFrame(
        0, index=mapel_df["label"], columns=kelas_df["nama_kelas"], dtype="Int64"
    )

    mapel_id_to_label = dict(zip(mapel_df["id"], mapel_df["label"]))
    kelas_id_to_nama = dict(zip(kelas_df["id"], kelas_df["nama_kelas"]))

    for _, r in beban_df.iterrows():
        label = mapel_id_to_label.get(r["mapel_id"])
        nama_kelas = kelas_id_to_nama.get(r["kelas_id"])
        if label is not None and nama_kelas is not None:
            pivot.loc[label, nama_kelas] = int(r["jam_per_minggu"])

    pivot = pivot.reset_index().rename(columns={"label": "Mapel"})
    return pivot


def save_beban_ajar_pivot(pivot_df):
    """Menyimpan kembali tabel pivot yang sudah diedit user ke tabel beban_ajar."""
    conn = get_conn()
    cur = conn.cursor()

    mapel_rows = {row[1]: row[0] for row in cur.execute("SELECT id, kode FROM mapel")}
    # label format: "KODE - nama mapel" -> ambil kode di depan spasi-strip-spasi pertama
    kelas_rows = {row[1]: row[0] for row in cur.execute("SELECT id, nama_kelas FROM kelas")}

    cur.execute("DELETE FROM beban_ajar")

    kelas_cols = [c for c in pivot_df.columns if c != "Mapel"]

    for _, row in pivot_df.iterrows():
        label = str(row["Mapel"])
        kode = label.split(" - ")[0].strip()
        mapel_id = mapel_rows.get(kode)
        if not mapel_id:
            continue
        for kelas_nama in kelas_cols:
            jam = row.get(kelas_nama)
            if pd.isna(jam) or jam is None:
                continue
            jam = int(jam)
            if jam <= 0:
                continue
            kelas_id = kelas_rows.get(kelas_nama)
            if not kelas_id:
                continue
            cur.execute(
                "INSERT OR REPLACE INTO beban_ajar (mapel_id, kelas_id, jam_per_minggu) "
                "VALUES (?, ?, ?)",
                (mapel_id, kelas_id, jam),
            )

    conn.commit()
    conn.close()


def get_beban_ajar_requirements():
    """List requirement untuk scheduler: kelas_id, kelas_nama, mapel_id, kode,
    nama_mapel, guru_id, guru_nama, jam_per_minggu."""
    conn = get_conn()
    df = pd.read_sql(
        """
        SELECT b.kelas_id, k.nama_kelas AS kelas_nama,
               b.mapel_id, m.kode, m.nama_mapel,
               m.guru_id, g.nama AS guru_nama,
               b.jam_per_minggu
        FROM beban_ajar b
        JOIN kelas k ON k.id = b.kelas_id
        JOIN mapel m ON m.id = b.mapel_id
        LEFT JOIN guru g ON g.id = m.guru_id
        WHERE b.jam_per_minggu > 0
        """,
        conn,
    )
    conn.close()
    return df.to_dict("records")


# ---------------------------------------------------------------------------
# JADWAL
# ---------------------------------------------------------------------------

def clear_jadwal(versi_id=None):
    conn = get_conn()
    if versi_id is not None:
        conn.execute("DELETE FROM jadwal WHERE versi_id = ?", (versi_id,))
    else:
        conn.execute("DELETE FROM jadwal")
    conn.commit()
    conn.close()


def save_jadwal(rows, versi_id=None):
    """rows: list of tuple (kelas_id, mapel_id, hari, jam_ke)"""
    conn = get_conn()
    if versi_id is not None:
        conn.executemany(
            "INSERT INTO jadwal (kelas_id, mapel_id, hari, jam_ke, versi_id) VALUES (?, ?, ?, ?, ?)",
            [(r[0], r[1], r[2], r[3], versi_id) for r in rows],
        )
    else:
        conn.executemany(
            "INSERT INTO jadwal (kelas_id, mapel_id, hari, jam_ke) VALUES (?, ?, ?, ?)",
            rows,
        )
    conn.commit()
    conn.close()


def get_jadwal_df(versi_id=None):
    conn = get_conn()
    query = """
        SELECT j.id, j.kelas_id, k.nama_kelas, j.mapel_id, m.kode, m.nama_mapel,
               g.nama AS guru_nama, j.hari, j.jam_ke
        FROM jadwal j
        JOIN kelas k ON k.id = j.kelas_id
        JOIN mapel m ON m.id = j.mapel_id
        LEFT JOIN guru g ON g.id = m.guru_id
    """
    params = ()
    if versi_id is not None:
        query += " WHERE j.versi_id = ?"
        params = (versi_id,)
    query += " ORDER BY j.hari, j.jam_ke"
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df


# ---------------------------------------------------------------------------
# VERSI JADWAL
# ---------------------------------------------------------------------------

def create_versi(nama, total_slot=0, unplaced_slot=0):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO versi_jadwal (nama, total_slot, unplaced_slot) VALUES (?, ?, ?)",
        (nama, total_slot, unplaced_slot),
    )
    conn.commit()
    versi_id = cur.lastrowid
    conn.close()
    return versi_id


def get_versi_list():
    conn = get_conn()
    df = pd.read_sql(
        "SELECT id, nama, dibuat, total_slot, unplaced_slot FROM versi_jadwal ORDER BY id",
        conn,
    )
    conn.close()
    return df


def delete_versi(versi_id):
    conn = get_conn()
    conn.execute("DELETE FROM jadwal WHERE versi_id = ?", (versi_id,))
    conn.execute("DELETE FROM versi_jadwal WHERE id = ?", (versi_id,))
    conn.commit()
    conn.close()


def update_versi_stats(versi_id, total_slot, unplaced_slot):
    conn = get_conn()
    conn.execute(
        "UPDATE versi_jadwal SET total_slot = ?, unplaced_slot = ? WHERE id = ?",
        (total_slot, unplaced_slot, versi_id),
    )
    conn.commit()
    conn.close()


def ensure_default_version():
    """Migrate old jadwal data (NULL versi_id) into a default version."""
    conn = get_conn()
    cur = conn.cursor()
    count_null = cur.execute(
        "SELECT COUNT(*) FROM jadwal WHERE versi_id IS NULL"
    ).fetchone()[0]
    ver_count = cur.execute(
        "SELECT COUNT(*) FROM versi_jadwal"
    ).fetchone()[0]
    if count_null > 0 and ver_count == 0:
        cur.execute(
            "INSERT INTO versi_jadwal (nama, total_slot, unplaced_slot) VALUES (?, ?, ?)",
            ("Versi 1", count_null, 0),
        )
        versi_id = cur.lastrowid
        cur.execute(
            "UPDATE jadwal SET versi_id = ? WHERE versi_id IS NULL",
            (versi_id,),
        )
        conn.commit()
    conn.close()


def get_all_kelas_names():
    conn = get_conn()
    names = [r[0] for r in conn.execute(
        "SELECT nama_kelas FROM kelas ORDER BY jurusan, tingkat, nama_kelas"
    )]
    conn.close()
    return names


def get_all_guru_names():
    conn = get_conn()
    names = [r[0] for r in conn.execute("SELECT nama FROM guru ORDER BY nama")]
    conn.close()
    return names


# ---------------------------------------------------------------------------
# VERIFIKASI DATA (pra-generate)
# ---------------------------------------------------------------------------

def get_verification_data():
    """Mengembalikan data untuk verifikasi pra-generate."""
    conn = get_conn()
    cur = conn.cursor()

    # 1. Mapel tanpa guru
    mapel_tanpa_guru = [
        {"kode": r[0], "nama_mapel": r[1]}
        for r in cur.execute(
            "SELECT kode, nama_mapel FROM mapel WHERE guru_id IS NULL"
        )
    ]

    # 2. Mapel tanpa beban ajar
    mapel_tanpa_beban = [
        {"kode": r[0], "nama_mapel": r[1]}
        for r in cur.execute(
            """
            SELECT m.kode, m.nama_mapel FROM mapel m
            LEFT JOIN beban_ajar b ON b.mapel_id = m.id
            WHERE b.id IS NULL
            """
        )
    ]

    # 3. Kelas tanpa beban ajar
    kelas_tanpa_beban = [
        r[0]
        for r in cur.execute(
            """
            SELECT k.nama_kelas FROM kelas k
            LEFT JOIN beban_ajar b ON b.kelas_id = k.id
            WHERE b.id IS NULL
            """
        )
    ]

    # 4. Duplikat kode mapel
    duplikat_kode = [
        r[0] for r in cur.execute(
            "SELECT kode FROM mapel GROUP BY kode HAVING COUNT(*) > 1"
        )
    ]

    # 5. Duplikat nama kelas
    duplikat_kelas = [
        r[0] for r in cur.execute(
            "SELECT nama_kelas FROM kelas GROUP BY nama_kelas HAVING COUNT(*) > 1"
        )
    ]

    # 6. Total JP per kelas
    reqs = get_beban_ajar_requirements()
    total_jp_per_kelas = {}
    for r in reqs:
        nama = r["kelas_nama"]
        total_jp_per_kelas[nama] = total_jp_per_kelas.get(nama, 0) + r["jam_per_minggu"]

    # 7. Total jam per guru
    total_jam_per_guru = {}
    for r in reqs:
        guru = r["guru_nama"] or "(tanpa guru)"
        total_jam_per_guru[guru] = total_jam_per_guru.get(guru, 0) + r["jam_per_minggu"]

    # 8. Mapel with dual assignments (same guru teaching same mapel under diff kode)
    mapel_per_guru = {}
    for r in reqs:
        guru = r["guru_nama"] or "(tanpa guru)"
        mapel_per_guru.setdefault(guru, set()).add(r["kode"])

    # 9. Counts
    jumlah_mapel = cur.execute("SELECT COUNT(*) FROM mapel").fetchone()[0]
    jumlah_kelas = cur.execute("SELECT COUNT(*) FROM kelas").fetchone()[0]
    jumlah_guru = cur.execute("SELECT COUNT(*) FROM guru").fetchone()[0]

    conn.close()

    return {
        "mapel_tanpa_guru": mapel_tanpa_guru,
        "mapel_tanpa_beban": mapel_tanpa_beban,
        "kelas_tanpa_beban": kelas_tanpa_beban,
        "duplikat_kode": duplikat_kode,
        "duplikat_kelas": duplikat_kelas,
        "total_jp_per_kelas": total_jp_per_kelas,
        "total_jam_per_guru": total_jam_per_guru,
        "jumlah_mapel": jumlah_mapel,
        "jumlah_kelas": jumlah_kelas,
        "jumlah_guru": jumlah_guru,
    }
