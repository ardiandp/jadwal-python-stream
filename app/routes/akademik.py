import json
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Guru, Kelas, Mapel, BebanAjar, PreferensiGuru, AturanMapel, Pengaturan
from app.routes.auth import admin_required

akademik_bp = Blueprint("akademik", __name__, url_prefix="/akademik")


# --- BEBAN AJAR (JS Grid) ---
@akademik_bp.route("/beban-ajar", methods=["GET", "POST"])
@login_required
def beban_ajar():
    if request.method == "POST" and current_user.role == "admin":
        data = request.get_json(force=True) if request.is_json else request.form
        try:
            # data = { "kelas_id": { "mapel_id": jam_per_minggu }, ... }
            BebanAjar.query.delete()
            for kelas_id_str, mapels in data.items():
                kelas_id = int(kelas_id_str)
                for mapel_id_str, jam in mapels.items():
                    jam_int = int(jam) if jam else 0
                    if jam_int > 0:
                        db.session.add(BebanAjar(
                            mapel_id=int(mapel_id_str),
                            kelas_id=kelas_id,
                            jam_per_minggu=jam_int,
                        ))
            db.session.commit()
            return jsonify({"status": "ok", "message": "Beban ajar disimpan."})
        except Exception as e:
            db.session.rollback()
            return jsonify({"status": "error", "message": str(e)}), 400

    mapel_list = Mapel.query.order_by(Mapel.kode).all()
    kelas_list = Kelas.query.order_by(Kelas.nama_kelas).all()
    beban_list = BebanAjar.query.all()
    beban_map = {}
    for b in beban_list:
        beban_map[(b.mapel_id, b.kelas_id)] = b.jam_per_minggu

    return render_template("akademik/beban_ajar.html",
                           mapel_list=mapel_list,
                           kelas_list=kelas_list,
                           beban_map=beban_map,
                           active_menu="beban")


# --- PREFERENSI GURU ---
@akademik_bp.route("/preferensi", methods=["GET", "POST"])
@login_required
def preferensi():
    if request.method == "POST" and current_user.role == "admin":
        data = request.form
        try:
            # Update existing
            for key, val in data.items():
                if key.startswith("hari_"):
                    pid = int(key.replace("hari_", ""))
                    p = db.session.get(PreferensiGuru, pid)
                    if p:
                        p.preferensi_hari = val.strip() or None
                        p.preferensi_waktu = data.get(f"waktu_{pid}", "").strip() or None
                        bobot_str = data.get(f"bobot_{pid}", "").strip()
                        p.bobot = int(bobot_str) if bobot_str else 5
            db.session.commit()
            flash("Preferensi guru disimpan.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error: {e}", "danger")
        return redirect(url_for("akademik.preferensi"))

    guru_list = Guru.query.order_by(Guru.nama).all()
    preferensi_list = PreferensiGuru.query.all()
    pref_map = {p.guru_id: p for p in preferensi_list}
    return render_template("akademik/preferensi.html",
                           guru_list=guru_list,
                           pref_map=pref_map,
                           active_menu="preferensi")


# --- PENGATURAN ---
@akademik_bp.route("/pengaturan", methods=["GET", "POST"])
@login_required
def pengaturan():
    if request.method == "POST" and current_user.role == "admin":
        data = request.form
        try:
            settings = {}
            settings["nama_sekolah"] = data.get("nama_sekolah", "").strip()
            settings["tahun_pelajaran"] = data.get("tahun_pelajaran", "").strip()
            settings["hari_aktif"] = ",".join(data.getlist("hari_aktif")) if "hari_aktif" in data else ""
            settings["jam_per_hari"] = data.get("jam_per_hari", "8")
            settings["max_blok"] = data.get("max_blok", "2")
            settings["waktu_mulai"] = data.get("waktu_mulai", "07:00")
            settings["durasi_jam"] = data.get("durasi_jam", "35")
            settings["durasi_aktivitas_khusus"] = data.get("durasi_aktivitas_khusus", "35")

            istirahat = []
            for i in range(1, 3):
                setelah = data.get(f"istirahat_setelah_{i}", "").strip()
                durasi = data.get(f"istirahat_durasi_{i}", "").strip()
                if setelah and durasi:
                    istirahat.append({"setelah": int(setelah), "durasi": int(durasi)})
            settings["istirahat"] = json.dumps(istirahat)

            aktivitas = {}
            for hari in ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"]:
                aktivitas[hari] = data.get(f"aktivitas_{hari}", "").strip()
            settings["aktivitas_khusus"] = json.dumps(aktivitas)

            for key, value in settings.items():
                p = Pengaturan.query.get(key)
                if p:
                    p.value = value
                else:
                    db.session.add(Pengaturan(key=key, value=value))
            db.session.commit()
            flash("Pengaturan disimpan.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error: {e}", "danger")
        return redirect(url_for("akademik.pengaturan"))

    def gs(key, default=""):
        p = db.session.get(Pengaturan, key)
        return p.value if p else default

    settings = {
        "nama_sekolah": gs("nama_sekolah", "SD NEGERI ....."),
        "tahun_pelajaran": gs("tahun_pelajaran", "2025/2026"),
        "hari_aktif": gs("hari_aktif", "Senin,Selasa,Rabu,Kamis,Jumat").split(","),
        "jam_per_hari": int(gs("jam_per_hari", "8")),
        "max_blok": int(gs("max_blok", "2")),
        "waktu_mulai": gs("waktu_mulai", "07:00"),
        "durasi_jam": int(gs("durasi_jam", "35")),
        "durasi_aktivitas_khusus": int(gs("durasi_aktivitas_khusus", "35")),
        "istirahat": json.loads(gs("istirahat", "[]")),
        "aktivitas_khusus": json.loads(gs("aktivitas_khusus", "{}")),
    }
    return render_template("akademik/pengaturan.html", settings=settings, active_menu="pengaturan")
