from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SelectField, SelectMultipleField,
    IntegerField, SubmitField, BooleanField, FieldList, FormField,
)
from wtforms.validators import DataRequired, Length, Optional, NumberRange


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Masuk")


class UserRegisterForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=4)])
    role = SelectField("Role", choices=[("admin", "Admin"), ("guru", "Guru"), ("kepsek", "Kepsek")])
    guru_id = SelectField("Linked Guru", coerce=int, choices=[(0, "-- Tidak ada --")])
    submit = SubmitField("Simpan")


class SettingForm(FlaskForm):
    nama_sekolah = StringField("Nama Sekolah")
    tahun_pelajaran = StringField("Tahun Pelajaran")
    hari_aktif = SelectMultipleField("Hari Aktif", choices=[
        ("Senin", "Senin"), ("Selasa", "Selasa"), ("Rabu", "Rabu"),
        ("Kamis", "Kamis"), ("Jumat", "Jumat"), ("Sabtu", "Sabtu"),
    ])
    jam_per_hari = IntegerField("Jam per Hari", validators=[NumberRange(min=1, max=12)])
    max_blok = IntegerField("Max Blok", validators=[NumberRange(min=1, max=4)])
    waktu_mulai = StringField("Waktu Mulai")
    durasi_jam = IntegerField("Durasi Jam (menit)", validators=[NumberRange(min=15, max=120)])
    durasi_aktivitas_khusus = IntegerField("Durasi Aktivitas Khusus (menit)", validators=[NumberRange(min=5, max=120)])
    submit = SubmitField("Simpan Pengaturan")
