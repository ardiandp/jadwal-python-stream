from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, Guru
from app.forms import LoginForm, UserRegisterForm
from functools import wraps

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def admin_required(f):
    @wraps(f)
    @login_required
    def wrapper(*args, **kwargs):
        if current_user.role != "admin":
            flash("Akses ditolak. Hanya untuk admin.", "danger")
            return redirect(url_for("dashboard.index"))
        return f(*args, **kwargs)
    return wrapper


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash(f"Selamat datang, {user.username}!", "success")
            return redirect(url_for("dashboard.index"))
        flash("Username atau password salah.", "danger")
    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Anda telah logout.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"])
@admin_required
def register():
    form = UserRegisterForm()
    guru_choices = [(0, "-- Tidak ada --")] + [
        (g.id, g.nama) for g in Guru.query.order_by(Guru.nama).all()
    ]
    form.guru_id.choices = guru_choices
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash("Username sudah digunakan.", "danger")
            return render_template("auth/register.html", form=form, users=User.query.all())
        user = User(
            username=form.username.data,
            role=form.role.data,
            guru_id=form.guru_id.data if form.guru_id.data else None,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(f"User {user.username} berhasil dibuat.", "success")
        return redirect(url_for("auth.register"))
    return render_template("auth/register.html", form=form, users=User.query.all())


@auth_bp.route("/delete-user/<int:user_id>", methods=["POST"])
@admin_required
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash("User tidak ditemukan.", "danger")
    elif user.id == current_user.id:
        flash("Tidak bisa menghapus diri sendiri.", "danger")
    else:
        db.session.delete(user)
        db.session.commit()
        flash(f"User {user.username} dihapus.", "success")
    return redirect(url_for("auth.register"))
