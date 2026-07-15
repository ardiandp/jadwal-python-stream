from app import db as sqldb
from app.models import Mapel, Kelas, BebanAjar, Pengaturan


def get_verification_data():
    """Returns dict with verification data similar to old db.get_verification_data()."""
    mapel_list = Mapel.query.options(
        sqldb.joinedload(Mapel.beban_list),
        sqldb.joinedload(Mapel.guru),
    ).all()

    kelas_list = Kelas.query.options(
        sqldb.joinedload(Kelas.beban_list),
    ).all()

    mapel_tanpa_guru = []
    mapel_tanpa_beban_list = []
    for m in mapel_list:
        if m.guru_id is None:
            mapel_tanpa_guru.append({"kode": m.kode, "nama_mapel": m.nama_mapel})
        if len(m.beban_list) == 0:
            mapel_tanpa_beban_list.append({"kode": m.kode, "nama_mapel": m.nama_mapel})

    kelas_tanpa_beban = []
    for k in kelas_list:
        if len(k.beban_list) == 0:
            kelas_tanpa_beban.append(k.nama_kelas)

    # Duplicates
    from collections import Counter
    kode_counts = Counter(m.kode for m in mapel_list)
    duplikat_kode = [k for k, v in kode_counts.items() if v > 1]
    nama_kelas_counts = Counter(k.nama_kelas for k in kelas_list)
    duplikat_kelas = [nk for nk, v in nama_kelas_counts.items() if v > 1]

    # Total JP per kelas
    beban_list = BebanAjar.query.all()
    total_jp_per_kelas = {}
    for b in beban_list:
        k = sqldb.session.get(Kelas, b.kelas_id)
        if k:
            total_jp_per_kelas[k.nama_kelas] = total_jp_per_kelas.get(k.nama_kelas, 0) + b.jam_per_minggu

    # Total jam per guru
    total_jam_per_guru = {}
    for b in beban_list:
        m = sqldb.session.get(Mapel, b.mapel_id)
        if m and m.guru:
            total_jam_per_guru[m.guru.nama] = total_jam_per_guru.get(m.guru.nama, 0) + b.jam_per_minggu
        elif m and not m.guru:
            total_jam_per_guru["(tanpa guru)"] = total_jam_per_guru.get("(tanpa guru)", 0) + b.jam_per_minggu

    return {
        "mapel_tanpa_guru": mapel_tanpa_guru,
        "mapel_tanpa_beban": mapel_tanpa_beban_list,
        "kelas_tanpa_beban": kelas_tanpa_beban,
        "duplikat_kode": duplikat_kode,
        "duplikat_kelas": duplikat_kelas,
        "total_jp_per_kelas": total_jp_per_kelas,
        "total_jam_per_guru": total_jam_per_guru,
        "jumlah_mapel": len(mapel_list),
        "jumlah_kelas": len(kelas_list),
        "jumlah_guru": len(set(m.guru_id for m in mapel_list if m.guru_id)),
    }
