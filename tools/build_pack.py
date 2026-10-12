#!/usr/bin/env python3
"""Yeni bir güncelleme paketi üretir ve manifest.json'u günceller.

Kullanım:  python3 tools/build_pack.py sources/2026-w42
  sources/<paket>/<sinif>.jsonl  (okul_oncesi, 1 … 6) — biçim: tools/YAZIM_KURALLARI.md
Çıktı:     packs/<paket>.json, manifest.json (sha256, sürüm), tools/bilinen_sorular.txt

- Aynı sınıfta daha önce yayımlanmış (uygulamaya gömülü veya önceki paketlerdeki) bir soru metni atlanır.
- Paket sürümü her derlemede manifest'teki en büyük sürümün bir fazlasıdır (uygulama yeni sürümü indirir).
- Hatalı bir görevi geri çekmek için kimliğini manifest.json → "retired" listesine ekleyin.
"""
import json, re, sys, unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from kidon_content import GRADES, read_jsonl, to_task, write_pack  # noqa: E402

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
    manifest = json.loads(man_path.read_text(encoding="utf-8"))
    version = max([BUNDLED_VERSION] + [p["version"] for p in manifest["packs"]]) + 1
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
            t = to_task(o, g, "u", version)
            if t["id"] in seen:
                skipped += 1
                continue
            seen.add(t["id"])
            known.add(key)
            tasks.append(t)
    if not tasks:
        sys.exit("pakette görev yok")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sha, size = write_pack(old, version, tasks, note=f"KidOn güncelleme paketi {pack_id}", updated_at=now)
    if size > MAX_PACK_BYTES:  # uygulama daha büyük paketi reddeder (ContentService MAX_PACK_BYTES)
        old.unlink()
        sys.exit(f"paket çok büyük ({size} bayt > {MAX_PACK_BYTES}); kaynağı bölün")
    manifest["packs"] = [p for p in manifest["packs"] if p["id"] != pack_id] + [
        {"id": pack_id, "url": f"packs/{pack_id}.json", "version": version, "sha256": sha, "bytes": size}
    ]
    manifest["version"] = manifest.get("version", 0) + 1
    manifest["updatedAt"] = now
    man_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    known_path.write_text("\n".join(sorted(known)) + "\n", encoding="utf-8")
    from collections import Counter
    print(f"packs/{pack_id}.json: {len(tasks)} görev (atlanan tekrar: {skipped}), sürüm {version}, {size/1024:.0f} KB")
    print("  sınıf:", dict(Counter(t["grades"][0] for t in tasks)))
    print("  ders:", dict(Counter(t["subject"] for t in tasks)))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
