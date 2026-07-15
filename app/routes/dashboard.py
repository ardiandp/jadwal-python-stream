from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app import db
from app.models import Guru, Mapel, Kelas, BebanAjar, VersiJadwal, Pengaturan

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    jumlah_guru = Guru.query.count()
    jumlah_mapel = Mapel.query.count()
    jumlah_kelas = Kelas.query.count()
    jumlah_versi = VersiJadwal.query.count()

    # Beban guru
    guru_beban = (
        db.session.query(Guru.nama, db.func.coalesce(db.func.sum(BebanAjar.jam_per_minggu), 0))
        .outerjoin(Mapel, Mapel.guru_id == Guru.id)
        .outerjoin(BebanAjar, BebanAjar.mapel_id == Mapel.id)
        .group_by(Guru.id, Guru.nama)
        .order_by(Guru.nama)
        .all()
    )

    return render_template("dashboard/index.html",
                           jumlah_guru=jumlah_guru,
                           jumlah_mapel=jumlah_mapel,
                           jumlah_kelas=jumlah_kelas,
                           jumlah_versi=jumlah_versi,
                           guru_beban=guru_beban,
                           active_menu="dashboard")
