# Aplikasi Penjadwal Sekolah (Python + Streamlit)

Aplikasi CRUD + generator jadwal pelajaran otomatis, dibuat berdasarkan
struktur data: **Guru → Mapel/Kode Penugasan → Kelas → Beban Ajar (jam/minggu)
→ Jadwal**.

## Fitur

1. **Dashboard** — ringkasan jumlah guru, kelas, mapel, dan rekap total jam
   mengajar per guru.
2. **Data Guru** — CRUD nama guru.
3. **Data Mapel & Penugasan** — CRUD kode penugasan (mis. `A`, `B1`, `B2`, ...)
   yang menghubungkan satu guru dengan satu mata pelajaran. Satu guru boleh
   punya banyak kode jika mengampu beberapa mapel.
4. **Data Kelas** — CRUD kelas (jurusan, tingkat, nama kelas/rombel).
5. **Beban Ajar (Jam/Minggu)** — matriks editable persis seperti tabel
   "Beban Ajar Mata Pelajaran" pada data sumber: baris = mapel, kolom = kelas,
   isi = jam/minggu.
6. **Pengaturan Jadwal** — pilih hari aktif, jumlah jam pelajaran per hari,
   dan maksimal jam berurutan per mapel dalam sehari (blok).
7. **Generate Jadwal** — mesin penjadwal otomatis (randomized greedy,
   multi-restart) yang menyusun jadwal tanpa bentrok:
   - satu kelas tidak mungkin punya 2 mapel di jam yang sama,
   - satu guru tidak mungkin mengajar 2 kelas di jam yang sama.
8. **Lihat Jadwal** — tampilan jadwal per kelas, per guru, tabel mentah, dan
   tombol unduh ke Excel (satu sheet per kelas).

## Cara Menjalankan

```bash
cd jadwal_app
pip install -r requirements.txt
streamlit run app.py
```

Aplikasi akan membuka browser ke `http://localhost:8501`. Semua data
tersimpan otomatis di file `jadwal.db` (SQLite) pada folder yang sama, jadi
tidak hilang saat aplikasi ditutup/dijalankan ulang.

## Data Dummy Awal

Saat pertama kali dijalankan, aplikasi otomatis mengisi:
- 14 guru,
- 10 kelas (TKJ X/XI/XII-1/XII-2, MPLB X/XI, TSM X/XI/XII, AKL X),
- 21 kode penugasan mapel (mengikuti contoh: A, B1, B2, C, D, E, F1–F3, G,
  H1, H2, J, K, L, M, N1–N3, O1, O2),
- beban ajar (jam/minggu) untuk tiap kombinasi mapel–kelas.

> **Catatan:** Kode `H1` pada foto sumber tampak dipakai dua kali (untuk
> "Seni Budaya" dan "Produk Kreatif dan Kewirausahaan"). Di aplikasi ini
> dibetulkan menjadi `H1` dan `H2` agar tetap unik. Nilai jam pada beberapa
> baris beban ajar juga merupakan estimasi mendekati foto sumber yang sedikit
> buram — silakan sesuaikan langsung lewat menu **Beban Ajar** sesuai data
> riil sekolah Anda. Semua data (guru, mapel, kelas, beban ajar) bisa diedit
> bebas — data dummy ini hanya starting point.

## Cara Kerja Mesin Penjadwal

1. Setiap baris beban ajar (mapel di kelas tertentu, sekian jam/minggu)
   dipecah jadi blok maksimal `max_blok` jam berurutan (default 2), misal
   4 jam → dua blok @2 jam.
2. Semua blok dari semua kelas digabung lalu diacak urutannya.
3. Setiap blok dicoba ditempatkan pada slot (hari, jam) yang kosong untuk
   kelas tsb **dan** kosong untuk guru pengampunya.
4. Jika ada blok gagal ditempatkan, seluruh proses diulang (multi-restart,
   default hingga 300 kali) dengan urutan acak berbeda, lalu diambil hasil
   dengan jumlah kegagalan paling sedikit.
5. Jika kapasitas hari/jam aktif tidak cukup dibanding total beban, akan ada
   sisa jam yang gagal ditempatkan — aplikasi menampilkan daftarnya di
   halaman **Generate Jadwal** agar bisa disesuaikan (tambah hari/jam aktif,
   atau kurangi beban).

## Struktur File

```
jadwal_app/
├── app.py            # Aplikasi Streamlit (UI, CRUD, halaman)
├── db.py             # Lapisan database SQLite + seed data dummy
├── scheduler.py       # Mesin generate jadwal
├── requirements.txt
└── jadwal.db          # dibuat otomatis saat pertama kali dijalankan
```
