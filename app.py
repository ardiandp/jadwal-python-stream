"""
app.py
Aplikasi Penjadwal Sekolah (Guru, Mapel, Kelas, Beban Ajar, Generate Jadwal).

Jalankan dengan:
    streamlit run app.py
"""

import io
import json
import pandas as pd
import streamlit as st

import db
import scheduler

st.set_page_config(page_title="Aplikasi Penjadwal Sekolah", page_icon="🗓️", layout="wide")

db.init_db()

HARI_OPSI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"]


# ---------------------------------------------------------------------------
# Sidebar navigasi
# ---------------------------------------------------------------------------

st.sidebar.title("🗓️ Penjadwal Sekolah")
page = st.sidebar.radio(
    "Menu",
    [
        "🏠 Dashboard",
        "👨‍🏫 Data Guru",
        "🎯 Preferensi Guru",
        "📘 Data Mapel & Penugasan",
        "🏫 Data Kelas",
        "📊 Beban Ajar (Jam/Minggu)",
        "⚙️ Pengaturan Jadwal",
        "🚀 Generate Jadwal",
        "📅 Lihat Jadwal",
    ],
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Data disimpan lokal di `jadwal.db` (SQLite). Semua data awal adalah "
    "**data dummy** contoh — silakan diedit sesuai kebutuhan sekolah Anda."
)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

def page_dashboard():
    st.title("🏠 Dashboard")
    st.write("Ringkasan data yang tersimpan saat ini.")

    guru_df = db.get_guru_df()
    kelas_df = db.get_kelas_df()
    mapel_df = db.get_mapel_df()
    beban_df = db.get_beban_ajar_pivot()
    jadwal_df = db.get_jadwal_df()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Jumlah Guru", len(guru_df))
    c2.metric("Jumlah Kelas", len(kelas_df))
    c3.metric("Jumlah Penugasan Mapel", len(mapel_df))
    c4.metric("Slot Jadwal Terbentuk", len(jadwal_df))

    st.markdown("### Rekap Total Beban Ajar per Guru (jam/minggu)")
    if not mapel_df.empty:
        req = pd.DataFrame(db.get_beban_ajar_requirements())
        if not req.empty:
            rekap = (
                req.groupby("guru_nama")["jam_per_minggu"]
                .sum()
                .reset_index()
                .rename(columns={"guru_nama": "Guru", "jam_per_minggu": "Total Jam/Minggu"})
                .sort_values("Total Jam/Minggu", ascending=False)
            )
            st.dataframe(rekap, use_container_width=True, hide_index=True)
        else:
            st.info("Belum ada beban ajar yang diisi.")
    else:
        st.info("Belum ada data mapel.")

    if jadwal_df.empty:
        st.warning("Jadwal belum dibuat. Buka menu **Generate Jadwal** untuk membentuknya.")
    else:
        st.success("Jadwal sudah terbentuk. Buka menu **Lihat Jadwal** untuk melihat detailnya.")


# ---------------------------------------------------------------------------
# CRUD: Guru
# ---------------------------------------------------------------------------

def page_guru():
    st.title("👨‍🏫 Data Guru")
    st.write(
        "Tambah baris kosong untuk guru baru, edit nama langsung di tabel, "
        "atau hapus baris (klik ikon 🗑️ di kiri baris) lalu klik **Simpan Perubahan**."
    )

    df = db.get_guru_df()
    edited = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", disabled=True),
            "nama": st.column_config.TextColumn("Nama Guru", required=True),
        },
        key="editor_guru",
    )

    if st.button("💾 Simpan Perubahan", key="save_guru"):
        db.save_guru_df(edited)
        st.success("Data guru berhasil disimpan.")
        st.rerun()


# ---------------------------------------------------------------------------
# Preferensi Guru
# ---------------------------------------------------------------------------

def page_preferensi_guru():
    st.title("🎯 Preferensi Guru")
    st.write(
        "Atur preferensi hari dan waktu mengajar untuk setiap guru. "
        "Preferensi ini akan digunakan oleh mesin penjadwalan untuk menyusun "
        "jadwal yang lebih sesuai dengan keinginan guru."
    )
    st.info(
        "**Preferensi Hari**: tulis hari yang diinginkan, pisahkan dengan koma "
        "(contoh: Senin,Rabu). Kosongkan jika tidak ada preferensi hari.\n\n"
        "**Preferensi Waktu**: pilih 'Pagi' (jam ke-1 s/d pertengahan) atau "
        "'Siang' (setelah pertengahan).\n\n"
        "**Bobot**: seberapa penting preferensi ini (1-10). Semakin besar "
        "semakin diprioritaskan oleh mesin."
    )

    guru_all = db.get_guru_df()
    pref_df = db.get_preferensi_guru_df()

    # Gabung semua guru dengan preferensi
    merged = guru_all.merge(pref_df, on="guru_id", how="left", suffixes=("", "_pref"))
    merged["id"] = merged["id_pref"].fillna(0).astype("Int64")
    merged["preferensi_hari"] = merged["preferensi_hari"].fillna("")
    merged["preferensi_waktu"] = merged["preferensi_waktu"].fillna("")
    merged["bobot"] = merged["bobot"].fillna(5).astype(int)

    display = merged[["id", "guru_id", "nama", "preferensi_hari", "preferensi_waktu", "bobot"]].copy()
    display.columns = ["id", "guru_id", "Nama Guru", "Hari Preferensi", "Waktu", "Bobot"]

    edited = st.data_editor(
        display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", disabled=True),
            "guru_id": st.column_config.NumberColumn("Guru ID", disabled=True),
            "Nama Guru": st.column_config.TextColumn("Nama Guru", disabled=True),
            "Hari Preferensi": st.column_config.TextColumn(
                "Hari Preferensi",
                help="Pisahkan dengan koma. Contoh: Senin,Rabu",
            ),
            "Waktu": st.column_config.SelectboxColumn(
                "Waktu",
                options=["", "pagi", "siang"],
                help="Pagi = jam awal, Siang = jam akhir",
            ),
            "Bobot": st.column_config.NumberColumn(
                "Bobot", min_value=1, max_value=10, step=1,
                help="Semakin besar, semakin diprioritaskan",
            ),
        },
        key="editor_preferensi_guru",
    )

    if st.button("💾 Simpan Preferensi Guru", key="save_preferensi_guru"):
        # Rename back to db column names
        to_save = edited.rename(columns={
            "Nama Guru": "guru",
            "Hari Preferensi": "preferensi_hari",
            "Waktu": "preferensi_waktu",
        })
        to_save["guru_id"] = to_save["guru_id"].astype("Int64")
        db.save_preferensi_guru_df(to_save)
        st.success("Preferensi guru berhasil disimpan.")
        st.rerun()


# ---------------------------------------------------------------------------
# CRUD: Kelas
# ---------------------------------------------------------------------------

def page_kelas():
    st.title("🏫 Data Kelas")
    st.write(
        "Kelas biasanya berformat `Jurusan + Tingkat`, contoh: TKJ, X, "
        "menghasilkan nama kelas `TKJ X`. Untuk rombel paralel (mis. XII-1, XII-2) "
        "tulis langsung pada kolom **Nama Kelas**."
    )

    df = db.get_kelas_df()
    edited = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", disabled=True),
            "jurusan": st.column_config.TextColumn("Jurusan", required=True),
            "tingkat": st.column_config.TextColumn("Tingkat", required=True),
            "nama_kelas": st.column_config.TextColumn("Nama Kelas (unik)", required=True),
        },
        key="editor_kelas",
    )

    if st.button("💾 Simpan Perubahan", key="save_kelas"):
        db.save_kelas_df(edited)
        st.success("Data kelas berhasil disimpan.")
        st.rerun()


# ---------------------------------------------------------------------------
# CRUD: Mapel & Penugasan Guru
# ---------------------------------------------------------------------------

def page_mapel():
    st.title("📘 Data Mapel & Penugasan Guru")
    st.write(
        "Setiap baris = satu **penugasan** (kode unik) yang menghubungkan "
        "seorang guru dengan satu mata pelajaran. Satu guru boleh punya "
        "beberapa kode/baris jika mengajar lebih dari satu mapel "
        "(contoh: guru yang sama mengajar Baca Tulis Al-Qur'an dan "
        "Pendidikan Agama dengan kode berbeda)."
    )

    st.info(
        "**Aturan Khusus**: centang **Pagi Saja** jika mapel ini hanya boleh "
        "dijadwalkan di jam awal (misal PJOK). Tentukan **Maks Jam Ke** "
        "sebagai batas akhir jam pelajaran."
    )

    guru_list = db.get_all_guru_names()
    max_jam = int(db.get_setting("jam_per_hari", "8"))
    df = db.get_mapel_df()

    edited = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", disabled=True),
            "kode": st.column_config.TextColumn("Kode (unik)", required=True),
            "nama_mapel": st.column_config.TextColumn("Mata Pelajaran", required=True),
            "guru": st.column_config.SelectboxColumn("Guru Pengampu", options=guru_list),
            "pagi_saja": st.column_config.CheckboxColumn(
                "Pagi Saja",
                help=f"Centang jika mapel hanya boleh di jam 1-{max_jam}",
            ),
            "max_jam_ke": st.column_config.NumberColumn(
                "Maks Jam Ke",
                min_value=1,
                max_value=max_jam,
                step=1,
                format="%d",
                help="Batas jam terakhir (misal 4 = boleh jam 1 s/d 4)",
            ),
        },
        key="editor_mapel",
    )

    if st.button("💾 Simpan Perubahan", key="save_mapel"):
        db.save_mapel_df(edited)
        st.success("Data mapel & penugasan berhasil disimpan.")
        st.rerun()


# ---------------------------------------------------------------------------
# CRUD: Beban Ajar (matriks mapel x kelas)
# ---------------------------------------------------------------------------

def page_beban_ajar():
    st.title("📊 Beban Ajar (Jam per Minggu)")
    st.write(
        "Matriks ini persis seperti rekap **Beban Ajar Mata Pelajaran** pada "
        "gambar contoh: baris = penugasan (kode - mapel), kolom = kelas, "
        "isi sel = jumlah jam/minggu. Isi `0` atau kosongkan jika mapel "
        "tersebut tidak diajarkan di kelas itu."
    )

    pivot = db.get_beban_ajar_pivot()
    if pivot.empty or pivot.shape[1] <= 1:
        st.info("Tambahkan data Guru, Mapel, dan Kelas terlebih dahulu.")
        return

    kelas_cols = [c for c in pivot.columns if c != "Mapel"]
    col_config = {"Mapel": st.column_config.TextColumn("Mapel", disabled=True)}
    for c in kelas_cols:
        col_config[c] = st.column_config.NumberColumn(c, min_value=0, step=1)

    edited = st.data_editor(
        pivot,
        use_container_width=True,
        hide_index=True,
        column_config=col_config,
        key="editor_beban_ajar",
    )

    colA, colB = st.columns([1, 3])
    with colA:
        if st.button("💾 Simpan Perubahan", key="save_beban"):
            db.save_beban_ajar_pivot(edited)
            st.success("Beban ajar berhasil disimpan.")
            st.rerun()

    st.markdown("### Total Jam per Kelas")
    totals = edited[kelas_cols].sum(numeric_only=True)
    st.dataframe(
        totals.reset_index().rename(columns={"index": "Kelas", 0: "Total Jam/Minggu"}),
        use_container_width=True,
        hide_index=True,
    )


# ---------------------------------------------------------------------------
# Pengaturan jadwal (hari aktif, jam per hari, ukuran blok)
# ---------------------------------------------------------------------------

def page_pengaturan():
    st.title("⚙️ Pengaturan Jadwal")

    hari_aktif_saved = db.get_setting("hari_aktif", "Senin,Selasa,Rabu,Kamis,Jumat").split(",")
    jam_per_hari_saved = int(db.get_setting("jam_per_hari", "8"))
    max_blok_saved = int(db.get_setting("max_blok", "2"))

    waktu_mulai = db.get_setting("waktu_mulai", "07:00")
    durasi_jam = int(db.get_setting("durasi_jam", "35"))
    durasi_aktivitas_khusus = int(db.get_setting("durasi_aktivitas_khusus", "35"))
    nama_sekolah = db.get_setting("nama_sekolah", "SD NEGERI .....")
    tahun_pelajaran = db.get_setting("tahun_pelajaran", "2025/2026")

    istirahat_raw = db.get_setting("istirahat", '[{"setelah":3,"durasi":30},{"setelah":6,"durasi":35}]')
    try:
        istirahat = json.loads(istirahat_raw)
    except Exception:
        istirahat = [{"setelah": 3, "durasi": 30}, {"setelah": 6, "durasi": 35}]

    aktivitas_khusus_raw = db.get_setting("aktivitas_khusus", "{}")
    try:
        aktivitas_khusus = json.loads(aktivitas_khusus_raw)
    except Exception:
        aktivitas_khusus = {}

    with st.expander("Pengaturan Dasar", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            hari_aktif = st.multiselect(
                "Hari Aktif Sekolah", HARI_OPSI, default=[h for h in hari_aktif_saved if h in HARI_OPSI]
            )
            jam_per_hari = st.number_input(
                "Jumlah Jam Pelajaran per Hari", min_value=1, max_value=15, value=jam_per_hari_saved
            )
            max_blok = st.number_input(
                "Maksimal Jam Berurutan per Mapel dalam 1 Hari (blok)",
                min_value=1, max_value=6, value=max_blok_saved,
                help="Contoh: jika 4 jam/minggu dan blok=2, maka akan dipecah jadi 2 hari x 2 jam.",
            )
        with c2:
            nama_sekolah = st.text_input("Nama Sekolah", value=nama_sekolah)
            tahun_pelajaran = st.text_input("Tahun Pelajaran", value=tahun_pelajaran)

    with st.expander("Pengaturan Waktu", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            waktu_mulai = st.text_input(
                "Waktu Mulai Jam Pertama", value=waktu_mulai,
                help="Format HH:MM, contoh 07:00",
            )
        with c2:
            durasi_jam = st.number_input(
                "Durasi per Jam Pelajaran (menit)", min_value=15, max_value=60,
                value=durasi_jam, step=5,
            )
        with c3:
            durasi_aktivitas_khusus = st.number_input(
                "Durasi Aktivitas Khusus (menit)", min_value=5, max_value=60,
                value=durasi_aktivitas_khusus, step=5,
                help="Durasi untuk upacara/literasi/senam dll di jam pertama",
            )

        st.markdown("#### Istirahat")
        ist1_aktif = st.checkbox("Istirahat 1", value=len(istirahat) > 0)
        if ist1_aktif:
            ic1, ic2 = st.columns(2)
            with ic1:
                ist1_setelah = st.number_input(
                    "Setelah jam ke-", min_value=1, max_value=jam_per_hari,
                    value=istirahat[0]["setelah"] if len(istirahat) > 0 else 3,
                    key="ist1_setelah",
                )
            with ic2:
                ist1_durasi = st.number_input(
                    "Durasi (menit)", min_value=5, max_value=60,
                    value=istirahat[0]["durasi"] if len(istirahat) > 0 else 30,
                    step=5, key="ist1_durasi",
                )

        ist2_aktif = st.checkbox("Istirahat 2", value=len(istirahat) > 1)
        if ist2_aktif:
            ic1, ic2 = st.columns(2)
            with ic1:
                ist2_setelah = st.number_input(
                    "Setelah jam ke-", min_value=1, max_value=jam_per_hari,
                    value=istirahat[1]["setelah"] if len(istirahat) > 1 else 6,
                    key="ist2_setelah",
                )
            with ic2:
                ist2_durasi = st.number_input(
                    "Durasi (menit)", min_value=5, max_value=60,
                    value=istirahat[1]["durasi"] if len(istirahat) > 1 else 35,
                    step=5, key="ist2_durasi",
                )

    with st.expander("Aktivitas Khusus Jam Pertama", expanded=True):
        st.write(
            "Aktivitas yang ditampilkan di jam pertama setiap hari "
            "(misal Upacara, Literasi, Senam). Kosongkan jika tidak ada."
        )
        aktivitas_baru = {}
        for hari in HARI_OPSI:
            val = aktivitas_khusus.get(hari, "")
            aktivitas_baru[hari] = st.text_input(f"{hari}", value=val, key=f"akt_{hari}")

    if st.button("💾 Simpan Semua Pengaturan"):
        if not hari_aktif:
            st.error("Pilih minimal satu hari aktif.")
        else:
            db.set_setting("hari_aktif", ",".join(hari_aktif))
            db.set_setting("jam_per_hari", str(jam_per_hari))
            db.set_setting("max_blok", str(max_blok))
            db.set_setting("waktu_mulai", waktu_mulai)
            db.set_setting("durasi_jam", str(durasi_jam))
            db.set_setting("durasi_aktivitas_khusus", str(durasi_aktivitas_khusus))
            db.set_setting("nama_sekolah", nama_sekolah)
            db.set_setting("tahun_pelajaran", tahun_pelajaran)

            ist_list = []
            if ist1_aktif:
                ist_list.append({"setelah": ist1_setelah, "durasi": ist1_durasi})
            if ist2_aktif:
                ist_list.append({"setelah": ist2_setelah, "durasi": ist2_durasi})
            db.set_setting("istirahat", json.dumps(ist_list))

            akt_clean = {k: v for k, v in aktivitas_baru.items() if v.strip()}
            db.set_setting("aktivitas_khusus", json.dumps(akt_clean))
            st.success("Semua pengaturan berhasil disimpan.")


# ---------------------------------------------------------------------------
# Verifikasi data pra-generate
# ---------------------------------------------------------------------------

def _verifikasi_data(hari_aktif, jam_per_hari):
    v = db.get_verification_data()
    kapasitas = len(hari_aktif) * jam_per_hari

    errors = []
    warnings = []
    info_items = []

    # ERROR: Mapel tanpa guru
    if v["mapel_tanpa_guru"]:
        items = [f"{m['kode']} - {m['nama_mapel']}" for m in v["mapel_tanpa_guru"]]
        errors.append({
            "label": "Mapel tanpa guru pengampu",
            "items": items,
            "rekomendasi": "Tambahkan guru pengampu di menu **📘 Data Mapel & Penugasan**",
        })

    # ERROR: Kelas tanpa beban ajar
    if v["kelas_tanpa_beban"]:
        errors.append({
            "label": "Kelas tanpa beban ajar",
            "items": v["kelas_tanpa_beban"],
            "rekomendasi": "Atur jam pelajaran untuk kelas ini di menu **📊 Beban Ajar**",
        })

    # ERROR: Duplikat kode mapel
    if v["duplikat_kode"]:
        errors.append({
            "label": "Kode mapel duplikat",
            "items": v["duplikat_kode"],
            "rekomendasi": "Ubah kode mapel duplikat di menu **📘 Data Mapel & Penugasan**",
        })

    # ERROR: Duplikat nama kelas
    if v["duplikat_kelas"]:
        errors.append({
            "label": "Nama kelas duplikat",
            "items": v["duplikat_kelas"],
            "rekomendasi": "Ubah nama kelas duplikat di menu **🏫 Data Kelas**",
        })

    # WARNING: Mapel tanpa beban ajar
    if v["mapel_tanpa_beban"]:
        items = [f"{m['kode']} - {m['nama_mapel']}" for m in v["mapel_tanpa_beban"]]
        warnings.append({
            "label": "Mapel tidak memiliki beban ajar (tidak masuk jadwal)",
            "items": items,
            "rekomendasi": "Atur jam pelajaran untuk mapel ini di menu **📊 Beban Ajar**",
        })

    # WARNING: Total JP per kelas tidak sesuai kapasitas
    for nama_kelas, jp in sorted(v["total_jp_per_kelas"].items()):
        selisih = kapasitas - jp
        if selisih > 0:
            warnings.append({
                "label": f"Kelas {nama_kelas}: JP {jp} dari {kapasitas} (kurang {selisih} slot)",
                "items": [],
                "rekomendasi": "Tambah jam pelajaran di **📊 Beban Ajar** atau kurangi jumlah hari aktif di **⚙️ Pengaturan Jadwal**",
            })
        elif selisih < 0:
            warnings.append({
                "label": f"Kelas {nama_kelas}: JP {jp} dari {kapasitas} (kelebihan {abs(selisih)} slot)",
                "items": [],
                "rekomendasi": "Kurangi jam pelajaran di **📊 Beban Ajar** atau tambah jumlah hari aktif di **⚙️ Pengaturan Jadwal**",
            })

    # INFO: Ringkasan
    info_items.append(f"🧑‍🏫 {v['jumlah_guru']} guru")
    info_items.append(f"📚 {v['jumlah_mapel']} mapel")
    info_items.append(f"🏫 {v['jumlah_kelas']} kelas")
    total_jam = sum(v["total_jp_per_kelas"].values())
    info_items.append(f"📊 Total JP: {total_jam} | Kapasitas: {v['jumlah_kelas'] * kapasitas} slot")

    # INFO: Beban guru
    guru_beban = []
    for guru, jam in sorted(v["total_jam_per_guru"].items()):
        guru_beban.append(f"{guru}: {jam} JP/minggu")
    if guru_beban:
        info_items.append(f"📋 Beban guru: {' | '.join(guru_beban)}")

    return {
        "errors": errors,
        "warnings": warnings,
        "info": info_items,
        "siap": len(errors) == 0,
        "kapasitas": kapasitas,
    }


# ---------------------------------------------------------------------------
# Generate Jadwal
# ---------------------------------------------------------------------------

def page_generate():
    st.title("🚀 Generate Jadwal")

    hari_aktif = db.get_setting("hari_aktif", "Senin,Selasa,Rabu,Kamis,Jumat").split(",")
    jam_per_hari = int(db.get_setting("jam_per_hari", "8"))
    max_blok = int(db.get_setting("max_blok", "2"))

    st.write(
        f"Pengaturan aktif: **{', '.join(hari_aktif)}**, "
        f"**{jam_per_hari} jam/hari**, blok maksimal **{max_blok} jam berurutan**. "
        "Ubah di menu **Pengaturan Jadwal** jika perlu."
    )

    requirements = db.get_beban_ajar_requirements()
    total_jam = sum(r["jam_per_minggu"] for r in requirements) if requirements else 0
    st.write(f"Total kebutuhan jam yang akan dijadwalkan: **{total_jam} jam** "
             f"dari **{len(requirements)}** baris beban ajar.")

    c1, c2 = st.columns(2)
    with c1:
        max_attempts = st.slider(
            "Percobaan per versi (semakin besar semakin optimal, tapi lebih lambat)",
            min_value=20, max_value=1000, value=300, step=20,
        )
    with c2:
        num_versions = st.slider(
            "Jumlah versi yang akan digenerate",
            min_value=1, max_value=10, value=3,
            help="Beberapa versi akan digenerate dan bisa dibandingkan. "
                 "Pilih versi terbaik di menu Lihat Jadwal.",
        )

    versi_sekarang = db.get_versi_list()
    if not versi_sekarang.empty:
        with st.expander("Versi yang sudah ada"):
            st.dataframe(
                versi_sekarang[["nama", "total_slot", "unplaced_slot", "dibuat"]]
                .rename(columns={"nama": "Versi", "total_slot": "Slot Terisi",
                                 "unplaced_slot": "Gagal", "dibuat": "Dibuat"}),
                use_container_width=True, hide_index=True,
            )
            hapus = st.selectbox("Hapus versi", [""] + versi_sekarang["nama"].tolist())
            if hapus and st.button("🗑️ Hapus Versi"):
                row = versi_sekarang[versi_sekarang["nama"] == hapus].iloc[0]
                db.delete_versi(int(row["id"]))
                st.success(f"Versi '{hapus}' berhasil dihapus.")
                st.rerun()

    # Load preferensi & aturan untuk scheduler
    preferensi_guru = db.get_preferensi_guru_dict()
    aturan_mapel = db.get_aturan_mapel_dict()

    if preferensi_guru:
        n_pref = len(preferensi_guru)
        st.caption(f"📋 {n_pref} guru memiliki preferensi yang akan dioptimalkan.")
    if aturan_mapel:
        n_aturan = sum(1 for r in aturan_mapel.values() if r.get("pagi_saja"))
        if n_aturan:
            st.caption(f"🔒 {n_aturan} mapel memiliki aturan khusus (pagi saja).")

    # Verifikasi data
    verifikasi = _verifikasi_data(hari_aktif, jam_per_hari)
    punya_masalah = len(verifikasi["errors"]) > 0 or len(verifikasi["warnings"]) > 0

    with st.expander("📋 Verifikasi Data", expanded=punya_masalah):
        if not punya_masalah:
            st.success("✅ Semua data lengkap dan siap generate!")

        if verifikasi["errors"]:
            for e in verifikasi["errors"]:
                detail = ", ".join(e["items"]) if e["items"] else ""
                st.error(f"**{e['label']}**" + (f": {detail}" if detail else ""))
                if e.get("rekomendasi"):
                    st.caption(f"💡 **Rekomendasi:** {e['rekomendasi']}")

        if verifikasi["warnings"]:
            for w in verifikasi["warnings"]:
                detail = ", ".join(w["items"]) if w["items"] else ""
                st.warning(f"**{w['label']}**" + (f": {detail}" if detail else ""))
                if w.get("rekomendasi"):
                    st.caption(f"💡 **Rekomendasi:** {w['rekomendasi']}")

        if verifikasi["info"]:
            for item in verifikasi["info"]:
                st.caption(item)

    can_generate = verifikasi["siap"]
    force_generate = False
    if not can_generate:
        col1, col2 = st.columns([1, 4])
        with col1:
            force_generate = st.checkbox(
                "Generate tetap berjalan",
                help="Lewati error dan tetap generate. Hasil mungkin tidak maksimal.",
            )
        if force_generate:
            can_generate = True

    if "generate_clicked" not in st.session_state:
        st.session_state.generate_clicked = False

    if st.button(
        "🚀 Generate / Regenerate Jadwal",
        type="primary",
        disabled=not can_generate,
    ):
        if not requirements:
            st.error("Belum ada beban ajar. Isi dulu di menu **Beban Ajar**.")
            return

        st.session_state.generate_clicked = True

    if st.session_state.generate_clicked and can_generate:
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i in range(num_versions):
            status_text.text(f"Menyusun jadwal versi {i+1} dari {num_versions}...")
            assigned, unplaced = scheduler.generate_jadwal(
                requirements, hari_aktif, jam_per_hari,
                max_blok=max_blok, max_attempts=max_attempts,
                preferensi_guru=preferensi_guru,
                aturan_mapel=aturan_mapel,
            )
            versi_id = db.create_versi(f"Versi {i+1}", len(assigned), len(unplaced))
            if assigned:
                db.save_jadwal(assigned, versi_id)
            results.append({
                "versi_id": versi_id,
                "Versi": f"Versi {i+1}",
                "Slot Terisi": len(assigned),
                "Gagal": len(unplaced),
                "Status": "✅ Optimal" if not unplaced else "⚠️ Sebagian",
            })
            progress_bar.progress((i + 1) / num_versions)

        st.session_state.generate_clicked = False
        status_text.text("")
        progress_bar.empty()

        st.markdown("### Hasil Generate")
        results_df = pd.DataFrame(results)
        best_idx = int(results_df["Gagal"].idxmin())

        st.dataframe(
            results_df[["Versi", "Slot Terisi", "Gagal", "Status"]],
            use_container_width=True, hide_index=True,
        )

        if results_df.loc[best_idx, "Gagal"] == 0:
            st.success(
                f"✅ **{results_df.loc[best_idx, 'Versi']}** — semua slot terisi penuh tanpa bentrok!"
            )
        else:
            st.warning(
                f"⚠️ **{results_df.loc[best_idx, 'Versi']}** adalah yang terbaik, "
                f"namun masih ada {results_df.loc[best_idx, 'Gagal']} blok yang gagal ditempatkan."
            )
            with st.expander("Lihat detail blok yang gagal"):
                unplaced_detail = []
                for u in unplaced:
                    unplaced_detail.append({
                        "Kelas": u.get("kelas_nama", ""),
                        "Kode": u.get("kode", ""),
                        "Mapel": u.get("nama_mapel", ""),
                        "Guru": u.get("guru_nama", ""),
                        "Jam Gagal": u.get("blok", 0),
                    })
                st.dataframe(
                    pd.DataFrame(unplaced_detail),
                    use_container_width=True, hide_index=True,
                )

        st.info("Buka menu **Lihat Jadwal** untuk melihat & membandingkan semua versi.")


# ---------------------------------------------------------------------------
# Lihat Jadwal
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Helper: perhitungan waktu & render HTML jadwal
# ---------------------------------------------------------------------------

def _calculate_times(waktu_mulai, durasi_jam, durasi_aktivitas_khusus, istirahat_list, jam_per_hari):
    jam, menit = map(int, waktu_mulai.split(":"))
    current = jam * 60 + menit

    times = []

    times.append({
        "jam_ke": 0, "start": current, "end": current + durasi_aktivitas_khusus,
        "is_break": False, "is_special": True,
    })
    current += durasi_aktivitas_khusus

    break_after = {b["setelah"]: b["durasi"] for b in istirahat_list}

    for j in range(1, jam_per_hari + 1):
        if (j - 1) in break_after:
            d = break_after[j - 1]
            times.append({
                "jam_ke": None, "start": current, "end": current + d,
                "is_break": True, "label": "Istirahat",
            })
            current += d

        times.append({
            "jam_ke": j, "start": current, "end": current + durasi_jam,
            "is_break": False, "is_special": False,
        })
        current += durasi_jam

    return times


def _time_str(minutes):
    return f"{minutes // 60:02d}.{minutes % 60:02d}"


def _render_jadwal_html(df_kelas, nama_kelas, settings, hari_aktif, jam_per_hari, alokasi_df):
    waktu_mulai = settings["waktu_mulai"]
    durasi_jam = settings["durasi_jam"]
    durasi_aktivitas_khusus = settings["durasi_aktivitas_khusus"]
    istirahat_list = settings["istirahat"]
    aktivitas_khusus = settings["aktivitas_khusus"]
    nama_sekolah = settings["nama_sekolah"]
    tahun_pelajaran = settings["tahun_pelajaran"]

    times = _calculate_times(waktu_mulai, durasi_jam, durasi_aktivitas_khusus, istirahat_list, jam_per_hari)

    cell_map = {}
    for _, r in df_kelas.iterrows():
        guru = f" ({r['guru_nama']})" if pd.notna(r.get("guru_nama")) else ""
        cell_map[(r["hari"], r["jam_ke"])] = f"{r['kode']} - {r['nama_mapel']}{guru}"

    parts = []

    parts.append(f'<h3 style="text-align:center;margin:5px 0;font-family:Arial,sans-serif;">{nama_sekolah}</h3>')
    parts.append(f'<h3 style="text-align:center;margin:5px 0;font-family:Arial,sans-serif;">TAHUN PELAJARAN {tahun_pelajaran}</h3>')
    parts.append(f'<p style="font-weight:bold;font-size:14px;margin:5px 0;font-family:Arial,sans-serif;">KELAS {nama_kelas}</p>')

    parts.append('<div style="display:flex;gap:30px;align-items:flex-start;">')

    parts.append('<div>')
    parts.append('<table style="border-collapse:collapse;text-align:center;font-family:Arial,sans-serif;font-size:13px;">')

    # header row 1
    parts.append('<tr>')
    parts.append(f'<th rowspan="2" style="background:#4472C4;color:white;border:1px solid black;padding:4px 8px;">Jam Ke</th>')
    parts.append(f'<th rowspan="2" style="background:#4472C4;color:white;border:1px solid black;padding:4px 8px;">WAKTU</th>')
    parts.append(f'<th colspan="{len(hari_aktif)}" style="background:#4472C4;color:white;border:1px solid black;padding:4px 8px;">HARI</th>')
    parts.append('</tr>')

    # header row 2
    parts.append('<tr>')
    for h in hari_aktif:
        parts.append(f'<th style="background:#4472C4;color:white;border:1px solid black;padding:4px 8px;">{h.upper()}</th>')
    parts.append('</tr>')

    col_count = 2 + len(hari_aktif)

    for t in times:
        if t["is_break"]:
            parts.append(
                f'<tr><td colspan="{col_count}" style="background:#FFFF00;border:1px solid black;'
                f'padding:4px 8px;font-style:italic;">'
                f'{_time_str(t["start"])}-{_time_str(t["end"])}  '
                f'&nbsp;&nbsp;&nbsp;&nbsp;Istirahat</td></tr>'
            )
        elif t.get("is_special"):
            parts.append('<tr>')
            parts.append(f'<td style="border:1px solid black;padding:4px 8px;"></td>')
            parts.append(f'<td style="border:1px solid black;padding:4px 8px;">{_time_str(t["start"])}-{_time_str(t["end"])}</td>')
            for h in hari_aktif:
                activity = aktivitas_khusus.get(h, "")
                if activity:
                    parts.append(
                        f'<td style="background:#FF6B6B;color:white;border:1px solid black;padding:4px 8px;">{activity}</td>'
                    )
                else:
                    parts.append(f'<td style="border:1px solid black;padding:4px 8px;"></td>')
            parts.append('</tr>')
        else:
            parts.append('<tr>')
            parts.append(f'<td style="border:1px solid black;padding:4px 8px;">{t["jam_ke"]}</td>')
            parts.append(f'<td style="border:1px solid black;padding:4px 8px;">{_time_str(t["start"])}-{_time_str(t["end"])}</td>')
            for h in hari_aktif:
                content = cell_map.get((h, t["jam_ke"]), "")
                parts.append(f'<td style="border:1px solid black;padding:4px 8px;">{content}</td>')
            parts.append('</tr>')

    parts.append('</table>')

    parts.append('</div>')  # end schedule table wrapper

    # Alokasi Waktu
    parts.append('<div>')
    parts.append('<p style="font-weight:bold;font-size:14px;margin:0 0 5px 0;font-family:Arial,sans-serif;">Alokasi Waktu</p>')
    parts.append('<table style="border-collapse:collapse;font-family:Arial,sans-serif;font-size:13px;">')
    parts.append('<tr>')
    parts.append('<th style="background:#4472C4;color:white;border:1px solid black;padding:4px 8px;">Mata Pelajaran</th>')
    parts.append('<th style="background:#4472C4;color:white;border:1px solid black;padding:4px 8px;">Jumlah JP</th>')
    parts.append('</tr>')
    if alokasi_df is not None and not alokasi_df.empty:
        for _, r in alokasi_df.iterrows():
            parts.append(
                f'<tr><td style="border:1px solid black;padding:4px 8px;text-align:left;">{r["mapel"]}</td>'
                f'<td style="border:1px solid black;padding:4px 8px;">{int(r["jp"])} JP</td></tr>'
            )
        total_jp = int(alokasi_df["jp"].sum())
        parts.append(
            f'<tr style="font-weight:bold;"><td style="border:1px solid black;padding:4px 8px;text-align:left;">TOTAL</td>'
            f'<td style="border:1px solid black;padding:4px 8px;">{total_jp} JP</td></tr>'
        )
    parts.append('</table>')
    parts.append('</div>')  # end alokasi wrapper

    parts.append('</div>')  # end flex container

    return "".join(parts)


def _build_alokasi_df():
    req = db.get_beban_ajar_requirements()
    agg = {}
    for r in req:
        label = f"{r['kode']} - {r['nama_mapel']}"
        agg[label] = agg.get(label, 0) + r["jam_per_minggu"]
    if not agg:
        return pd.DataFrame()
    return pd.DataFrame([{"mapel": k, "jp": v} for k, v in sorted(agg.items())])


# ---------------------------------------------------------------------------
# Lihat Jadwal
# ---------------------------------------------------------------------------

def page_lihat_jadwal():
    st.title("📅 Lihat Jadwal")

    db.ensure_default_version()

    versi_df = db.get_versi_list()
    if versi_df.empty:
        st.info("Jadwal belum dibuat. Buka menu **Generate Jadwal** terlebih dahulu.")
        return

    hari_aktif = db.get_setting("hari_aktif", "Senin,Selasa,Rabu,Kamis,Jumat").split(",")
    jam_per_hari = int(db.get_setting("jam_per_hari", "8"))

    waktu_mulai = db.get_setting("waktu_mulai", "07:00")
    durasi_jam = int(db.get_setting("durasi_jam", "35"))
    durasi_aktivitas_khusus = int(db.get_setting("durasi_aktivitas_khusus", "35"))
    nama_sekolah = db.get_setting("nama_sekolah", "SD NEGERI .....")
    tahun_pelajaran = db.get_setting("tahun_pelajaran", "2025/2026")

    istirahat_raw = db.get_setting("istirahat", '[{"setelah":3,"durasi":30},{"setelah":6,"durasi":35}]')
    try:
        istirahat = json.loads(istirahat_raw)
    except Exception:
        istirahat = [{"setelah": 3, "durasi": 30}, {"setelah": 6, "durasi": 35}]

    aktivitas_khusus_raw = db.get_setting("aktivitas_khusus", "{}")
    try:
        aktivitas_khusus = json.loads(aktivitas_khusus_raw)
    except Exception:
        aktivitas_khusus = {}

    settings = {
        "waktu_mulai": waktu_mulai,
        "durasi_jam": durasi_jam,
        "durasi_aktivitas_khusus": durasi_aktivitas_khusus,
        "istirahat": istirahat,
        "aktivitas_khusus": aktivitas_khusus,
        "nama_sekolah": nama_sekolah,
        "tahun_pelajaran": tahun_pelajaran,
    }

    alokasi_df = _build_alokasi_df()

    # Versi selector
    versi_options = {
        f"{r['nama']} (terisi {r['total_slot']} slot)"
        + ("" if r["unplaced_slot"] == 0 else f" — ⚠️ {r['unplaced_slot']} gagal"):
        r["id"]
        for _, r in versi_df.iterrows()
    }
    selected_label = st.selectbox("Pilih Versi Jadwal", list(versi_options.keys()))
    selected_versi_id = versi_options[selected_label]

    df = db.get_jadwal_df(versi_id=selected_versi_id)
    if df.empty:
        st.info("Versi ini belum memiliki data jadwal.")
        return

    kelas_list = sorted(df["nama_kelas"].unique())
    kelas_pilihan = kelas_list[0]

    tab1, tab2, tab3 = st.tabs(["Per Kelas", "Per Guru", "Data Mentah"])

    with tab1:
        kelas_pilihan = st.selectbox("Pilih Kelas", kelas_list)
        df_kelas = df[df["nama_kelas"] == kelas_pilihan]

        html = _render_jadwal_html(
            df_kelas, kelas_pilihan, settings, hari_aktif, jam_per_hari, alokasi_df,
        )
        st.markdown(html, unsafe_allow_html=True)

    with tab2:
        guru_opsi = sorted([g for g in df["guru_nama"].dropna().unique()])
        guru_pilihan = st.selectbox("Pilih Guru", guru_opsi)
        df_guru = df[df["guru_nama"] == guru_pilihan]

        # Build per-guru grid as simple table
        guru_grid = pd.DataFrame(
            "", index=[f"Jam ke-{j}" for j in range(1, jam_per_hari + 1)], columns=hari_aktif
        )
        for _, r in df_guru.iterrows():
            if r["hari"] in hari_aktif:
                guru_grid.loc[f"Jam ke-{r['jam_ke']}", r["hari"]] = (
                    f"{r['kode']} - {r['nama_mapel']} ({r['nama_kelas']})"
                )
        st.dataframe(guru_grid, use_container_width=True)

    with tab3:
        st.dataframe(
            df[["nama_kelas", "kode", "nama_mapel", "guru_nama", "hari", "jam_ke"]]
            .sort_values(["nama_kelas", "hari", "jam_ke"]),
            use_container_width=True, hide_index=True,
        )

    # Export
    st.markdown("### Unduh")
    c1, c2 = st.columns(2)

    with c1:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            for kelas in sorted(df["nama_kelas"].unique()):
                dfk = df[df["nama_kelas"] == kelas]
                times = _calculate_times(
                    waktu_mulai, durasi_jam, durasi_aktivitas_khusus, istirahat, jam_per_hari,
                )
                rows = []
                for t in times:
                    if t["is_break"]:
                        row = {"Jam Ke": "", "WAKTU": f"{_time_str(t['start'])}-{_time_str(t['end'])}"}
                        for h in hari_aktif:
                            row[h] = ""
                        rows.append(row)
                    elif t.get("is_special"):
                        row = {"Jam Ke": "", "WAKTU": f"{_time_str(t['start'])}-{_time_str(t['end'])}"}
                        for h in hari_aktif:
                            row[h] = aktivitas_khusus.get(h, "")
                        rows.append(row)
                    else:
                        row = {"Jam Ke": t["jam_ke"], "WAKTU": f"{_time_str(t['start'])}-{_time_str(t['end'])}"}
                        for h in hari_aktif:
                            cell = dfk[(dfk["hari"] == h) & (dfk["jam_ke"] == t["jam_ke"])]
                            if not cell.empty:
                                rr = cell.iloc[0]
                                row[h] = f"{rr['kode']} - {rr['nama_mapel']} ({rr['guru_nama']})"
                            else:
                                row[h] = ""
                        rows.append(row)

                export_df = pd.DataFrame(rows)
                sheet_name = kelas[:31]
                export_df.to_excel(writer, sheet_name=sheet_name, index=False)

        st.download_button(
            "⬇️ Unduh Semua Kelas (.xlsx)",
            data=buf.getvalue(),
            file_name=f"jadwal_pelajaran_{tahun_pelajaran.replace('/', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    with c2:
        # HTML export for current class
        df_kelas_curr = df[df["nama_kelas"] == kelas_pilihan] if not df.empty else df
        html_curr = _render_jadwal_html(
            df_kelas_curr, kelas_pilihan, settings, hari_aktif, jam_per_hari, alokasi_df,
        )
        html_full = f"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <title>Jadwal Pelajaran - {kelas_pilihan}</title>
    <style>
        body {{ font-family: Arial, sans-serif; font-size: 13px; margin: 20px; }}
        h3 {{ text-align: center; margin: 5px 0; }}
        table {{ border-collapse: collapse; text-align: center; }}
        th, td {{ border: 1px solid black; padding: 4px 8px; }}
    </style>
</head>
<body>
{html_curr}
</body>
</html>"""
        st.download_button(
            "⬇️ Unduh HTML Kelas Ini",
            data=html_full,
            file_name=f"jadwal_{kelas_pilihan}.html",
            mime="text/html",
        )


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

if page == "🏠 Dashboard":
    page_dashboard()
elif page == "👨‍🏫 Data Guru":
    page_guru()
elif page == "🎯 Preferensi Guru":
    page_preferensi_guru()
elif page == "📘 Data Mapel & Penugasan":
    page_mapel()
elif page == "🏫 Data Kelas":
    page_kelas()
elif page == "📊 Beban Ajar (Jam/Minggu)":
    page_beban_ajar()
elif page == "⚙️ Pengaturan Jadwal":
    page_pengaturan()
elif page == "🚀 Generate Jadwal":
    page_generate()
elif page == "📅 Lihat Jadwal":
    page_lihat_jadwal()
