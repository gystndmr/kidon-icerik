# KidOn elle yazılan görev biçimi (JSONL)

Her satır bir görevdir (tek satır JSON, UTF-8). Dosya: `content/src/curated/<sinif>.jsonl`
(`okul_oncesi`, `1` … `6`). Kimlik, sürüm, yaş grubu, sınıf alanlarını YAZMAYIN — derleme betiği ekler.

## Ortak alanlar
| Alan | Zorunlu | Açıklama |
|---|---|---|
| subject | evet | `matematik`, `turkce`, `tarih`, `bulmaca`, `puzzle`, `akil_oyunu`, `bilim`, `ingilizce` |
| skill | evet | küçük harf ASCII snake_case beceri etiketi (ör. `es_anlam`, `gezegenler`, `colors`) |
| difficulty | evet | 1 kolay, 2 orta, 3 zor (o sınıf içinde) |
| type | evet | `multiple_choice`, `matching`, `ordering`, `number_input` |
| prompt | evet | Çocuğa hitap eden soru (≤ 300 karakter; okuma parçası varsa ≤ 600) |
| emoji | hayır | Soruyu süsleyen TEK emoji |
| explanation | evet | Cevap sonrası gösterilen, 1–2 cümlelik, cesaretlendirici, öğretici açıklama |
| hint | hayır | Cevabı vermeyen ipucu |

## MEB bağlantısı (zorunlu: matematik, türkçe, bilim, tarih, ingilizce)
`"meb": {"s": "<ders>", "u": <ünite no>, "o": "<kazanım kodu>"}` — `tools/mufredat.json` içindeki o sınıfın ünitesi ve öğrenme çıktısı.
- `s`: `matematik`, `turkce`, `hayat_bilgisi` (1–3), `fen` (3–8), `sosyal` (4–7), `inkilap` (8), `ingilizce` (2–8), `okul_oncesi` (u = alan no).
- `o` emin değilseniz yazılmaz. O sınıfın programında olmayan konu YAZILMAZ.
- Yeni görevler, o haftalarda okulda işlenen ünitelere (mufredat.json → `weeks`) öncelik verecek şekilde seçilir.
- 7. ve 8. sınıf (LGS) desteklenir: 4 seçenekli, tek doğru cevaplı, LGS hazırlık tarzı sorular.

## Türler
- **multiple_choice**: `"options": [3 veya 4 metin]`, `"answer": doğru seçeneğin 0'dan başlayan sırası`. Seçenekler benzersiz, makul çeldiriciler; "hepsi / hiçbiri" yok. Sıra önemli değil (betik karıştırır).
- **matching**: `"pairs": [["sol","sağ"], …]` 3–4 çift; sol değerler de sağ değerler de benzersiz.
- **ordering**: `"items": [...]` 3–5 öğe **DOĞRU SIRADA** yazılır (betik karıştırır). Prompt ölçütü açıkça söyler ("küçükten büyüğe", "olayların oluş sırasına göre"). Tek ve tartışmasız bir doğru sıra olmalı. Öğeler benzersiz.
- **number_input**: `"answer": tam sayı (0–1000000)`, isteğe bağlı `"unit": "TL"`. Yalnızca tek ve kesin sayısal cevabı olan sorular.

## Örnekler
```
{"subject":"turkce","skill":"zit_anlam","difficulty":1,"type":"multiple_choice","prompt":"“Uzun” kelimesinin zıt anlamlısı hangisi?","emoji":"📏","options":["Kısa","Geniş","Yüksek"],"answer":0,"explanation":"Uzun ↔ kısa zıt anlamlıdır."}
{"subject":"ingilizce","skill":"animals","difficulty":1,"type":"matching","prompt":"İngilizce kelimeyi Türkçesiyle eşleştir.","emoji":"🐾","pairs":[["cat","kedi"],["dog","köpek"],["bird","kuş"]],"explanation":"cat = kedi, dog = köpek, bird = kuş."}
{"subject":"bilim","skill":"bitki_buyume","difficulty":2,"type":"ordering","prompt":"Bir bitkinin büyüme aşamalarını sıraya koy.","emoji":"🌱","items":["Tohum","Filiz","Fide","Çiçekli bitki"],"explanation":"Tohum çimlenir, filiz çıkar, fide olur ve sonra çiçek açar."}
{"subject":"matematik","skill":"problem","difficulty":2,"type":"number_input","prompt":"Sınıfta 14 kız ve 13 erkek öğrenci var. Sınıfta toplam kaç öğrenci var?","emoji":"🏫","answer":27,"explanation":"14 + 13 = 27 öğrenci."}
```

## İçerik ilkeleri
- Türkiye'deki MEB müfredatının o sınıf düzeyine uygun konular; tamamen ÖZGÜN metin (kitap/şarkı/şiir alıntısı yok).
- Bilgi kesin ve güncel olmalı; tartışmalı, siyasi, dini veya korkutucu içerik yok. Tarih: Atatürk, Cumhuriyet, Milli Mücadele, ilk Türk devletleri, Osmanlı'nın temel bilgileri, ilk uygarlıklar, millî bayramlar, sembollerimiz — tarafsız ve olgusal.
- Cinsiyet/meslek kalıp yargısı yok; isimler çeşitli (Ayşe, Mehmet, Elif, Can, Zeynep, Emir, Defne, Ali…).
- Okul öncesi: kısa, somut, emoji destekli (sesli okunacak). Okuma bilmeyen çocuk için seçenekler kısa olsun.
- Açıklamalar asla küçümseyici değil ("Harika deneme!" değil; öğretici cümle).
- Aynı soruyu iki kez yazmayın.

Kontrol: `python3 scripts/check_curated.py content/src/curated/<sinif>.jsonl`
