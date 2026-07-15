from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Guru, Kelas, Mapel, AturanMapel, BebanAjar, Pengaturan
from app.routes.auth import admin_required

master_bp = Blueprint("master", __name__, url_prefix="/master")


# --- GURU ---
@master_bp.route("/guru", methods=["GET", "POST"])
@login_required
def guru():
    if request.method == "POST" and current_user.role == "admin":
        data = request.form
        try:
            # Update existing
            for key, val in data.items():
                if key.startswith("nama_") and key != "nama_baru":
                    suffix = key[len("nama_"):]
                    if suffix.isdigit():
                        gid = int(suffix)
                    g = db.session.get(Guru, gid)
                    if g:
                        g.nama = val.strip()
            # Add new
            nama_baru = data.get("nama_baru", "").strip()
            if nama_baru and not Guru.query.filter_by(nama=nama_baru).first():
                db.session.add(Guru(nama=nama_baru))
            # Delete
            hapus_ids = data.get("hapus_ids", "")
            for hid in hapus_ids.split(","):
                hid = hid.strip()
                if hid and hid.isdigit():
                    g = db.session.get(Guru, int(hid))
                    if g:
                        db.session.delete(g)
            db.session.commit()
            flash("Data guru disimpan.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error: {e}", "danger")
        return redirect(url_for("master.guru"))
    guru_list = Guru.query.order_by(Guru.nama).all()
    return render_template("master/guru.html", guru_list=guru_list, active_menu="guru")


# --- KELAS ---
@master_bp.route("/kelas", methods=["GET", "POST"])
@login_required
def kelas():
    if request.method == "POST" and current_user.role == "admin":
        data = request.form
        try:
            for key, val in data.items():
                if key.startswith("jurusan_") and not key.endswith("_baru"):
                    suffix = key[len("jurusan_"):]
                    if suffix.isdigit():
                        kid = int(suffix)
                    k = db.session.get(Kelas, kid)
                    if k:
                        k.jurusan = data.get(f"jurusan_{kid}", "").strip()
                        k.tingkat = data.get(f"tingkat_{kid}", "").strip()
                        k.nama_kelas = data.get(f"nama_kelas_{kid}", "").strip()
            nama_baru = request.form.get("nama_kelas_baru", "").strip()
            if nama_baru and not Kelas.query.filter_by(nama_kelas=nama_baru).first():
                db.session.add(Kelas(
                    jurusan=request.form.get("jurusan_baru", "").strip(),
                    tingkat=request.form.get("tingkat_baru", "").strip(),
                    nama_kelas=nama_baru,
                ))
            hapus_ids = data.get("hapus_ids", "")
            for hid in hapus_ids.split(","):
                hid = hid.strip()
                if hid and hid.isdigit():
                    k = db.session.get(Kelas, int(hid))
                    if k:
                        db.session.delete(k)
            db.session.commit()
            flash("Data kelas disimpan.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error: {e}", "danger")
        return redirect(url_for("master.kelas"))
    kelas_list = Kelas.query.order_by(Kelas.nama_kelas).all()
    return render_template("master/kelas.html", kelas_list=kelas_list, active_menu="kelas")


# --- MAPEL ---
@master_bp.route("/mapel", methods=["GET", "POST"])
@login_required
def mapel():
    if request.method == "POST" and current_user.role == "admin":
        data = request.form
        try:
            # Update existing
            for key, val in data.items():
                if key.startswith("kode_") and key != "kode_baru":
                    suffix = key[len("kode_"):]
                    if suffix.isdigit():
                        mid = int(suffix)
                    m = db.session.get(Mapel, mid)
                    if m:
                        m.kode = val.strip()
                        m.nama_mapel = data.get(f"nama_mapel_{mid}", "").strip()
                        guru_id_val = data.get(f"guru_id_{mid}", "").strip()
                        m.guru_id = int(guru_id_val) if guru_id_val and guru_id_val.isdigit() else None
                        # aturan
                        at = m.aturan
                        if not at:
                            at = AturanMapel(mapel_id=m.id)
                            db.session.add(at)
                        at.pagi_saja = bool(data.get(f"pagi_saja_{mid}"))
                        max_jk = data.get(f"max_jam_ke_{mid}", "").strip()
                        at.max_jam_ke = int(max_jk) if max_jk and max_jk.isdigit() else None
            # Add new
            kode_baru = data.get("kode_baru", "").strip()
            if kode_baru and not Mapel.query.filter_by(kode=kode_baru).first():
                m = Mapel(
                    kode=kode_baru,
                    nama_mapel=data.get("nama_mapel_baru", "").strip(),
                    guru_id=int(data.get("guru_id_baru")) if data.get("guru_id_baru", "").isdigit() else None,
                )
                db.session.add(m)
                db.session.flush()
                at = AturanMapel(
                    mapel_id=m.id,
                    pagi_saja=bool(data.get("pagi_saja_baru")),
                    max_jam_ke=int(data.get("max_jam_ke_baru")) if data.get("max_jam_ke_baru", "").isdigit() else None,
                )
                db.session.add(at)
            # Delete
            hapus_ids = data.get("hapus_ids", "")
            for hid in hapus_ids.split(","):
                hid = hid.strip()
                if hid and hid.isdigit():
                    m = db.session.get(Mapel, int(hid))
                    if m:
                        db.session.delete(m)
            db.session.commit()
            flash("Data mapel disimpan.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error: {e}", "danger")
        return redirect(url_for("master.mapel"))
    mapel_list = Mapel.query.order_by(Mapel.kode).all()
    guru_list = Guru.query.order_by(Guru.nama).all()
    jam_per_hari = db.session.get(Pengaturan, "jam_per_hari")
    max_jam = int(jam_per_hari.value) if jam_per_hari and jam_per_hari.value else 8
    return render_template("master/mapel.html", mapel_list=mapel_list,
                           guru_list=guru_list, max_jam=max_jam,
                           active_menu="mapel")
