import json
import io
import pandas as pd
from flask import send_file
from app import db as sqldb
from app.models import Mapel, BebanAjar, Jadwal, Kelas, VersiJadwal, Pengaturan, Guru


def get_settings_dict():
    def gs(key, default=""):
        p = sqldb.session.get(Pengaturan, key)
        return p.value if p else default

    istirahat_raw = gs("istirahat", '[{"setelah":3,"durasi":30},{"setelah":6,"durasi":35}]')
    try:
        istirahat = json.loads(istirahat_raw)
    except Exception:
        istirahat = [{"setelah": 3, "durasi": 30}, {"setelah": 6, "durasi": 35}]

    aktivitas_khusus_raw = gs("aktivitas_khusus", "{}")
    try:
        aktivitas_khusus = json.loads(aktivitas_khusus_raw)
    except Exception:
        aktivitas_khusus = {}

    return {
        "hari_aktif": gs("hari_aktif", "Senin,Selasa,Rabu,Kamis,Jumat").split(","),
        "jam_per_hari": int(gs("jam_per_hari", "8")),
        "max_blok": int(gs("max_blok", "2")),
        "waktu_mulai": gs("waktu_mulai", "07:00"),
        "durasi_jam": int(gs("durasi_jam", "35")),
        "durasi_aktivitas_khusus": int(gs("durasi_aktivitas_khusus", "35")),
        "istirahat": istirahat,
        "nama_sekolah": gs("nama_sekolah", "SD NEGERI ....."),
        "tahun_pelajaran": gs("tahun_pelajaran", "2025/2026"),
        "aktivitas_khusus": aktivitas_khusus,
    }


def calculate_times(waktu_mulai, durasi_jam, durasi_aktivitas_khusus, istirahat_list, jam_per_hari):
    jam_int, menit = map(int, waktu_mulai.split(":"))
    current = jam_int * 60 + menit
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


def time_str(minutes):
    return f"{minutes // 60:02d}.{minutes % 60:02d}"


def build_alokasi_df(kelas_id=None):
    query = BebanAjar.query.options(sqldb.joinedload(BebanAjar.mapel))
    if kelas_id:
        query = query.filter(BebanAjar.kelas_id == kelas_id)
    beban_list = query.all()

    agg = {}
    for b in beban_list:
        label = f"{b.mapel.kode} - {b.mapel.nama_mapel}"
        agg[label] = agg.get(label, 0) + b.jam_per_minggu
    if not agg:
        return pd.DataFrame()
    return pd.DataFrame([{"mapel": k, "jp": v} for k, v in sorted(agg.items())])


def render_jadwal_html(versi_id, kelas_nama, settings):
    hari_aktif = settings["hari_aktif"]
    jam_per_hari = settings["jam_per_hari"]
    nama_sekolah = settings["nama_sekolah"]
    tahun_pelajaran = settings["tahun_pelajaran"]
    aktivitas_khusus = settings["aktivitas_khusus"]

    jadwal_rows = (
        sqldb.session.query(Jadwal, Mapel, Guru)
        .join(Mapel, Jadwal.mapel_id == Mapel.id)
        .outerjoin(Guru, Mapel.guru_id == Guru.id)
        .join(Kelas, Jadwal.kelas_id == Kelas.id)
        .filter(Jadwal.versi_id == versi_id, Kelas.nama_kelas == kelas_nama)
        .all()
    )

    cell_map = {}
    for j, m, g in jadwal_rows:
        guru_text = f" ({g.nama})" if g else ""
        cell_map[(j.hari, j.jam_ke)] = f"{m.kode} - {m.nama_mapel}{guru_text}"

    kelas_obj = Kelas.query.filter_by(nama_kelas=kelas_nama).first()
    alokasi_df = build_alokasi_df(kelas_obj.id if kelas_obj else None)
    times = calculate_times(
        settings["waktu_mulai"], settings["durasi_jam"],
        settings["durasi_aktivitas_khusus"], settings["istirahat"], jam_per_hari
    )

    parts = []
    parts.append(f'<h3 style="text-align:center;margin:5px 0;font-family:Arial,sans-serif;">{nama_sekolah}</h3>')
    parts.append(f'<h3 style="text-align:center;margin:5px 0;font-family:Arial,sans-serif;">TAHUN PELAJARAN {tahun_pelajaran}</h3>')
    parts.append(f'<p style="font-weight:bold;font-size:14px;margin:5px 0;font-family:Arial,sans-serif;">KELAS {kelas_nama}</p>')

    parts.append('<div style="display:flex;gap:30px;align-items:flex-start;">')
    parts.append('<div>')
    parts.append('<table style="border-collapse:collapse;text-align:center;font-family:Arial,sans-serif;font-size:13px;">')

    col_count = 2 + len(hari_aktif)
    parts.append('<tr>')
    parts.append(f'<th rowspan="2" style="background:#4472C4;color:white;border:1px solid black;padding:4px 8px;">Jam Ke</th>')
    parts.append(f'<th rowspan="2" style="background:#4472C4;color:white;border:1px solid black;padding:4px 8px;">WAKTU</th>')
    parts.append(f'<th colspan="{len(hari_aktif)}" style="background:#4472C4;color:white;border:1px solid black;padding:4px 8px;">HARI</th>')
    parts.append('</tr>')
    parts.append('<tr>')
    for h in hari_aktif:
        parts.append(f'<th style="background:#4472C4;color:white;border:1px solid black;padding:4px 8px;">{h.upper()}</th>')
    parts.append('</tr>')

    for t in times:
        if t["is_break"]:
            parts.append(
                f'<tr><td colspan="{col_count}" style="background:#FFFF00;border:1px solid black;'
                f'padding:4px 8px;font-style:italic;">'
                f'{time_str(t["start"])}-{time_str(t["end"])}  '
                f'&nbsp;&nbsp;&nbsp;&nbsp;Istirahat</td></tr>'
            )
        elif t.get("is_special"):
            parts.append('<tr>')
            parts.append(f'<td style="border:1px solid black;padding:4px 8px;"></td>')
            parts.append(f'<td style="border:1px solid black;padding:4px 8px;">{time_str(t["start"])}-{time_str(t["end"])}</td>')
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
            parts.append(f'<td style="border:1px solid black;padding:4px 8px;">{time_str(t["start"])}-{time_str(t["end"])}</td>')
            for h in hari_aktif:
                content = cell_map.get((h, t["jam_ke"]), "")
                parts.append(f'<td style="border:1px solid black;padding:4px 8px;">{content}</td>')
            parts.append('</tr>')

    parts.append('</table>')
    parts.append('</div>')

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
    parts.append('</div>')
    parts.append('</div>')

    return "".join(parts)


def export_excel(versi_id, settings):
    hari_aktif = settings["hari_aktif"]
    jam_per_hari = settings["jam_per_hari"]
    aktivitas_khusus = settings["aktivitas_khusus"]

    jadwal_data = (
        sqldb.session.query(Jadwal, Mapel, Guru, Kelas)
        .join(Mapel, Jadwal.mapel_id == Mapel.id)
        .outerjoin(Guru, Mapel.guru_id == Guru.id)
        .join(Kelas, Jadwal.kelas_id == Kelas.id)
        .filter(Jadwal.versi_id == versi_id)
        .all()
    )

    times = calculate_times(
        settings["waktu_mulai"], settings["durasi_jam"],
        settings["durasi_aktivitas_khusus"], settings["istirahat"], jam_per_hari
    )

    # Group by kelas
    kelas_groups = {}
    for j, m, g, k in jadwal_data:
        kelas_groups.setdefault(k.nama_kelas, []).append((j, m, g))

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for kelas_name in sorted(kelas_groups.keys()):
            items = kelas_groups[kelas_name]
            cmap = {}
            for j, m, g in items:
                guru_text = f" ({g.nama})" if g else ""
                cmap[(j.hari, j.jam_ke)] = f"{m.kode} - {m.nama_mapel}{guru_text}"

            rows = []
            for t in times:
                row = {}
                if t["is_break"]:
                    row["Jam Ke"] = ""
                    row["WAKTU"] = f'{time_str(t["start"])}-{time_str(t["end"])}'
                    for h in hari_aktif:
                        row[h] = "ISTIRAHAT"
                elif t.get("is_special"):
                    row["Jam Ke"] = ""
                    row["WAKTU"] = f'{time_str(t["start"])}-{time_str(t["end"])}'
                    for h in hari_aktif:
                        row[h] = aktivitas_khusus.get(h, "")
                else:
                    row["Jam Ke"] = t["jam_ke"]
                    row["WAKTU"] = f'{time_str(t["start"])}-{time_str(t["end"])}'
                    for h in hari_aktif:
                        row[h] = cmap.get((h, t["jam_ke"]), "")
                rows.append(row)

            export_df = pd.DataFrame(rows)
            sheet_name = kelas_name[:31]
            export_df.to_excel(writer, sheet_name=sheet_name, index=False)

    buf.seek(0)
    return buf
