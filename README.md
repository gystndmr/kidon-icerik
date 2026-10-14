# kidon-icerik

KidOn uygulamasının **güncelleme görev paketleri**. Uygulama manifest dosyasını günde en fazla bir kez okur,
yeni paketleri indirir, sha256 ve şema doğrulamasından geçirir ve uygulamaya gömülü görevlerin üzerine ekler.

- `manifest.json`: uygulama 1.0.x (okul öncesi–6. sınıf).
- `manifest-v2.json`: uygulama 1.1+ (okul öncesi–8. sınıf; 7-8. sınıf paketleri `-78` ekiyle ayrıdır).
- Görevler MEB müfredatına bağlıdır (`meb` alanı: ders, ünite, kazanım). Müfredat: `tools/mufredat.json`; eski becerilerin ünite eşlemesi: `tools/esleme/`.

- Burada **yalnızca soru içeriği** bulunur. Çocuk verisi, kullanım bilgisi veya kişisel veri bu depoya hiçbir zaman yazılmaz; uygulama buraya hiçbir şey göndermez.
- Depo **herkese açık** olmalıdır (uygulama kimlik doğrulaması olmadan okur).

## Yeni paket ekleme
1. `sources/<paket-adı>/<sinif>.jsonl` dosyaları yazılır (`okul_oncesi`, `1` … `8`). Biçim: `tools/YAZIM_KURALLARI.md`. Okul derslerinde her görevde `meb` alanı olmalı.
2. Denetim: `python3 tools/check_curated.py sources/<paket-adı>/*.jsonl`
3. Paket: `python3 tools/build_pack.py sources/<paket-adı>` → `packs/<paket-adı>.json` (+ `-78`) ve iki manifest güncellenir.
4. Commit + push. Uygulamalar 20 saat içinde (veya Ayarlar › “Şimdi kontrol et”) alır.

## Hatalı soruyu geri çekme
Görevin kimliğini (`u-3-…`) `manifest.json` → `retired` listesine ekleyip paketi yeniden derleyin (iki manifest birleştirilir) ve push edin; uygulamalarda pasifleşir.
Bir paketi tamamen geri çekmek için `packs` listesinden çıkarın (uygulama önbellekten siler).

Haftalık otomatik paketler `sources/<yıl>-w<hafta>/` adıyla eklenir.
