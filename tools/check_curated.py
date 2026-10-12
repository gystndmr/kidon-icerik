#!/usr/bin/env python3
"""KidOn JSONL görev denetleyicisi (content/src/YAZIM_KURALLARI.md).
Kullanım: python3 scripts/check_curated.py dosya.jsonl [...]
Hata varsa satır numarasıyla yazar ve 1 ile çıkar; özet istatistik basar."""
import json, re, sys, unicodedata
from collections import Counter

SUBJECTS = {"matematik", "turkce", "tarih", "bulmaca", "puzzle", "akil_oyunu", "bilim", "ingilizce"}
TYPES = {"multiple_choice", "matching", "ordering", "number_input"}
ALLOWED = {"subject", "skill", "difficulty", "type", "prompt", "emoji", "explanation", "hint",
           "options", "answer", "pairs", "items", "unit", "ages"}
AGES = {"3-4", "5-6", "7-8", "9-10", "11-12"}


def norm(s):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s)).strip().lower()


def js_len(s):
    """Uygulama (JavaScript) uzunluğu UTF-16 birimiyle ölçer; emoji vb. 2 birim sayılır."""
    return len(s.encode("utf-16-le")) // 2


def nonempty(v, maxlen=None):
    return isinstance(v, str) and v.strip() != "" and (maxlen is None or js_len(v) <= maxlen)


def check_item(o):
    e = []
    if not isinstance(o, dict):
        return ["nesne değil"]
    extra = set(o) - ALLOWED
    if extra:
        e.append(f"bilinmeyen alan: {sorted(extra)}")
    if o.get("subject") not in SUBJECTS:
        e.append("subject geçersiz")
    if not (isinstance(o.get("skill"), str) and re.fullmatch(r"[a-z0-9_]{2,40}", o["skill"])):
        e.append("skill snake_case ASCII olmalı")
    if o.get("difficulty") not in (1, 2, 3):
        e.append("difficulty 1-3")
    t = o.get("type")
    if t not in TYPES:
        e.append("type geçersiz")
    if not nonempty(o.get("prompt"), 600):
        e.append("prompt boş veya çok uzun")
    if not nonempty(o.get("explanation"), 400):
        e.append("explanation boş veya çok uzun")
    if "hint" in o and not nonempty(o["hint"], 200):
        e.append("hint geçersiz")
    if "emoji" in o and not nonempty(o["emoji"], 16):
        e.append("emoji geçersiz")
    if "ages" in o and not (isinstance(o["ages"], list) and o["ages"] and all(a in AGES for a in o["ages"])):
        e.append("ages geçersiz")
    if t == "multiple_choice":
        ops = o.get("options")
        if not (isinstance(ops, list) and 2 <= len(ops) <= 4 and all(nonempty(x, 160) for x in ops)):
            e.append("options 2-4 metin olmalı")
        elif len({norm(x) for x in ops}) != len(ops):
            e.append("seçenekler tekrar ediyor")
        elif not (isinstance(o.get("answer"), int) and 0 <= o["answer"] < len(ops)):
            e.append("answer seçenek sırası olmalı")
        for bad in ("hepsi", "hiçbiri"):
            if isinstance(ops, list) and any(bad in norm(str(x)) for x in ops):
                e.append(f"'{bad}' seçeneği kullanılmamalı")
    elif t == "matching":
        ps = o.get("pairs")
        if not (isinstance(ps, list) and 2 <= len(ps) <= 5 and all(isinstance(p, list) and len(p) == 2 and nonempty(p[0], 80) and nonempty(p[1], 80) for p in ps)):
            e.append("pairs 2-5 adet [sol,sağ] olmalı")
        else:
            if len({norm(p[0]) for p in ps}) != len(ps):
                e.append("sol değerler tekrar ediyor")
            if len({norm(p[1]) for p in ps}) != len(ps):
                e.append("sağ değerler tekrar ediyor")
    elif t == "ordering":
        it = o.get("items")
        if not (isinstance(it, list) and 3 <= len(it) <= 6 and all(nonempty(x, 80) for x in it)):
            e.append("items 3-6 metin olmalı")
        elif len({norm(x) for x in it}) != len(it):
            e.append("items tekrar ediyor")
    elif t == "number_input":
        a = o.get("answer")
        if not (isinstance(a, int) and not isinstance(a, bool) and -1000000 <= a <= 1000000):
            e.append("answer tam sayı olmalı")
        if "unit" in o and not nonempty(o["unit"], 12):
            e.append("unit geçersiz")
    return e


def main(paths):
    bad = 0
    for path in paths:
        seen = {}
        subj = Counter()
        types = Counter()
        n = 0
        with open(path, encoding="utf-8") as f:
            for ln, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    o = json.loads(line)
                except Exception as ex:
                    print(f"{path}:{ln}: JSON hatası: {ex}")
                    bad += 1
                    continue
                errs = check_item(o)
                key = norm(str(o.get("prompt", ""))) + "|" + json.dumps(o.get("options") or o.get("pairs") or o.get("items") or o.get("answer"), ensure_ascii=False)
                if key in seen:
                    errs.append(f"satır {seen[key]} ile aynı soru")
                seen[key] = ln
                for x in errs:
                    print(f"{path}:{ln}: {x}")
                bad += len(errs)
                n += 1
                subj[o.get("subject")] += 1
                types[o.get("type")] += 1
        print(f"{path}: {n} görev | " + ", ".join(f"{k}={v}" for k, v in sorted(subj.items(), key=lambda x: str(x[0]))) + " | " + ", ".join(f"{k}={v}" for k, v in types.items()))
    if bad:
        print(f"TOPLAM {bad} HATA")
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main(sys.argv[1:])
