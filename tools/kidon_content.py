"""KidOn içerik araçları: JSONL görev kaynağı → kidon.tasks paketi.

Kaynak biçimi: content/src/YAZIM_KURALLARI.md. Bu modül hem uygulamaya gömülü paketi
(scripts/build-content.py) hem de uzaktan güncelleme paketlerini (kidon-icerik deposu) üretir.

Kimlikler içerikten türetilir (sha1) ve ASLA yeniden kullanılmaz: bir soru düzeltilirse yeni
kimlik alır; eskisini kaldırmak için paket `retired` listesine eklenir (active=false).
"""
import hashlib
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_curated import check_item  # noqa: E402

GRADES = ["okul_oncesi", "1", "2", "3", "4", "5", "6"]
GRADE_CODE = {"okul_oncesi": "oo", "1": "1", "2": "2", "3": "3", "4": "4", "5": "5", "6": "6"}
# Sınıf → varsayılan yaş grupları (sınıfı yaşından farklı ilerleyen çocuklar için komşu gruplar dahil)
DEFAULT_AGES = {
    "okul_oncesi": ["5-6"],
    "1": ["5-6", "7-8"],
    "2": ["7-8", "9-10"],
    "3": ["7-8", "9-10"],
    "4": ["9-10", "11-12"],
    "5": ["9-10", "11-12"],
    "6": ["11-12"],
}
LETTERS = "abcdefgh"


def canonical(o):
    keep = {k: o.get(k) for k in ("subject", "type", "prompt", "options", "answer", "pairs", "items", "unit")}
    return json.dumps(keep, ensure_ascii=False, sort_keys=True)


def task_id(prefix, grade, o):
    h = hashlib.sha1(canonical(o).encode("utf-8")).hexdigest()[:10]
    return f"{prefix}-{GRADE_CODE[grade]}-{h}"


def to_task(o, grade, prefix, content_version):
    errs = check_item(o)
    if errs:
        raise ValueError(f"{grade}: {o.get('prompt', '')[:60]!r}: {errs}")
    tid = task_id(prefix, grade, o)
    rnd = random.Random(tid)
    t = {
        "id": tid,
        "contentVersion": content_version,
        "ageGroups": o.get("ages") or DEFAULT_AGES[grade],
        "grades": [grade],
        "subject": o["subject"],
        "skill": o["skill"],
        "difficulty": o["difficulty"],
        "type": o["type"],
        "prompt": o["prompt"].strip(),
    }
    if o.get("emoji"):
        t["promptEmoji"] = o["emoji"]
    typ = o["type"]
    if typ == "multiple_choice":
        opts = [(LETTERS[i], txt.strip()) for i, txt in enumerate(o["options"])]
        correct = opts[o["answer"]][0]
        rnd.shuffle(opts)
        # Kimlikleri ekrandaki sıraya göre yeniden harflendir; doğru cevabın harfi tahmin edilemesin
        remap = {old: LETTERS[i] for i, (old, _) in enumerate(opts)}
        t["options"] = [{"id": remap[old], "text": txt} for old, txt in opts]
        t["answer"] = {"kind": "option", "optionId": remap[correct]}
    elif typ == "matching":
        t["pairs"] = [{"id": f"p{i + 1}", "left": l.strip(), "right": r.strip()} for i, (l, r) in enumerate(o["pairs"])]
        t["answer"] = {"kind": "pairs"}
    elif typ == "ordering":
        items = [{"id": f"i{i + 1}", "text": x.strip()} for i, x in enumerate(o["items"])]
        order = [x["id"] for x in items]
        shown = items[:]
        for _ in range(5):  # karışık göster; doğru sırayla aynı kalmasın
            rnd.shuffle(shown)
            if [x["id"] for x in shown] != order:
                break
        else:
            shown = shown[1:] + shown[:1]  # 5 denemede de doğru sıra çıktıysa kaydır
        t["items"] = shown
        t["answer"] = {"kind": "order", "order": order}
    elif typ == "number_input":
        t["answer"] = {"kind": "number", "value": int(o["answer"])}
        if o.get("unit"):
            t["unit"] = o["unit"]
    t["explanation"] = o["explanation"].strip()
    if o.get("hint"):
        t["hint"] = o["hint"].strip()
    t["active"] = True
    return t


def read_jsonl(path):
    out = []
    with open(path, encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            if line.strip():
                try:
                    out.append(json.loads(line))
                except Exception as ex:  # pragma: no cover
                    raise ValueError(f"{path}:{ln}: {ex}")
    return out


def tasks_from_dir(directory, prefix, content_version, seen):
    """directory/<sinif>.jsonl dosyalarından görevler. `seen`: id kümesi (tekrarları atlar)."""
    tasks = []
    for g in GRADES:
        p = Path(directory) / f"{g}.jsonl"
        if not p.exists():
            continue
        for o in read_jsonl(p):
            t = to_task(o, g, prefix, content_version)
            if t["id"] in seen:
                continue
            seen.add(t["id"])
            tasks.append(t)
    return tasks


def write_pack(path, version, tasks, note=None, updated_at=None):
    pack = {"schema": "kidon.tasks", "version": version}
    if updated_at:
        pack["updatedAt"] = updated_at
    if note:
        pack["note"] = note
    pack["tasks"] = tasks
    data = json.dumps(pack, ensure_ascii=False, separators=(",", ":"))
    Path(path).write_text(data, encoding="utf-8")
    return hashlib.sha256(data.encode("utf-8")).hexdigest(), len(data.encode("utf-8"))
