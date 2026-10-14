# KidOn — Gizlilik Politikası / Privacy Policy

**Yürürlük tarihi / Effective date:** 14 Ekim 2026  
**Geliştirici / Developer:** Gıyasettin Demir · **İletişim / Contact:** info@nexeralive.com

## Türkçe

KidOn, ebeveynin kurduğu ve yönettiği bir eğitim ve ebeveyn kontrolü uygulamasıdır. Çocuk yaşına ve sınıfına uygun görevleri çözer, ebeveynin belirlediği kurala göre ekran süresi kazanır.

**Varsayılan olarak topladığımız veri: Yok.** KidOn hesap oluşturmaz; reklam, analitik, izleme (tracking), konum, kişi listesi, kamera, mikrofon veya fotoğraf kullanmaz. Ebeveyn aşağıdaki isteğe bağlı "Ebeveyn telefonu" özelliğini açmadıkça hiçbir veri cihazdan çıkmaz.

**Yalnızca cihazınızda saklananlar:**
- Çocuk profili: takma ad, avatar, yaş grubu ve sınıf (gerçek ad, doğum tarihi, okul veya fotoğraf istenmez),
- görev cevapları ve ilerleme, ödül kuralları, kazanılan/kullanılan süreler,
- ebeveyn PIN'i (yalnızca tek yönlü özet hâlinde, cihazın güvenli anahtar zincirinde),
- Ekran Süresi seçimleri: Apple bu seçimleri KidOn'a gizli belirteçler olarak verir; KidOn uygulama adlarını bile göremez.

**Ekran Süresi (Apple FamilyControls, ManagedSettings, DeviceActivity):** yalnızca ebeveyn kontrolü sağlamak için — uygulamaları kilitlemek, ödül süresini ölçmek ve süre bitince yeniden kilitlemek — kullanılır. Bu bilgiler cihazdan çıkmaz, paylaşılmaz, satılmaz.

**İnternet bağlantısı:** KidOn yeni görev paketlerini günde en fazla bir kez herkese açık bir GitHub deposundan (raw.githubusercontent.com) indirir. Bu istekte kişisel veri gönderilmez; GitHub, her web isteğinde olduğu gibi IP adresi gibi teknik bilgileri kendi gizlilik politikasına göre işleyebilir. Ebeveyn isterse kendi içerik adresini ekleyebilir; aynı kural geçerlidir. Otomatik indirme Ayarlar'dan kapatılabilir.

**İsteğe bağlı "Ebeveyn telefonu" (sürüm 1.1 ve sonrası):** Ebeveyn, çocuğun telefonunda PIN ile girip bir eşleştirme kodu alır ve bu kodu kendi telefonundaki KidOn'a girerse, çocuğun telefonu şu özeti sunucumuza gönderir: çocuğun takma adı, avatarı ve sınıfı; günlük/haftalık çözülen ve doğru görev sayıları; derslere göre doğruluk oranları; zorlandığı konu adları; kazanılan, kullanılan ve bekleyen süre; koruma durumu (açık/kapalı, mola, koruma izninin kapatılması). Ebeveyn telefonundan gönderilen komutlar (ek süre, ödülü bitir, kilitle, mola) da saklanır. Gerçek ad, konum, ekran içeriği, tek tek soru cevapları veya cihaz tanımlayıcıları gönderilmez. Hesap, e-posta veya telefon numarası istenmez; her cihaz rastgele, anonim bir oturum kimliği kullanır. Veriler Supabase (AB – Frankfurt) üzerinde, yalnızca eşleştirilmiş cihazların okuyabileceği şekilde saklanır; reklam veya başka bir amaçla kullanılmaz, satılmaz. Komut kayıtları 30 gün sonra silinir. Çocuğun telefonunda "Bağlantıyı tamamen kaldır" denildiğinde sunucudaki tüm veriler hemen silinir; ebeveyn telefonu takipten istediği an çıkabilir.

**Android – Erişilebilirlik izni:** Android'de uygulama kilidi için ebeveynin açık onayıyla Erişilebilirlik hizmeti kullanılır. KidOn bu izinle yalnızca o an öne gelen uygulamanın paket adını görür; ekrandaki yazıları, mesajları, şifreleri veya yazılanları okumaz, kaydetmez ve hiçbir yere göndermez. Kullanım erişimi izni yalnızca ödül uygulamasının açık kaldığı süreyi ölçmek için kullanılır ve cihazdan çıkmaz.

**Bildirimler:** yalnızca cihaz içi (yerel) bildirimlerdir ("Süren bitti").

**Silme:** Bir çocuk profilini ve tüm kayıtlarını Ebeveyn › Veri yönetimi'nden silebilirsiniz. Uygulamayı silmek tüm verileri siler (PIN özeti cihazın anahtar zincirinde kalabilir). Ekran Süresi iznini Ayarlar › Ekran Süresi'nden istediğiniz an kaldırabilirsiniz.

**Çocuklar:** Uygulama ebeveyn veya veli tarafından kurulur ve yönetilir. "Ebeveyn telefonu" kapalıyken çocuklardan hiçbir kişisel veri toplanmaz. Bu özellik yalnızca ebeveynin PIN'i ve açık eylemiyle açılır; paylaşılan özet, ebeveynin kendi çocuğunu takip etmesi amacıyla ve en az veri ilkesiyle işlenir (KVKK, GDPR, COPPA). Ebeveyn verilerin silinmesini istediği an uygulamadan yapabilir veya info@nexeralive.com adresine yazabilir.

**Değişiklikler:** Bu politika değişirse bu sayfada yayımlanır ve yürürlük tarihi güncellenir.

## English

KidOn is an education and parental-control app set up and managed by a parent. A child solves age-appropriate tasks and earns screen time according to the parent's rule.

**Data we collect by default: None.** No accounts, ads, analytics, tracking, location, contacts, camera, microphone or photos. Nothing leaves the device unless the parent turns on the optional "Parent phone" feature.

**Stored only on your device:** the child's nickname, avatar, age group and grade; task answers and progress; reward rules and minutes; the parent PIN (only as a one-way hash in the device Keychain); and Screen Time selections, which Apple provides as opaque tokens (KidOn cannot even see app names).

**Screen Time APIs** (FamilyControls, ManagedSettings, DeviceActivity) are used solely to provide parental controls. This data never leaves the device and is never shared or sold.

**Network:** KidOn downloads new question packs at most once a day from a public GitHub repository (raw.githubusercontent.com). No personal data is sent; GitHub may process technical data such as IP addresses under its own policy. Automatic downloads can be turned off in Settings.

**Optional "Parent phone" (version 1.1+):** if the parent (behind the PIN) pairs their own phone with a one-time code, the child's device uploads a summary to our server: the child's nickname, avatar and grade; daily/weekly counts of solved and correct tasks; accuracy per subject; names of difficult topics; earned, used and pending minutes; protection status. Parent commands (extra time, end reward, lock, pause) are stored too. No real names, location, screen content, individual answers or device identifiers are sent; no account, email or phone number is required (anonymous random session IDs). Data is stored on Supabase (EU – Frankfurt), readable only by the paired devices, never used for ads or sold. Commands are deleted after 30 days; "Remove connection" on the child's device deletes all server data immediately.

**Android Accessibility:** on Android, app locking uses the Accessibility service with the parent's explicit consent. KidOn only sees the package name of the app coming to the foreground; it does not read, store or transmit screen text, messages, passwords or typed input. Usage access is used only to measure reward-app time and stays on the device.

**Notifications** are local only. **Deletion:** delete a child profile in Parent › Data; deleting the app removes all data; revoke Screen Time access any time in iOS Settings › Screen Time. **Children:** the app is set up and managed by a parent/guardian. With "Parent phone" off, no personal data is collected from children; when the parent turns it on, the minimal summary above is processed only so the parent can follow their own child (COPPA/GDPR/KVKK), and can be deleted at any time. Contact: info@nexeralive.com
