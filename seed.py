"""
Migrate data from old Streamlit jadwal.db to new Flask jadwal_flask.db
+ create default admin user.
"""
import os
import sqlite3
import json
from datetime import datetime, timezone

import pandas as pd

from app import create_app, db as new_db
from app.models import (
    Guru, Kelas, Mapel, BebanAjar, VersiJadwal, Jadwal,
    PreferensiGuru, AturanMapel, Pengaturan, User,
)

OLD_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jadwal.db")


def old_conn():
    conn = sqlite3.connect(OLD_DB)
    conn.row_factory = sqlite3.Row
    return conn


def migrate():
    # Bersihkan SQLite DB lama (kalau ada)
    old_flask_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jadwal_flask.db")
    if os.path.exists(old_flask_db):
        os.remove(old_flask_db)

    app = create_app()
    with app.app_context():
        new_db.drop_all()
        new_db.create_all()

        conn = old_conn()

        # --- Guru ---
        rows = conn.execute("SELECT id, nama FROM guru ORDER BY id").fetchall()
        guru_map = {}
        for r in rows:
            g = Guru(id=r["id"], nama=r["nama"])
            new_db.session.add(g)
            guru_map[r["id"]] = g
        new_db.session.commit()

        # --- Kelas ---
        rows = conn.execute("SELECT id, jurusan, tingkat, nama_kelas FROM kelas ORDER BY id").fetchall()
        kelas_map = {}
        for r in rows:
            k = Kelas(id=r["id"], jurusan=r["jurusan"], tingkat=r["tingkat"], nama_kelas=r["nama_kelas"])
            new_db.session.add(k)
            kelas_map[r["id"]] = k
        new_db.session.commit()

        # --- Mapel ---
        rows = conn.execute("SELECT id, kode, nama_mapel, guru_id FROM mapel ORDER BY id").fetchall()
        mapel_map = {}
        for r in rows:
            gid = r["guru_id"]
            m = Mapel(id=r["id"], kode=r["kode"],
                       nama_mapel=r["nama_mapel"],
                       guru_id=gid if gid else None)
            new_db.session.add(m)
            mapel_map[r["id"]] = m
        new_db.session.commit()

        # --- AturanMapel ---
        rows = conn.execute("SELECT id, mapel_id, pagi_saja, max_jam_ke FROM aturan_mapel").fetchall()
        for r in rows:
            a = AturanMapel(id=r["id"], mapel_id=r["mapel_id"],
                            pagi_saja=bool(r["pagi_saja"]),
                            max_jam_ke=r["max_jam_ke"])
            new_db.session.add(a)
        new_db.session.commit()

        # --- PreferensiGuru ---
        rows = conn.execute("SELECT id, guru_id, preferensi_hari, preferensi_waktu, bobot FROM preferensi_guru").fetchall()
        for r in rows:
            p = PreferensiGuru(id=r["id"], guru_id=r["guru_id"],
                               preferensi_hari=r["preferensi_hari"],
                               preferensi_waktu=r["preferensi_waktu"],
                               bobot=r["bobot"] or 5)
            new_db.session.add(p)
        new_db.session.commit()

        # --- BebanAjar ---
        rows = conn.execute("SELECT id, mapel_id, kelas_id, jam_per_minggu FROM beban_ajar ORDER BY id").fetchall()
        for r in rows:
            ba = BebanAjar(id=r["id"], mapel_id=r["mapel_id"],
                           kelas_id=r["kelas_id"],
                           jam_per_minggu=r["jam_per_minggu"])
            new_db.session.add(ba)
        new_db.session.commit()

        # --- Pengaturan ---
        default_settings = {
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
        for key, default_val in default_settings.items():
            r = conn.execute("SELECT value FROM pengaturan WHERE key=?", (key,)).fetchone()
            val = r["value"] if r else default_val
            p = Pengaturan(key=key, value=val)
            new_db.session.add(p)
        new_db.session.commit()

        # --- VersiJadwal ---
        try:
            rows = conn.execute("SELECT id, nama, dibuat, total_slot, unplaced_slot FROM versi_jadwal ORDER BY id").fetchall()
        except sqlite3.OperationalError:
            rows = []
        versi_map = {}
        for r in rows:
            dibuat = r["dibuat"]
            if isinstance(dibuat, str):
                dibuat = datetime.fromisoformat(dibuat)
            v = VersiJadwal(id=r["id"], nama=r["nama"],
                            dibuat=dibuat,
                            total_slot=r["total_slot"] or 0,
                            unplaced_slot=r["unplaced_slot"] or 0)
            new_db.session.add(v)
            versi_map[r["id"]] = v
        new_db.session.commit()

        # --- Jadwal ---
        if versi_map:
            for vid in versi_map:
                jrows = conn.execute(
                    "SELECT kelas_id, mapel_id, hari, jam_ke FROM jadwal WHERE versi_id=?",
                    (vid,)
                ).fetchall()
                for r in jrows:
                    j = Jadwal(kelas_id=r["kelas_id"], mapel_id=r["mapel_id"],
                               hari=r["hari"], jam_ke=r["jam_ke"], versi_id=vid)
                    new_db.session.add(j)
            new_db.session.commit()

        # --- Default User ---
        if not User.query.filter_by(username="admin").first():
            u = User(username="admin", role="admin")
            u.set_password("admin123")
            new_db.session.add(u)
            new_db.session.commit()

        conn.close()

        print("Migrasi selesai!")
        print(f"  Guru : {Guru.query.count()}")
        print(f"  Kelas: {Kelas.query.count()}")
        print(f"  Mapel: {Mapel.query.count()}")
        print(f"  Beban: {BebanAjar.query.count()}")
        print(f"  Versi : {VersiJadwal.query.count()}")
        print(f"  Users: {User.query.count()}")
        print(f"  Admin login: admin / admin123")


if __name__ == "__main__":
    migrate()
