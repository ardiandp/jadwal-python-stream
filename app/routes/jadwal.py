import json
import io
import random
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user
from app import db as sqldb
from app.models import (
    Mapel, Kelas, BebanAjar, Jadwal, VersiJadwal,
    PreferensiGuru, AturanMapel, Pengaturan, Guru,
)
from app.services.scheduler import generate_jadwal
from app.services.verification import get_verification_data
from app.services.export import get_settings_dict, render_jadwal_html, export_excel, build_alokasi_df
from app.routes.auth import admin_required
import pandas as pd

jadwal_bp = Blueprint("jadwal", __name__, url_prefix="/jadwal")


def _verify(hari_aktif, jam_per_hari):
    v = get_verification_data()
    kapasitas = len(hari_aktif) * jam_per_hari

    errors = []
    warnings = []
    info_items = []

    # ERROR
    if v["mapel_tanpa_guru"]:
        items = [f"{m['kode']} - {m['nama_mapel']}" for m in v["mapel_tanpa_guru"]]
        errors.append({
            "label": "Mapel tanpa guru pengampu",
            "items": items,
            "rekomendasi": "Tambahkan guru pengampu di menu **Data Mapel & Penugasan**",
        })

    if v["kelas_tanpa_beban"]:
        errors.append({
            "label": "Kelas tanpa beban ajar",
            "items": v["kelas_tanpa_beban"],
            "rekomendasi": "Atur jam pelajaran untuk kelas ini di menu **Beban Ajar**",
        })

    if v["duplikat_kode"]:
        errors.append({
            "label": "Kode mapel duplikat",
            "items": v["duplikat_kode"],
            "rekomendasi": "Ubah kode mapel duplikat di menu **Data Mapel & Penugasan**",
        })

    if v["duplikat_kelas"]:
        errors.append({
            "label": "Nama kelas duplikat",
            "items": v["duplikat_kelas"],
            "rekomendasi": "Ubah nama kelas duplikat di menu **Data Kelas**",
        })

    # WARNING
    if v["mapel_tanpa_beban"]:
        items = [f"{m['kode']} - {m['nama_mapel']}" for m in v["mapel_tanpa_beban"]]
        warnings.append({
            "label": "Mapel tidak memiliki beban ajar (tidak masuk jadwal)",
            "items": items,
            "rekomendasi": "Atur jam pelajaran untuk mapel ini di menu **Beban Ajar**",
        })

    for nama_kelas, jp in sorted(v["total_jp_per_kelas"].items()):
        selisih = kapasitas - jp
        if selisih > 0:
            warnings.append({
                "label": f"Kelas {nama_kelas}: JP {jp} dari {kapasitas} (kurang {selisih} slot)",
                "items": [],
                "rekomendasi": "Tambah jam pelajaran di **Beban Ajar** atau kurangi jumlah hari aktif di **Pengaturan**",
            })
        elif selisih < 0:
            warnings.append({
                "label": f"Kelas {nama_kelas}: JP {jp} dari {kapasitas} (kelebihan {abs(selisih)} slot)",
                "items": [],
                "rekomendasi": "Kurangi jam pelajaran di **Beban Ajar** atau tambah jumlah hari aktif di **Pengaturan**",
            })

    # INFO
    info_items.append(f"Guru: {v['jumlah_guru']}")
    info_items.append(f"Mapel: {v['jumlah_mapel']}")
    info_items.append(f"Kelas: {v['jumlah_kelas']}")
    total_jam = sum(v["total_jp_per_kelas"].values())
    info_items.append(f"Total JP: {total_jam} | Kapasitas: {v['jumlah_kelas'] * kapasitas} slot")

    guru_beban = []
    for guru, jam in sorted(v["total_jam_per_guru"].items()):
        guru_beban.append(f"{guru}: {jam} JP/minggu")
    if guru_beban:
        info_items.append(f"Beban guru: {' | '.join(guru_beban)}")

    return {
        "errors": errors,
        "warnings": warnings,
        "info": info_items,
        "siap": len(errors) == 0,
        "kapasitas": kapasitas,
    }


@jadwal_bp.route("/generate", methods=["GET", "POST"])
@login_required
def generate():
    settings = get_settings_dict()
    hari_aktif = settings["hari_aktif"]
    jam_per_hari = settings["jam_per_hari"]

    verifikasi = _verify(hari_aktif, jam_per_hari)

    # Calculate total requirements
    reqs = BebanAjar.query.options(
        sqldb.joinedload(BebanAjar.mapel).joinedload(Mapel.guru),
        sqldb.joinedload(BebanAjar.kelas),
    ).all()
    total_jam = sum(r.jam_per_minggu for r in reqs)

    if request.method == "POST":
        override = request.form.get("override") == "1"
        if not verifikasi["siap"] and not override:
            flash("Ada error yang harus diperbaiki. Centang override jika tetap ingin generate.", "danger")
            return redirect(url_for("jadwal.generate"))

        max_attempts = int(request.form.get("max_attempts", 300))
        num_versions = int(request.form.get("num_versions", 3))

        try:
            # Prepare requirements dict
            requirements = []
            for r in reqs:
                requirements.append({
                    "kelas_id": r.kelas_id,
                    "kelas_nama": r.kelas.nama_kelas,
                    "mapel_id": r.mapel_id,
                    "kode": r.mapel.kode,
                    "nama_mapel": r.mapel.nama_mapel,
                    "guru_id": r.mapel.guru_id,
                    "guru_nama": r.mapel.guru.nama if r.mapel.guru else None,
                    "jam_per_minggu": r.jam_per_minggu,
                })

            # Preferences & rules
            preferensi_guru = {}
            for p in PreferensiGuru.query.all():
                preferensi_guru[p.guru_id] = {
                    "hari": [h.strip() for h in (p.preferensi_hari or "").split(",") if h.strip()],
                    "waktu": p.preferensi_waktu or "",
                    "bobot": p.bobot or 5,
                }

            aturan_mapel = {}
            for a in AturanMapel.query.all():
                aturan_mapel[a.mapel_id] = {
                    "pagi_saja": a.pagi_saja,
                    "max_jam_ke": a.max_jam_ke,
                }

            # Generate versions
            best_versions = []
            for vi in range(num_versions):
                assigned, unplaced = generate_jadwal(
                    requirements=requirements,
                    hari_list=hari_aktif,
                    jam_per_hari=jam_per_hari,
                    max_blok=settings["max_blok"],
                    max_attempts=max_attempts,
                    preferensi_guru=preferensi_guru,
                    aturan_mapel=aturan_mapel,
                )

                # Save version
                total = len(assigned)
                unplaced_count = len(unplaced)
                v = VersiJadwal(
                    nama=f"Versi {vi + 1} (generated)",
                    total_slot=total,
                    unplaced_slot=unplaced_count,
                )
                sqldb.session.add(v)
                sqldb.session.flush()

                # Save jadwal rows
                for row in assigned:
                    sqldb.session.add(Jadwal(
                        kelas_id=row[0],
                        mapel_id=row[1],
                        hari=row[2],
                        jam_ke=row[3],
                        versi_id=v.id,
                    ))

                best_versions.append({
                    "versi_id": v.id,
                    "nama": v.nama,
                    "total": total,
                    "unplaced": unplaced_count,
                    "unplaced_detail": unplaced[:5],
                })

            sqldb.session.commit()
            flash(f"Generate selesai! {len(best_versions)} versi dibuat.", "success")

        except Exception as e:
            sqldb.session.rollback()
            flash(f"Error saat generate: {e}", "danger")

        return redirect(url_for("jadwal.lihat_jadwal"))

    # GET - show existing versions
    versi_list = VersiJadwal.query.order_by(VersiJadwal.id.desc()).all()
    return render_template("jadwal/generate.html",
                           settings=settings,
                           verifikasi=verifikasi,
                           total_jam=total_jam,
                           versi_list=versi_list,
                           active_menu="generate")


@jadwal_bp.route("/delete-versi/<int:versi_id>", methods=["POST"])
@login_required
def delete_versi(versi_id):
    if current_user.role != "admin":
        flash("Akses ditolak.", "danger")
        return redirect(url_for("jadwal.generate"))
    v = sqldb.session.get(VersiJadwal, versi_id)
    if v:
        sqldb.session.delete(v)
        sqldb.session.commit()
        flash(f"Versi {v.nama} dihapus.", "success")
    return redirect(url_for("jadwal.generate"))


@jadwal_bp.route("/lihat")
@login_required
def lihat_jadwal():
    settings = get_settings_dict()
    hari_aktif = settings["hari_aktif"]
    jam_per_hari = settings["jam_per_hari"]
    versi_list = VersiJadwal.query.order_by(VersiJadwal.id.desc()).all()

    if not versi_list:
        flash("Belum ada jadwal. Generate terlebih dahulu.", "warning")
        return redirect(url_for("jadwal.generate"))

    versi_id = request.args.get("versi_id", type=int) or versi_list[0].id
    versi_selected = sqldb.session.get(VersiJadwal, versi_id)

    # Get all jadwal for this version
    jadwal_data = (
        sqldb.session.query(Jadwal, Mapel, Guru, Kelas)
        .join(Mapel, Jadwal.mapel_id == Mapel.id)
        .outerjoin(Guru, Mapel.guru_id == Guru.id)
        .join(Kelas, Jadwal.kelas_id == Kelas.id)
        .filter(Jadwal.versi_id == versi_id)
        .all()
    )

    # Build DataFrame for raw view
    rows = []
    for j, m, g, k in jadwal_data:
        rows.append({
            "Kelas": k.nama_kelas,
            "Kode": m.kode,
            "Mapel": m.nama_mapel,
            "Guru": g.nama if g else "-",
            "Hari": j.hari,
            "Jam Ke": j.jam_ke,
        })
    df = pd.DataFrame(rows)

    kelas_list = sorted(df["Kelas"].unique()) if not df.empty else []
    guru_list = sorted(set(r["Guru"] for r in rows)) if rows else []

    # Get selected class for HTML view
    kelas_pilihan = request.args.get("kelas", kelas_list[0] if kelas_list else "")

    html_jadwal = ""
    if kelas_pilihan:
        html_jadwal = render_jadwal_html(versi_id, kelas_pilihan, settings)

    guru_pilihan = request.args.get("guru", guru_list[0] if guru_list else "")

    return render_template("jadwal/lihat_jadwal.html",
                           settings=settings,
                           versi_list=versi_list,
                           versi_selected=versi_selected,
                           versi_id=versi_id,
                           kelas_list=kelas_list,
                           kelas_pilihan=kelas_pilihan,
                           html_jadwal=html_jadwal,
                           guru_list=guru_list,
                           guru_pilihan=guru_pilihan,
                           df=df,
                           df_json=df.to_json(orient="records") if not df.empty else "[]",
                           active_menu="jadwal")


@jadwal_bp.route("/export-excel/<int:versi_id>")
@login_required
def export_excel_route(versi_id):
    settings = get_settings_dict()
    buf = export_excel(versi_id, settings)
    tahun_pelajaran = settings["tahun_pelajaran"].replace("/", "_")
    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"jadwal_pelajaran_{tahun_pelajaran}.xlsx",
    )


@jadwal_bp.route("/export-html/<int:versi_id>/<kelas>")
@login_required
def export_html(versi_id, kelas):
    settings = get_settings_dict()
    html_content = render_jadwal_html(versi_id, kelas, settings)
    full_html = f"""<!DOCTYPE html><html lang="id"><head><meta charset="UTF-8">
<title>Jadwal {kelas}</title></head><body style="margin:20px;">
{html_content}
</body></html>"""
    buf = io.BytesIO(full_html.encode("utf-8"))
    return send_file(
        buf,
        mimetype="text/html",
        as_attachment=True,
        download_name=f"jadwal_{kelas}.html",
    )
