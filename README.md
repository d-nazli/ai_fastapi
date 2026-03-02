# IntelliumAI Backend

FastAPI tabanlı mülakat analiz servisi. LM Studio üzerinden yerel AI modeli kullanarak JSON transcript dosyalarını sınıflandırır, özetler ve aday değerlendirmesi yapar.

## Gereksinimler

- **Python** 3.10+
- **LM Studio** — localhost:1234 üzerinde çalışır durumda, model yüklü (ör. `qwen/qwen3-4b-2507`)

## Kurulum

```bash
cd backendnew
pip install -r requirements.txt
```

`.env` dosyasını düzenle (varsayılan değerlerle çalışır, gerekirse güncelle):

| Değişken | Varsayılan | Açıklama |
|----------|-----------|----------|
| `LM_STUDIO_HOST` | `localhost` | LM Studio adresi |
| `LM_STUDIO_PORT` | `1234` | LM Studio portu |
| `AI_MODEL` | `qwen/qwen3-4b-2507` | LM Studio'da yüklü model adı |
| `AI_TEMPERATURE` | `0.3` | Model sıcaklık değeri |
| `AI_TIMEOUT` | `300` | AI istek zaman aşımı (saniye) |
| `WEBHOOK_URL` | `http://127.0.0.1:5000/...` | Mülakat sonucu webhook adresi |
| `PORT` | `8000` | Sunucu portu |

## Çalıştırma

```bash
python main.py
```

Sunucu `http://localhost:8000` adresinde başlar. Port meşgulse:

```bash
# Windows PowerShell
$env:PORT="8001"; python main.py
```

## Endpointler

| Metod | Yol | Açıklama |
|-------|-----|----------|
| `GET` | `/` | Uygulama bilgisi |
| `GET` | `/health` | LM Studio bağlantı durumu |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/test` | Test arayüzü (HTML) |
| `POST` | `/chat/analyze-json-transcript-with-summary/` | Transcript sınıflandırma + özet |
| `POST` | `/chat/mulakat-degerlendirme/` | 4 paralel AI mülakat değerlendirmesi |

### POST `/chat/analyze-json-transcript-with-summary/`

JSON transcript dosyasını analiz eder, MÜLAKAT/TOPLANTI/DİĞER olarak sınıflandırır ve Türkçe özet çıkarır.

**Request:**
```json
{
  "json_path": "C:/tam/yol/transcript.json"
}
```

**Response:**
```json
{
  "success": true,
  "json_path": "C:/tam/yol/transcript.json",
  "context_type": "MÜLAKAT",
  "summary": "Elif Demir, İTÜ Bilgisayar Mühendisliği mezunu...",
  "transcript_txt_path": "C:/tam/yol/transcript_transcript.txt"
}
```

### POST `/chat/mulakat-degerlendirme/`

Aday bilgileri ve transcript dosyasıyla 4 paralel AI analizi yapar, sonucu webhook ile gönderir.

**Request:**
```json
{
  "userId": "user-001",
  "firstName": "Elif",
  "lastName": "Demir",
  "email": "elif@test.com",
  "transcriptPath": "C:/tam/yol/transcript.json"
}
```

**Response:**
```json
{
  "success": true,
  "userId": "user-001",
  "puanlamaTablosu": "İletişim Becerisi: 5/5 ...",
  "recruiterNotu": "Genel Yorum: ...",
  "teknikYetkinlik": "Programlama: 90/100 ...",
  "softSkillAnalizi": "İletişim Tarzı: 5/5 ...",
  "totalTime": 53.07,
  "webhookSent": true
}
```

## Proje Yapısı

```
backendnew/
├── main.py                 # FastAPI uygulama giriş noktası
├── .env                    # Ortam değişkenleri
├── requirements.txt        # Python bağımlılıkları
├── core/
│   ├── settings.py         # Pydantic Settings (LM Studio, webhook, CORS)
│   ├── middleware.py        # RequestID, Access Log, Security Headers, CORS
│   └── exceptions.py       # ServiceError hiyerarşisi, RFC 7807
├── routers/
│   ├── transcript.py       # /chat/analyze-json-transcript-with-summary/
│   └── mulakat.py          # /chat/mulakat-degerlendirme/
├── schemas/
│   ├── transcript.py       # Request/Response şemaları
│   └── mulakat.py          # Request/Response şemaları
├── services/
│   ├── lm_studio_service.py    # LM Studio API client (httpx async)
│   ├── file_reader_service.py  # JSON/DOCX/TXT dosya okuma
│   └── webhook_service.py      # Async webhook gönderici
├── frontend_test.html      # Tarayıcı test arayüzü
└── test_data/              # Örnek test dosyaları
```

## Mimari Notlar

- **AI Backend:** LM Studio (OpenAI-uyumlu API, `localhost:1234`). Harici çalışır, process yönetimi yok.
- **Async:** Tüm AI çağrıları ve webhook gönderimi `httpx.AsyncClient` ile asenkron.
- **Paralel Analiz:** Mülakat endpointi 4 AI analizini `asyncio.gather` ile eş zamanlı çalıştırır.
- **Veritabanı:** Yok. Endpointler sadece dosya okuma + AI analizi yapar.
- **Hata Yönetimi:** RFC 7807 Problem Details formatı.
