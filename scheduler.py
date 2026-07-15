"""
scheduler.py
Mesin pembangkit jadwal pelajaran.

Pendekatan: scored greedy dengan multi-restart.
Setiap mata pelajaran dipecah menjadi "blok" jam (maksimal `max_blok` jam
berturut-turut per hari), lalu setiap blok dicari semua slot (hari, jam ke-)
yang valid (tidak bentrok kelas & guru) dan dipilih yang memiliki skor
tertinggi berdasarkan preferensi guru dan aturan mapel.

Fitur:
  - Hard constraint: pagi_saja (mapel hanya di jam awal)
  - Soft constraint: preferensi hari & waktu guru (skoring)
  - Multi-restart: mengulang dengan urutan acak berbeda
"""

import random


def split_blocks(jam, max_blok=2):
    """Memecah total jam/minggu menjadi blok-blok (misal 5 -> [2, 2, 1])."""
    blocks = []
    remaining = int(jam)
    while remaining > 0:
        take = min(max_blok, remaining)
        blocks.append(take)
        remaining -= take
    return blocks


def _score_placement(item, candidate_slots, preferensi_guru, aturan_mapel, jam_per_hari):
    """
    Memberi skor pada kandidat slot (hari, jam_ke) untuk suatu blok mapel.
    Return None jika kandidat melanggar hard constraint.
    """
    hari = candidate_slots[0][0]
    start_ke = candidate_slots[0][1]
    mapel_id = item["mapel_id"]
    guru_id = item["guru_id"]

    # --- Hard constraint: aturan mapel ---
    if aturan_mapel and mapel_id in aturan_mapel:
        rule = aturan_mapel[mapel_id]
        if rule.get("pagi_saja") and rule.get("max_jam_ke") is not None:
            if any(j > rule["max_jam_ke"] for _, j in candidate_slots):
                return None

    score = 0

    # --- Soft constraint: preferensi guru ---
    if preferensi_guru and guru_id in preferensi_guru:
        pref = preferensi_guru[guru_id]
        bobot = pref.get("bobot", 5)

        if pref.get("hari") and hari in pref["hari"]:
            score += bobot

        mid = jam_per_hari // 2
        if pref.get("waktu") == "pagi" and start_ke <= mid:
            score += bobot
        elif pref.get("waktu") == "siang" and start_ke > mid:
            score += bobot

    # Random kecil untuk variasi tie-break
    score += random.random() * 0.1
    return score


def generate_jadwal(requirements, hari_list, jam_per_hari, max_blok=2,
                    max_attempts=300, seed=None,
                    preferensi_guru=None, aturan_mapel=None):
    """
    Parameters
    ----------
    requirements : list[dict]
        keys: kelas_id, kelas_nama, mapel_id, kode, nama_mapel,
              guru_id, guru_nama, jam_per_minggu
    hari_list : list[str]
        hari aktif, misal ["Senin", ..., "Jumat"]
    jam_per_hari : int
        jumlah jam per hari
    max_blok : int
        maksimal jam berurutan per mapel per hari (default 2)
    max_attempts : int
        jumlah percobaan acak (default 300)
    seed : int or None
        seed untuk reproducibility
    preferensi_guru : dict or None
        {guru_id: {"hari": [...], "waktu": "...", "bobot": N}}
    aturan_mapel : dict or None
        {mapel_id: {"pagi_saja": bool, "max_jam_ke": int}}

    Returns
    -------
    tuple (assigned_rows, unplaced_items)
    """
    if seed is not None:
        random.seed(seed)

    if not requirements:
        return [], []

    preferensi_guru = preferensi_guru or {}
    aturan_mapel = aturan_mapel or {}

    best_assigned = None
    best_unplaced = None

    for _ in range(max_attempts):
        kelas_busy = {}
        guru_busy = {}
        assigned = []
        unplaced = []

        # Bangun daftar blok, lalu acak
        block_items = []
        for r in requirements:
            for blok in split_blocks(r["jam_per_minggu"], max_blok):
                block_items.append({**r, "blok": blok})
        random.shuffle(block_items)

        for item in block_items:
            kelas_id = item["kelas_id"]
            guru_id = item["guru_id"]
            mapel_id = item["mapel_id"]
            blok = item["blok"]

            kelas_busy.setdefault(kelas_id, set())
            guru_busy.setdefault(guru_id, set())

            candidates = []
            for h in hari_list:
                max_start = jam_per_hari - blok + 1
                if max_start < 1:
                    continue
                for s in range(1, max_start + 1):
                    slots = [(h, j) for j in range(s, s + blok)]
                    if any(c in kelas_busy[kelas_id] for c in slots):
                        continue
                    if any(c in guru_busy[guru_id] for c in slots):
                        continue

                    sval = _score_placement(item, slots, preferensi_guru,
                                            aturan_mapel, jam_per_hari)
                    if sval is not None:
                        candidates.append((sval, slots))

            if candidates:
                candidates.sort(key=lambda x: -x[0])
                best_slots = candidates[0][1]
                for c in best_slots:
                    kelas_busy[kelas_id].add(c)
                    guru_busy[guru_id].add(c)
                    assigned.append((kelas_id, mapel_id, c[0], c[1]))
            else:
                unplaced.append(item)

        if best_unplaced is None or len(unplaced) < len(best_unplaced):
            best_assigned, best_unplaced = assigned, unplaced

        if not best_unplaced:
            break

    return best_assigned, best_unplaced
