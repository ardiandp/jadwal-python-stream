# Aplikasi Penjadwal Sekolah (Python)

Aplikasi CRUD + generator jadwal pelajaran otomatis, dibuat berdasarkan
struktur data: **Guru → Mapel/Kode Penugasan → Kelas → Beban Ajar (jam/minggu)
→ Jadwal**.

Tersedia dua versi frontend:
- **Flask** (rekomendasi) — web app dengan autentikasi user, MySQL
- **Streamlit** — prototype cepat dengan SQLite

## Screenshot

![Dashboard](https://raw.githubusercontent.com/ardiandp/jadwal-python-stream/refs/heads/flask/screenshoot/1.png)

![Jadwal](https://raw.githubusercontent.com/ardiandp/jadwal-python-stream/refs/heads/flask/screenshoot/2.png)

## Fitur

1. **Dashboard** — ringkasan jumlah guru, kelas, mapel, dan rekap total jam
   mengajar per guru.
2. **Data Guru** — CRUD nama guru.
3. **Data Mapel & Penugasan** — CRUD kode penugasan (mis. `A`, `B1`, `B2`, ...)
   yang menghubungkan satu guru dengan satu mata pelajaran.
4. **Data Kelas** — CRUD kelas (jurusan, tingkat, nama kelas/rombel).
5. **Beban Ajar (Jam/Minggu)** — matriks editable: baris = mapel, kolom = kelas,
   isi = jam/minggu.
6. **Pengaturan Jadwal** — pilih hari aktif, jumlah jam pelajaran per hari,
   dan maksimal jam berurutan per mapel dalam sehari (blok).
7. **Generate Jadwal** — mesin penjadwal otomatis (randomized greedy,
   multi-restart) tanpa bentrok.
8. **Lihat Jadwal** — tampilan jadwal per kelas, per guru, export ke Excel.

---

## Cara Menjalankan (Flask)

### Prasyarat

- Python 3.10+
- MySQL (bisa pakai Laragon/XAMPP)
- Database `jadwal_app` sudah dibuat

### Langkah

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Install driver MySQL (belum ada di requirements.txt)
pip install mysql-connector-python

# 3. Buat database di MySQL
mysql -u root -e "CREATE DATABASE IF NOT EXISTS jadwal_app;"

# 4. Migrate data dari Streamlit SQLite ke MySQL + buat tabel + seed admin
python seed.py

# 5. Jalankan Flask
python run.py
```

Buka browser ke **`http://localhost:5000`**.

Login default: **`admin`** / **`admin123`**

### Konfigurasi

Konfigurasi database ada di `config.py`:

```python
SQLALCHEMY_DATABASE_URI = "mysql+mysqlconnector://root@localhost/jadwal_app?charset=utf8mb4"
```

Ubah jika MySQL anda pakai password atau port berbeda.

---

## Cara Menjalankan (Streamlit — versi lama)

```bash
pip install streamlit pandas openpyxl
streamlit run app.py
```

Buka browser ke `http://localhost:8501`. Data tersimpan di `jadwal.db` (SQLite).

> **Catatan:** Versi Streamlit tidak memiliki autentikasi user.

---

## Struktur File

```
├── run.py                 # Entry point Flask
├── config.py              # Konfigurasi Flask (database, secret key)
├── seed.py                # Migrasi data SQLite → MySQL + seed admin
├── requirements.txt       # Dependencies Flask
├── app/
│   ├── __init__.py        # Flask app factory
│   ├── models.py          # SQLAlchemy models (9 tabel)
│   ├── forms.py           # WTForms (login, register, settings)
│   ├── routes/            # Blueprint routes
│   │   ├── auth.py        # Login, register
│   │   ├── dashboard.py   # Dashboard
│   │   ├── master.py      # CRUD guru, kelas, mapel
│   │   ├── akademik.py    # Beban ajar, preferensi, pengaturan
│   │   └── jadwal.py      # Generate & lihat jadwal
│   ├── services/          # Business logic
│   │   ├── scheduler.py   # Mesin generate jadwal
│   │   ├── export.py      # Export Excel
│   │   └── verification.py# Verifikasi data pra-generate
│   └── templates/         # Jinja2 HTML templates
├── app.py                 # Aplikasi Streamlit (versi lama)
├── db.py                  # Database layer SQLite (versi lama)
├── scheduler.py           # Mesin jadwal (versi lama)
└── jadwal.db              # SQLite database (versi Streamlit)
```
