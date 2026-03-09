# SlipScan-OCR 🔍

Microservice สำหรับประมวลผล OCR สลิปโอนเงินธนาคารไทย ใช้ **Typhoon OCR API** ในการอ่านข้อความและ Parser เฉพาะทางสำหรับข้อมูลสลิป

## Architecture

```
SlipScan-OCR (port 5000)
    └── POST /ocr    — รับภาพสลิป → คืน JSON ข้อมูลสลิป
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Runtime | Python 3.10 |
| Framework | Flask |
| OCR Engine | Typhoon OCR API |
| Container | Docker + Gunicorn |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/ocr` | ส่งภาพสลิป → รับ JSON ข้อมูล |
| POST | `/ocr/parse-text` | Parse raw text โดยไม่ใช้ OCR API |
| GET | `/health` | Health check |

### Request Format

```
POST /ocr
Content-Type: multipart/form-data

file: <image file>  (jpg, png, webp, max 10MB)
```

### Response Format

```json
{
  "success": true,
  "data": {
    "sender_name": "นาย สมชาย ใจดี",
    "bank_name": "กสิกรไทย",
    "amount": 1500.00,
    "slip_date": "2026-03-10",
    "slip_time": "14:30:00",
    "ref_no": "REF123456789",
    "receiver_name": "ร้านค้า ABC",
    "receiver_account": "xxx-x-xxxxx-x"
  },
  "warnings": []
}
```

## Getting Started

### 1. Clone

```bash
git clone https://github.com/Napat-ICE/SlipScan-OCR.git
cd SlipScan-OCR
```

### 2. Setup Environment

```bash
cp .env.example .env
# แก้ไข .env ใส่ค่าจริง
```

**.env** ที่ต้องกรอก:

```env
TYPHOON_OCR_API_KEY=your_typhoon_ocr_api_key
OCR_SERVICE_PORT=5000
OCR_MAX_FILE_SIZE_MB=10
LOG_LEVEL=INFO
```

### 3. Run with Docker

```bash
docker build -t slipscan-ocr .
docker run -p 5000:5000 --env-file .env slipscan-ocr
```

### 4. Run Locally (Development)

```bash
pip install -r requirements.txt
python app.py
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TYPHOON_OCR_API_KEY` | ✅ | — | API Key สำหรับ Typhoon OCR |
| `OCR_SERVICE_PORT` | ❌ | `5000` | Port ของ service |
| `OCR_MAX_FILE_SIZE_MB` | ❌ | `10` | ขนาดไฟล์สูงสุด (MB) |
| `LOG_LEVEL` | ❌ | `INFO` | Log level |

## Project Structure

```
SlipScan-OCR/
├── app.py              — Flask app, endpoints, request logging
├── Ocr.py              — SlipOCR engine + SlipParser
├── requirements.txt
├── Dockerfile
└── .env.example
```

## Related Services

- [SlipScan-Backend](https://github.com/Napat-ICE/SlipScan-Backend) — REST API
- [SlipScan-Frontend](https://github.com/Napat-ICE/SlipScan-Frontend) — Web interface
