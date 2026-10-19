# kidon-icerik

KidOn uygulamasının **güncelleme görev paketleri**. Uygulama manifest dosyasını günde en fazla bir kez okur,
yeni paketleri indirir, sha256 ve şema doğrulamasından geçirir ve uygulamaya gömülü görevlerin üzerine ekler.

- `manifest.json`: uygulama 1.0.x (okul öncesi–6. sınıf).
- `manifest-v2.json`: uygulama 1.1+ (okul öncesi–8. sınıf; 7-8. sınıf paketleri `-78` ekiyle ayrıdır).
- Görevler MEB müfredatına bağlıdır (`meb` alanı: ders, ünite, kazanım). Müfredat: `tools/mufredat.json`; eski becerilerin ünite eşlemesi: `tools/esleme/`.

- Burada **yalnızca soru içeriği** ve soruların isimsiz kalite sayıları (`veri/`) bulunur. Çocuk verisi veya kişisel veri bu depoya hiçbir zaman yazılmaz.
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

## Kendini geliştiren içerik
1. Uygulama (1.1+) ebeveyn izin verdiyse günde bir kez **isimsiz** soru istatistiği gönderir: görev kimliği, sınıf, içerik sürümü, ilk denemede kaç kez gösterildi / doğru yapıldı, sonradan doğru, en sık 3 yanlış cevap. Ayrıca çocuk "🚩 Bu soruda hata var" ile soru bildirebilir (görev kimliği + sebep). Ad, profil, cihaz, zaman bilgisi gönderilmez. Sunucu: `sunucu/istatistik.sql`.
2. Her pazar gecesi `.github/workflows/istatistik.yml` toplamları `veri/soru_istatistik.json`'a çeker ve `python3 tools/kalite.py analiz` ile `veri/kalite_raporu.md` + `veri/adaylar.json` üretir.
3. Pazartesi haftalık görev: bildirilen ve cevap anahtarı şüpheli soruları okur, gerçekten hatalı olanları `python3 tools/kalite.py uygula --geri-cek id1,id2` ile geri çeker (gerekirse düzeltilmiş hâlini yeni pakete yazar), `--zorluk-otomatik` ile zorluk düzeltmelerini `manifest-v2.json` → `adjust`'a yazar ve yeni soruları çocukların zorlandığı ünitelere ağırlık vererek üretir.
4. `tools/gomulu/tasks.json.gz`: uygulamaya gömülü görevlerin kopyası (analiz için). Uygulamanın gömülü içeriği değişince güncellenmeli.
