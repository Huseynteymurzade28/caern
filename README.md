# CAERN — Yapay Zeka Destekli Uydu ve Drone Görüntüsü Değişim Tespiti Platformu

---

## README Dosyası Hakkında

### Amacı
README dosyası, bir yazılım projesinin ilk ve en önemli belgesidir. Projeye yeni katılan geliştiricilere, kullanıcılara veya değerlendiricilere projenin ne yaptığını, nasıl çalıştığını ve nasıl kullanılacağını açıklar. GitHub gibi platformlarda depo ana sayfasında otomatik olarak görüntülenir; bu nedenle projenin "vitrin" belgesi işlevi görür.

### Yazılım Projelerinde Önemi
- **İlk izlenim:** Projeyi inceleyen herkes önce README'yi okur; iyi hazırlanmış bir README projenin kalitesi hakkında güçlü bir sinyal verir.
- **Hızlı başlangıç:** Kurulum ve kullanım adımları sayesinde yeni geliştiriciler projeyi dakikalar içinde çalıştırabilir.
- **İş birliği kolaylığı:** Katkı rehberi, projeye dışarıdan destek vermeyi standart hale getirir.
- **Sürdürülebilirlik:** Belgelenmiş projeler, yazarı olmasa bile yaşamaya devam eder.
- **Profesyonellik:** Açık kaynak topluluğunda ve iş başvurularında README, portföyün ayrılmaz parçasıdır.

---

## Proje Adı

**CAERN** *(Change Analysis and Environmental Recognition Network)*

---

## Proje Tanımı

CAERN, uydu ve drone görüntüleri üzerinde yapay zeka destekli arazi değişim tespiti yapan tam yığın (full-stack) bir coğrafi bilgi sistemi platformudur. Kullanıcılar bir bölgeye ait "önce" ve "sonra" görüntü çiftini yükler; sistem bu iki görüntüyü otomatik olarak hizalar, farklılaşan alanları tespit eder ve her değişim bölgesini kategorize eder. Sonuçlar; etkileşimli bir harita, metrik paneli ve indirilebilir raporlar (CSV/PDF) biçiminde sunulur.

Platform; kentsel dönüşüm izleme, doğal afet hasar tespiti, tarımsal alan değişimi analizi ve çevre koruma çalışmaları gibi geniş bir kullanım alanını hedeflemektedir.

---

## Özellikler

| # | Özellik | Açıklama |
|---|---|---|
| 1 | **Değişim Tespiti** | NDI tabanlı klasik boru hattı veya YOLOv8 + SAM ile iki görüntü arasındaki değişimler piksel hassasiyetiyle tespit edilir |
| 2 | **Otomatik Kategorilendirme** | Tespit edilen her bölge dört sınıftan birine atanır: `YENİ_YAPI`, `YIKIM`, `VEJETASYON`, `YÜZEY_DEĞİŞİMİ` |
| 3 | **Etkileşimli Harita** | Leaflet tabanlı karanlık tema haritada katman açma/kapama, opaklık kontrolü ve tıklanabilir bölge bilgi pencereleri |
| 4 | **Metrik Paneli** | Toplam değişim alanı (m²), değişim yüzdesi, güven skoru, kategori bazlı çubuk grafik ve halka göstergesi |
| 5 | **Raporlama** | CSV ve PDF dışa aktarma (kapak, özet, metrik tablosu, gömülü harita ekran görüntüsü, nesne listesi, metodoloji bölümü) |
| 6 | **Gerçek Zamanlı İlerleme** | Analiz aşamaları (Yükleme → Ön İşleme → Tespit → Sınıflandırma → Tamamlama) SSE akışıyla tarayıcıya iletilir |
| 7 | **JWT Kimlik Doğrulama & RBAC** | Giriş/token yenileme akışı ile rol tabanlı erişim denetimi |
| 8 | **GPU Desteği** | NVIDIA GPU varsa otomatik olarak kullanılır; yoksa CPU moduna geçer |

---

## Kullanılan Teknolojiler

### Backend

| Teknoloji | Sürüm | Kullanım Amacı |
|---|---|---|
| Python | 3.11 | Ana programlama dili |
| FastAPI | 0.110+ | REST API ve SSE endpoint'leri |
| Celery | 5.x | Asenkron iş kuyruğu (analiz görevleri) |
| SQLAlchemy | 2.x (async) | ORM katmanı |
| Alembic | — | Veritabanı migrasyon yönetimi |
| Pydantic-Settings | — | Ortam değişkeni yönetimi |
| WeasyPrint / ReportLab | — | PDF rapor üretimi |
| Jinja2 | — | Rapor şablonlama |

### Yapay Zeka / Görüntü İşleme

| Teknoloji | Kullanım Amacı |
|---|---|
| YOLOv8 (Ultralytics) | Nesne tespiti |
| Segment Anything Model (SAM) | Hassas bölge segmentasyonu |
| OpenCV | Morfolojik görüntü işleme |
| Rasterio / GDAL | Coğrafi referanslı görüntü hizalama, CRS dönüşümü |
| SciPy | Bağlı bileşen etiketleme |

### Frontend

| Teknoloji | Kullanım Amacı |
|---|---|
| React 18 + TypeScript | Kullanıcı arayüzü |
| Vite | Geliştirme sunucusu ve derleme |
| Tailwind CSS | Stil sistemi (karanlık tema) |
| Leaflet.js | Etkileşimli harita |
| Recharts | Grafik ve göstergeler |
| Zustand | Global durum yönetimi |
| React Query | Sunucu durum yönetimi ve önbellekleme |

### Veritabanı ve Depolama

| Teknoloji | Kullanım Amacı |
|---|---|
| PostgreSQL 15 + PostGIS 3.4 | İlişkisel veritabanı ve coğrafi sorgu desteği |
| Redis 7 | Celery mesaj aracısı ve önbellek |
| MinIO | S3 uyumlu nesne deposu (görüntü dosyaları) |

### Altyapı

| Teknoloji | Kullanım Amacı |
|---|---|
| Docker Compose | Servis orkestrasyon |
| nginx | TLS sonlandırma ve ters proxy |

### Mimari Genel Bakış

```
Tarayıcı (React + Leaflet)
        │  HTTPS
        ▼
    nginx (TLS / Reverse Proxy)
        │                │
        ▼                ▼
  FastAPI (API)     React SPA (statik)
        │
   ┌────┴────┐
   │         │
Redis     PostgreSQL + PostGIS
   │
Celery Worker
   │
MinIO (görüntü depolama)
```

---

## Kurulum Adımları

### Gereksinimler

| Gereksinim | Sürüm |
|---|---|
| Docker | 24+ |
| Docker Compose | v2 (Docker Desktop ile birlikte gelir) |
| `make` | herhangi bir sürüm |
| `openssl` | herhangi bir sürüm |

> **GPU (isteğe bağlı):** NVIDIA GPU kullanıyorsanız `nvidia-container-toolkit` kurulumu yapın ve `docker-compose.yml` dosyasındaki `worker` servisindeki `deploy.resources` bloğunu yorum dışı bırakın. GPU yoksa sistem otomatik olarak CPU moduna geçer.

---

### Adım 1 — Depoyu Klonlayın

```bash
git clone https://github.com/<kullanici-adi>/caern.git
cd caern
```

### Adım 2 — Ortam Değişkenlerini Ayarlayın

```bash
cp .env.example .env
```

`.env` dosyasını açıp aşağıdaki değerleri değiştirin:

```env
JWT_SECRET_KEY=<uzun-rastgele-karakter-dizisi>
POSTGRES_PASSWORD=<veritabani-sifreniz>
MINIO_ROOT_PASSWORD=<minio-sifreniz>
```

Geri kalan tüm varsayılan değerler yerel geliştirme için olduğu gibi çalışır.

### Adım 3 — Servisleri Başlatın

```bash
sudo make up
```

Bu komut sırasıyla:
1. `nginx/certs/` altında kendinden imzalı TLS sertifikası oluşturur (yoksa)
2. API, Celery Worker ve React frontend için Docker image'larını derler
3. Tüm konteynerleri başlatır (nginx, api, worker, redis, postgres, minio, frontend)

> İlk derleme PyTorch, GDAL ve model ağırlıklarını indirir. İnternet hızınıza göre **5–15 dakika** sürebilir.

### Adım 4 — Veritabanı Migrasyonlarını Çalıştırın

```bash
sudo make migrate
```

### Adım 5 — Yönetici Kullanıcısını Oluşturun

```bash
sudo make seed
```

Varsayılan yönetici bilgileri:

| Alan | Değer |
|---|---|
| E-posta | `admin@caern.local` |
| Şifre | `caern2024!` |

### Adım 6 — Uygulamayı Açın

Tarayıcınızda **[https://localhost](https://localhost)** adresine gidin.

> Sertifika kendinden imzalı olduğu için tarayıcı uyarısı göreceksiniz. Chrome'da **Gelişmiş → localhost'a devam et**, Firefox'ta **Riski kabul et** seçeneğine tıklayın.

---

### Make Komutları Referansı

| Komut | Açıklama |
|---|---|
| `sudo make up` | Image'ları derle ve tüm servisleri başlat |
| `sudo make down` | Konteynerleri durdur (veriler korunur) |
| `sudo make reset` | Konteynerleri durdur ve **tüm verileri sil** |
| `sudo make build` | Image'ları yeniden derle (bağımlılık ekledikten sonra) |
| `sudo make migrate` | Alembic migrasyonlarını uygula |
| `sudo make seed` | Varsayılan yönetici kullanıcısını oluştur |
| `sudo make test` | Pytest ile backend test paketini çalıştır |
| `sudo make certs` | TLS sertifikasını yeniden oluştur |

---

## Kullanım

### Analiz Çalıştırma

1. `https://localhost` adresine gidin ve giriş yapın
2. Sol panelden **Yeni Analiz**'e tıklayın
3. **Önce** ve **Sonra** görüntülerini yükleyin (hassas alan hesabı için GeoTIFF önerilir; JPEG/PNG de desteklenir)
4. Parametreleri ayarlayın:
   - **Güven eşiği** (50–95%) — yüksek değer daha az ama daha güvenilir tespit üretir
   - **Minimum alan** (25–500 m²) — bu değerin altındaki bölgeler göz ardı edilir
   - **Tespit modu** — `classical` (hızlı, yalnızca CPU) veya `yolov8+sam` (hassas, GPU önerilir)
5. **Analizi Başlat**'a tıklayın. İlerleme gerçek zamanlı gösterilir
6. Analiz tamamlandığında harita sonuç alanına yakınlaşır; sağ panelden katmanları ve opaklığı ayarlayın
7. **CSV Dışa Aktar** veya **PDF Dışa Aktar** ile raporunuzu indirin

### API Dokümantasyonu

Uygulama çalışırken interaktif API belgelerine erişebilirsiniz:

- **Swagger UI**: `https://localhost/docs`
- **ReDoc**: `https://localhost/redoc`

### Temel API Endpoint'leri

| Yöntem | Yol | Açıklama |
|---|---|---|
| `POST` | `/api/auth/login` | Erişim + yenileme token'ı al |
| `POST` | `/api/auth/refresh` | Erişim token'ını yenile |
| `POST` | `/api/images/upload` | Önce/sonra görüntü çifti yükle |
| `POST` | `/api/jobs` | Yeni analiz işi oluştur ve kuyruğa ekle |
| `GET` | `/api/jobs` | Tüm işleri listele |
| `GET` | `/api/jobs/{id}` | İş detayları ve durumu |
| `GET` | `/api/jobs/{id}/metrics` | Tamamlanan iş metriklerini al |
| `GET` | `/api/jobs/{id}/progress?token=...` | Gerçek zamanlı ilerleme SSE akışı |
| `GET` | `/api/reports/jobs/{id}/download.csv` | CSV raporu indir |
| `GET` | `/api/reports/jobs/{id}/download.pdf` | PDF raporu indir |
| `GET` | `/health` | Servis sağlık kontrolü |

---

## Proje Yapısı

```
caern/
├── backend/
│   ├── ai_models/          # YOLOv8 ve SAM model sarmalayıcıları
│   ├── alembic/            # Veritabanı migrasyonları
│   ├── analysis_engine/    # Celery uygulaması, iş orkestratörü, klasik dedektör
│   ├── api/                # FastAPI router'ları ve bağımlılık enjeksiyonu
│   ├── auth/               # JWT işleme, şifre hash'leme, RBAC
│   ├── common_utils/       # Yapılandırma, loglama, istisna yönetimi
│   ├── data_access/        # SQLAlchemy async oturum ve temel model
│   ├── geo_processing/     # GDAL/Rasterio görüntü hizalama ve meta veri
│   ├── models/             # AI model ağırlık dosyaları
│   ├── notification/       # SSE yayıncısı, SMTP e-posta
│   ├── reporting/          # CSV ve PDF rapor üreticileri
│   ├── storage/            # MinIO istemcisi
│   ├── tests/              # Pytest test paketi
│   ├── main.py             # FastAPI uygulama fabrikası
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/     # MapView, LayerManager, MetricsPanel, NewAnalysis, ...
│   │   └── index.css
│   └── package.json
├── nginx/
│   ├── nginx.conf
│   └── certs/              # Otomatik oluşturulan TLS sertifikası
├── docker-compose.yml
├── Makefile
└── .env.example
```

---

## Katkı (Contribution)

Katkılarınızı memnuniyetle karşılıyoruz! Aşağıdaki adımları izleyin:

### Katkı Rehberi

1. **Fork**'layın — Bu depoyu GitHub üzerinden fork'layın
2. **Klonlayın** — Fork'ladığınız depoyu yerel makinenize klonlayın
   ```bash
   git clone https://github.com/<kullanici-adiniz>/caern.git
   ```
3. **Branch oluşturun** — Değişiklikleriniz için yeni bir dal açın
   ```bash
   git checkout -b feature/ozellik-adi
   # veya
   git checkout -b fix/hata-aciklamasi
   ```
4. **Geliştirin** — Değişikliklerinizi yapın ve testleri çalıştırın
   ```bash
   sudo make test
   ```
5. **Commit'leyin** — Anlamlı commit mesajları yazın
   ```bash
   git commit -m "feat: yeni özellik açıklaması"
   ```
6. **Push'layın** — Dalınızı uzak depoya gönderin
   ```bash
   git push origin feature/ozellik-adi
   ```
7. **Pull Request açın** — GitHub üzerinden bir PR oluşturun ve değişikliklerinizi açıklayın

### Commit Mesajı Kuralları

| Önek | Kullanım |
|---|---|
| `feat:` | Yeni özellik |
| `fix:` | Hata düzeltmesi |
| `docs:` | Yalnızca belge değişikliği |
| `refactor:` | Davranışı değiştirmeyen kod yeniden düzenleme |
| `test:` | Test ekleme veya düzeltme |

### Hata Bildirimi

Bir hata bulursanız lütfen GitHub Issues bölümünde aşağıdaki bilgileri içeren bir issue açın:
- Hatanın açıklaması
- Yeniden oluşturma adımları
- Beklenen ve gerçekleşen davranış
- Ortam bilgisi (OS, Docker sürümü vb.)

---

## Lisans

Bu proje **MIT Lisansı** ile lisanslanmıştır.

```
MIT License

Copyright (c) 2024 CAERN Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
