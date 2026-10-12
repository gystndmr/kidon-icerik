# kidon-icerik

KidOn uygulamasının **güncelleme görev paketleri**. Uygulama `manifest.json` dosyasını günde en fazla bir kez okur,
yeni paketleri indirir, sha256 ve şema doğrulamasından geçirir ve uygulamaya gömülü ~6.000 görevin üzerine ekler.

- Burada **yalnızca soru içeriği** bulunur. Çocuk verisi, kullanım bilgisi veya kişisel veri bu depoya hiçbir zaman yazılmaz; uygulama buraya hiçbir şey göndermez.
- Depo **herkese açık** olmalıdır (uygulama kimlik doğrulaması olmadan okur).

## Yeni paket ekleme
1. `sources/<paket-adı>/<sinif>.jsonl` dosyaları yazılır (`okul_oncesi`, `1` … `6`). Biçim: `tools/YAZIM_KURALLARI.md`.
2. Denetim: `python3 tools/check_curated.py sources/<paket-adı>/*.jsonl`
3. Paket: `python3 tools/build_pack.py sources/<paket-adı>` → `packs/<paket-adı>.json` + `manifest.json` güncellenir.
4. Commit + push. Uygulamalar 20 saat içinde (veya Ayarlar › “Şimdi kontrol et”) alır.

## Hatalı soruyu geri çekme
Görevin kimliğini (`u-3-…`) `manifest.json` → `retired` listesine ekleyip push edin; uygulamalarda pasifleşir.
Bir paketi tamamen geri çekmek için `packs` listesinden çıkarın (uygulama önbellekten siler).

Haftalık otomatik paketler `sources/<yıl>-w<hafta>/` adıyla eklenir.
