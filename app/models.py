from datetime import datetime, timezone


# MySQL DATETIME doesn't store timezone, so we strip it
def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="guru")
    guru_id = db.Column(db.Integer, db.ForeignKey("guru.id", ondelete="SET NULL"), nullable=True)

    guru = db.relationship("Guru", backref="user", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Guru(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), unique=True, nullable=False)

    mapel_list = db.relationship("Mapel", backref="guru", lazy=True)
    preferensi_list = db.relationship("PreferensiGuru", backref="guru", lazy=True, cascade="all, delete-orphan")


class Kelas(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jurusan = db.Column(db.String(50), nullable=False)
    tingkat = db.Column(db.String(20), nullable=False)
    nama_kelas = db.Column(db.String(50), unique=True, nullable=False)

    beban_list = db.relationship("BebanAjar", backref="kelas", lazy=True, cascade="all, delete-orphan")
    jadwal_list = db.relationship("Jadwal", backref="kelas", lazy=True, cascade="all, delete-orphan")


class Mapel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kode = db.Column(db.String(20), unique=True, nullable=False)
    nama_mapel = db.Column(db.String(100), nullable=False)
    guru_id = db.Column(db.Integer, db.ForeignKey("guru.id", ondelete="SET NULL"), nullable=True)

    beban_list = db.relationship("BebanAjar", backref="mapel", lazy=True, cascade="all, delete-orphan")
    aturan = db.relationship("AturanMapel", backref="mapel", uselist=False, lazy=True, cascade="all, delete-orphan")
    jadwal_list = db.relationship("Jadwal", backref="mapel", lazy=True, cascade="all, delete-orphan")


class BebanAjar(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mapel_id = db.Column(db.Integer, db.ForeignKey("mapel.id", ondelete="CASCADE"), nullable=False)
    kelas_id = db.Column(db.Integer, db.ForeignKey("kelas.id", ondelete="CASCADE"), nullable=False)
    jam_per_minggu = db.Column(db.Integer, nullable=False)

    __table_args__ = (db.UniqueConstraint("mapel_id", "kelas_id", name="uq_mapel_kelas"),)


class VersiJadwal(db.Model):
    __tablename__ = "versi_jadwal"

    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)
    dibuat = db.Column(db.DateTime, default=_now)
    total_slot = db.Column(db.Integer, default=0)
    unplaced_slot = db.Column(db.Integer, default=0)

    jadwal_list = db.relationship("Jadwal", backref="versi", lazy=True, cascade="all, delete-orphan")


class Jadwal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kelas_id = db.Column(db.Integer, db.ForeignKey("kelas.id", ondelete="CASCADE"), nullable=False)
    mapel_id = db.Column(db.Integer, db.ForeignKey("mapel.id", ondelete="CASCADE"), nullable=False)
    hari = db.Column(db.String(20), nullable=False)
    jam_ke = db.Column(db.Integer, nullable=False)
    versi_id = db.Column(db.Integer, db.ForeignKey("versi_jadwal.id", ondelete="CASCADE"), nullable=True)


class PreferensiGuru(db.Model):
    __tablename__ = "preferensi_guru"

    id = db.Column(db.Integer, primary_key=True)
    guru_id = db.Column(db.Integer, db.ForeignKey("guru.id", ondelete="CASCADE"), nullable=False)
    preferensi_hari = db.Column(db.String(100), nullable=True)
    preferensi_waktu = db.Column(db.String(20), nullable=True)
    bobot = db.Column(db.Integer, default=5)


class AturanMapel(db.Model):
    __tablename__ = "aturan_mapel"

    id = db.Column(db.Integer, primary_key=True)
    mapel_id = db.Column(db.Integer, db.ForeignKey("mapel.id", ondelete="CASCADE"), unique=True, nullable=False)
    pagi_saja = db.Column(db.Boolean, default=False)
    max_jam_ke = db.Column(db.Integer, nullable=True)


class Pengaturan(db.Model):
    __tablename__ = "pengaturan"

    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.Text, nullable=True)
