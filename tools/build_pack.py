#!/usr/bin/env python3
"""Yeni bir güncelleme paketi üretir ve manifest dosyalarını günceller.

Kullanım:  python3 tools/build_pack.py sources/2026-w42
  sources/<paket>/<sinif>.jsonl  (okul_oncesi, 1 … 8) — biçim: tools/YAZIM_KURALLARI.md
Çıktı:     packs/<paket>.json (okul öncesi–6), packs/<paket>-78.json (7–8. sınıf, varsa),
           manifest.json (uygulama 1.0.x: yalnızca okul öncesi–6), manifest-v2.json (1.1+: hepsi),
           tools/bilinen_sorular.txt

- 1.0.x sürümü 7-8. sınıfı tanımaz ve bilinmeyen sınıflı paketi tümden reddeder; bu yüzden 7-8 ayrı pakettedir
  ve yalnızca manifest-v2.json'da listelenir.
- MEB bağlantısı: görevde "meb" alanı yoksa tools/esleme/<sinif>.json eşlemesi (ders/beceri → ünite) uygulanır.

- Aynı sınıfta daha önce yayımlanmış (uygulamaya gömülü veya önceki paketlerdeki) bir soru metni atlanır.
- Paket sürümü her derlemede manifest'teki en büyük sürümün bir fazlasıdır (uygulama yeni sürümü indirir).
- Hatalı bir görevi geri çekmek için kimliğini manifest.json → "retired" listesine ekleyin.
"""
import json, re, sys, unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from kidon_content import GRADES, NEW_GRADES, apply_meb, read_jsonl, to_task, write_pack  # noqa: E402

BUNDLED_VERSION = 2  # uygulamaya gömülü paketin sürümü
MAX_PACK_BYTES = 6_000_000


def norm(s):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s)).strip().lower()


def main(src):
    src = Path(src)
    pack_id = src.name
    if not re.fullmatch(r"[a-z0-9_.-]{1,64}", pack_id):
        sys.exit("paket adı küçük harf/rakam/-/_ olmalı: " + pack_id)
    man_path = ROOT / "manifest.json"
    man2_path = ROOT / "manifest-v2.json"
    manifest = json.loads(man_path.read_text(encoding="utf-8"))
    manifest2 = json.loads(man2_path.read_text(encoding="utf-8")) if man2_path.exists() else json.loads(json.dumps(manifest))
    version = max([BUNDLED_VERSION] + [p["version"] for p in manifest["packs"] + manifest2["packs"]]) + 1
    mapping = {}
    for f in sorted((ROOT / "tools" / "esleme").glob("*.json")):
        for key, v in json.loads(f.read_text(encoding="utf-8")).items():
            subj, skill = key.split("/", 1)
            mapping[(f.stem, subj, skill)] = v
    known_path = ROOT / "tools/bilinen_sorular.txt"
    known = set(known_path.read_text(encoding="utf-8").splitlines())
    # Bu paketin önceki sürümündeki sorular "bilinen" sayılmasın (yeniden derleme)
    old = ROOT / "packs" / f"{pack_id}.json"
    if old.exists():
        for t in json.loads(old.read_text(encoding="utf-8"))["tasks"]:
            for g in t["grades"]:
                known.discard(g + "\t" + norm(t["prompt"]))
    tasks, skipped, seen = [], 0, set()
    for g in GRADES:
        f = src / f"{g}.jsonl"
        if not f.exists():
            continue
        for o in read_jsonl(f):
            key = g + "\t" + norm(o["prompt"])
            if len(o["prompt"]) > 30 and key in known:
                skipped += 1
                continue
            t = apply_meb(to_task(o, g, "u", version), mapping)
            if t["id"] in seen:
                skipped += 1
                continue
            seen.add(t["id"])
            known.add(key)
            tasks.append(t)
    if not tasks:
        sys.exit("pakette görev yok")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    base = [t for t in tasks if not (set(t["grades"]) & NEW_GRADES)]
    upper = [t for t in tasks if set(t["grades"]) & NEW_GRADES]
    entries = []
    for pid, part in ((pack_id, base), (pack_id + "-78", upper)):
        path = ROOT / "packs" / f"{pid}.json"
        if not part:
            if path.exists():
                path.unlink()
            continue
        sha, size = write_pack(path, version, part, note=f"KidOn güncelleme paketi {pid}", updated_at=now)
        if size > MAX_PACK_BYTES:  # uygulama daha büyük paketi reddeder (ContentService MAX_PACK_BYTES)
            path.unlink()
            sys.exit(f"paket çok büyük ({size} bayt > {MAX_PACK_BYTES}); kaynağı bölün")
        entries.append(({"id": pid, "url": f"packs/{pid}.json", "version": version, "sha256": sha, "bytes": size}, pid == pack_id))
    ids = {pack_id, pack_id + "-78"}
    for m, path, allow_upper in ((manifest, man_path, False), (manifest2, man2_path, True)):
        m["packs"] = [p for p in m["packs"] if p["id"] not in ids] + [e for e, is_base in entries if is_base or allow_upper]
        m["version"] = m.get("version", 0) + 1
        m["updatedAt"] = now
        m["retired"] = sorted(set(manifest.get("retired", [])) | set(manifest2.get("retired", [])))
        path.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    size = sum(e["bytes"] for e, _ in entries)
    known_path.write_text("\n".join(sorted(known)) + "\n", encoding="utf-8")
    from collections import Counter
    print(f"packs/{pack_id}.json: {len(tasks)} görev (atlanan tekrar: {skipped}), sürüm {version}, {size/1024:.0f} KB")
    print("  sınıf:", dict(Counter(t["grades"][0] for t in tasks)))
    print("  ders:", dict(Counter(t["subject"] for t in tasks)))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
