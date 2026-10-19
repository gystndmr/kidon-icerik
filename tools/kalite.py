#!/usr/bin/env python3
"""Kendini geliştiren içerik: isimsiz soru istatistiklerinden kalite raporu ve düzeltmeler.

Kullanım:
  python3 tools/kalite.py analiz
      veri/soru_istatistik.json (her pazar GitHub Actions ile sunucudan çekilir) + bütün görevler
      (tools/gomulu/tasks.json.gz = uygulamaya gömülü görevler, packs/*.json = güncelleme paketleri) →
      veri/kalite_raporu.md (okunur özet) ve veri/adaylar.json (haftalık görevin inceleyeceği liste).

  python3 tools/kalite.py uygula [--geri-cek id1,id2,...] [--zorluk-otomatik]
      --geri-cek: incelemede GERÇEKTEN hatalı bulunan görevleri iki manifestin "retired" listesine ekler.
      --zorluk-otomatik: adaylar.json'daki zorluk önerilerini manifest-v2.json → "adjust" alanına yazar
                         (yalnızca 1.1+ uygulamalar okur; 1.0.x yok sayar).

Kurallar (eşikler aşağıda): istatistik yalnızca görevin GÜNCEL içerik sürümü için sayılır; az veriyle
(SHOWN_MIN altı) karar verilmez. Geri çekme her zaman bir insanın/denetçinin soruyu okuyup hatayı
doğrulamasından sonra yapılır; bu betik kendi başına soru geri çekmez.
"""
import gzip
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERI = ROOT / "veri"
SHOWN_MIN = 20          # zorluk/anahtar kararları için en az ilk deneme
REPORT_MIN = 2          # incelemeye almak için toplam bildirim (cevap_yanlis/uygunsuz için 1 yeter)
UNIT_MIN = 40           # ünite zayıflığı için en az ilk deneme
EASY, HARD = 0.90, 0.40 # ilk denemede doğru oranı eşikleri


def load_tasks():
    tasks = {}
    gz = ROOT / "tools" / "gomulu" / "tasks.json.gz"
    if gz.exists():
        for t in json.loads(gzip.decompress(gz.read_bytes()))["tasks"]:
            tasks[t["id"]] = {**t, "_kaynak": "gömülü"}
    for p in sorted((ROOT / "packs").glob("*.json")):
        for t in json.loads(p.read_text(encoding="utf-8"))["tasks"]:
            cur = tasks.get(t["id"])
            if not cur or t["contentVersion"] >= cur["contentVersion"]:
                tasks[t["id"]] = {**t, "_kaynak": p.stem}
    return tasks


def manifests():
    m1 = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    m2 = json.loads((ROOT / "manifest-v2.json").read_text(encoding="utf-8"))
    return m1, m2


def correct_text(t):
    a = t.get("answer", {})
    if a.get("kind") == "option":
        o = next((o for o in t.get("options", []) if o["id"] == a.get("optionId")), None)
        return f'{a.get("optionId")}) {o["text"] if o else "?"}'
    if a.get("kind") == "number":
        return str(a.get("value"))
    if a.get("kind") == "order":
        return " > ".join(a.get("order", []))
    return a.get("kind", "?")


def option_text(t, key):
    o = next((o for o in t.get("options", []) or [] if o["id"] == key), None)
    return f"{key}) {o['text']}" if o else key


def sinif(g):
    return "okul öncesi" if g == "okul_oncesi" else f"{g}. sınıf"


def suggest_difficulty(rate):
    return 1 if rate >= EASY else 3 if rate < HARD else 2


def analiz():
    src = VERI / "soru_istatistik.json"
    if not src.exists():
        sys.exit("veri/soru_istatistik.json yok (GitHub Actions 'Soru istatistikleri' iş akışı henüz çalışmadı)")
    data = json.loads(src.read_text(encoding="utf-8"))
    tasks = load_tasks()
    m1, m2 = manifests()
    retired = set(m1.get("retired", [])) | set(m2.get("retired", []))
    adjust = m2.get("adjust", {})

    # Güncel sürüm + bütün sınıflar birleşik (görev hangi sınıfta gösterildiyse)
    agg = defaultdict(lambda: {"n": 0, "c": 0, "l": 0, "w": defaultdict(int), "g": defaultdict(int), "b": 0})
    for s in data.get("stats", []):
        t = tasks.get(s["t"])
        if not t or s["v"] != t["contentVersion"] or s["t"] in retired:
            continue
        a = agg[s["t"]]
        a["n"] += s["n"]; a["c"] += s["c"]; a["l"] += s["l"]; a["b"] += s.get("b", 0)
        a["g"][s["g"]] += s["n"]
        for k, v in (s.get("w") or {}).items():
            a["w"][k] += v
    reports = defaultdict(lambda: defaultdict(int))
    for r in data.get("reports", []):
        t = tasks.get(r["t"])
        if not t or r["v"] != t["contentVersion"] or r["t"] in retired:
            continue
        reports[r["t"]][r["r"]] += r["n"]

    incele, anahtar, zorluk, birimler = [], [], [], defaultdict(lambda: {"n": 0, "c": 0, "gorev": 0})
    for tid, rs in reports.items():
        total = sum(rs.values())
        if total >= REPORT_MIN or rs.get("cevap_yanlis", 0) + rs.get("uygunsuz", 0) >= 1:
            incele.append({"id": tid, "bildirim": dict(rs), "istatistik": _stat(agg.get(tid))})
    for tid, a in agg.items():
        t = tasks[tid]
        if a["n"] >= SHOWN_MIN:
            rate = a["c"] / a["n"]
            # Anahtar şüphesi: aynı yanlış cevap doğru cevaptan daha sık seçilmiş
            if a["w"]:
                top_k, top_v = max(a["w"].items(), key=lambda kv: kv[1])
                if top_v > a["c"] and top_v >= 6:
                    anahtar.append({"id": tid, "dogru_sayilan": correct_text(t), "en_sik_yanlis": option_text(t, top_k),
                                    "en_sik_yanlis_sayi": top_v, "ilk_deneme": a["n"], "ilk_dogru": a["c"]})
            want = suggest_difficulty(rate)
            cur = adjust.get(tid, {}).get("difficulty", t["difficulty"])
            if want != cur:
                zorluk.append({"id": tid, "eski": cur, "yeni": want, "oran": round(rate, 3), "n": a["n"]})
        meb = t.get("meb")
        if meb:
            for g, n in a["g"].items():
                key = (g, meb["s"], meb["u"])
                share = n / a["n"] if a["n"] else 0
                birimler[key]["n"] += n
                birimler[key]["c"] += round(a["c"] * share)
                birimler[key]["gorev"] += 1

    zayif = sorted(
        ({"sinif": g, "ders": s, "unite": u, "oran": round(v["c"] / v["n"], 3), "ilk_deneme": v["n"], "gorev": v["gorev"]}
         for (g, s, u), v in birimler.items() if v["n"] >= UNIT_MIN),
        key=lambda x: x["oran"])
    out = {
        "olusturma": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "istatistik_tarihi": data.get("generated_at"),
        "toplam": {"gorev": len(agg), "ilk_deneme": sum(a["n"] for a in agg.values()),
                   "ilk_dogru": sum(a["c"] for a in agg.values()), "bildirim": sum(sum(r.values()) for r in reports.values())},
        "incele_bildirim": sorted(incele, key=lambda x: -sum(x["bildirim"].values())),
        "anahtar_suphesi": sorted(anahtar, key=lambda x: -x["en_sik_yanlis_sayi"]),
        "zorluk_onerisi": zorluk,
        "zayif_uniteler": zayif[:25],
    }
    VERI.mkdir(exist_ok=True)
    (VERI / "adaylar.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (VERI / "kalite_raporu.md").write_text(_rapor(out, tasks), encoding="utf-8")
    print(f"görev: {out['toplam']['gorev']}, ilk deneme: {out['toplam']['ilk_deneme']}, bildirim: {out['toplam']['bildirim']}; "
          f"incele: {len(incele)}, anahtar şüphesi: {len(anahtar)}, zorluk önerisi: {len(zorluk)}, zayıf ünite: {len(zayif)}")


def _stat(a):
    if not a:
        return None
    return {"ilk_deneme": a["n"], "ilk_dogru": a["c"], "sonra_dogru": a["l"], "yanlislar": dict(a["w"])}


def _rapor(o, tasks):
    t = o["toplam"]
    oran = f"{t['ilk_dogru'] / t['ilk_deneme']:.0%}" if t["ilk_deneme"] else "-"
    L = [f"# KidOn soru kalite raporu", "", f"İstatistik: {o['istatistik_tarihi']} · {t['gorev']} görev, {t['ilk_deneme']} ilk deneme (ilk denemede doğru {oran}), {t['bildirim']} hata bildirimi.", ""]
    L += ["## İncelenecek (çocuk/ebeveyn bildirdi)", ""]
    for x in o["incele_bildirim"][:60]:
        tk = tasks[x["id"]]
        L.append(f"- `{x['id']}` ({sinif(tk['grades'][0])}, {tk['subject']}) {x['bildirim']} — {tk['prompt'][:120]!r} · doğru: {correct_text(tk)}")
    L += ["", "## Cevap anahtarı şüphesi (bir yanlış seçenek doğrudan daha sık seçilmiş)", ""]
    for x in o["anahtar_suphesi"][:60]:
        tk = tasks[x["id"]]
        L.append(f"- `{x['id']}` {tk['prompt'][:120]!r} · doğru sayılan {x['dogru_sayilan']} ({x['ilk_dogru']}/{x['ilk_deneme']}) · en sık yanlış {x['en_sik_yanlis']} ({x['en_sik_yanlis_sayi']})")
    L += ["", f"## Zorluk önerileri ({len(o['zorluk_onerisi'])})", ""]
    for x in o["zorluk_onerisi"][:40]:
        L.append(f"- `{x['id']}` {x['eski']} → {x['yeni']} (ilk denemede doğru {x['oran']:.0%}, n={x['n']})")
    L += ["", "## Çocukların zorlandığı üniteler (yeni sorular buraya)", ""]
    for x in o["zayif_uniteler"]:
        L.append(f"- {sinif(x['sinif'])} {x['ders']} ünite {x['unite']}: ilk denemede doğru {x['oran']:.0%} ({x['ilk_deneme']} deneme, {x['gorev']} görev)")
    return "\n".join(L) + "\n"


def uygula(args):
    retire = []
    auto = "--zorluk-otomatik" in args
    if "--geri-cek" in args:
        i = args.index("--geri-cek")
        retire = [x.strip() for x in args[i + 1].split(",") if x.strip()]
    tasks = load_tasks()
    unknown = [x for x in retire if x not in tasks]
    if unknown:
        sys.exit(f"bilinmeyen görev kimliği: {unknown}")
    m1, m2 = manifests()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    changed = False
    if retire:
        r = sorted(set(m1.get("retired", [])) | set(m2.get("retired", [])) | set(retire))
        m1["retired"] = r
        m2["retired"] = r
        changed = True
    if auto:
        ad = json.loads((VERI / "adaylar.json").read_text(encoding="utf-8"))
        adj = dict(m2.get("adjust", {}))
        n = 0
        for z in ad["zorluk_onerisi"]:
            base = tasks[z["id"]]["difficulty"]
            if z["yeni"] == base:
                adj.pop(z["id"], None)
            else:
                adj[z["id"]] = {"difficulty": z["yeni"]}
            n += 1
        if n:
            m2["adjust"] = dict(sorted(adj.items()))
            changed = True
        print(f"zorluk düzeltmesi: {n} görev (toplam {len(m2.get('adjust', {}))})")
    if not changed:
        print("değişiklik yok")
        return
    for m, name, touched in ((m1, "manifest.json", bool(retire)), (m2, "manifest-v2.json", True)):
        if not touched:
            continue
        m["version"] = m.get("version", 0) + 1
        m["updatedAt"] = now
        (ROOT / name).write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"geri çekilen: {len(retire)}; manifestler güncellendi")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("analiz", "uygula"):
        sys.exit(__doc__)
    analiz() if sys.argv[1] == "analiz" else uygula(sys.argv[2:])
