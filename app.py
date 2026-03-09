"""
ocr_service/app.py
Flask microservice สำหรับ OCR สลิปธนาคารไทย
เรียกใช้ผ่าน HTTP — PHP backend จะ POST ไฟล์ภาพมาที่นี่
"""

import os
import sys
import uuid
import logging
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory, redirect
from dotenv import load_dotenv

# โหลด .env
load_dotenv()

from Ocr import SlipOCR, SlipParser

# ── Config ──────────────────────────────────────────────────────────────────
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("slipscan.ocr")

UPLOAD_DIR   = Path(__file__).parent / "temp_uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

MAX_SIZE_MB  = int(os.getenv("OCR_MAX_FILE_SIZE_MB", 10))
ALLOWED_EXT  = {".jpg", ".jpeg", ".png", ".webp"}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_SIZE_MB * 1024 * 1024

from flask import g
import time as _time

@app.before_request
def _before():
    g.start_time = _time.time()

@app.after_request
def _after(response):
    duration_ms = round((_time.time() - g.get("start_time", _time.time())) * 1000)
    logger.info("%s %s → %d (%dms)", request.method, request.path, response.status_code, duration_ms)
    return response

# Initialise OCR (สร้างครั้งเดียว)
ocr_engine = SlipOCR(
    api_key=os.getenv("TYPHOON_OCR_API_KEY"),
    auto_parse=True,
    preprocess=True,
)
slip_parser = SlipParser()



# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "slipscan-ocr"})


# ── POST /ocr  — รับภาพสลิป คืน JSON ──────────────────────────────────────
@app.post("/ocr")
def process_slip():
    """
    รับ multipart/form-data:
      - file: ไฟล์ภาพสลิป (jpg, png, webp)

    คืน JSON:
      {
        "success": true,
        "data": { ...parsed fields... },
        "warnings": []
      }
    """

    # ── Validate ──
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded (field: 'file')"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"success": False, "error": "Empty filename"}), 400

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        return jsonify({
            "success": False,
            "error": f"File type '{ext}' not supported. Allowed: {', '.join(ALLOWED_EXT)}"
        }), 415

    # ── บันทึกไฟล์ชั่วคราว ──
    temp_filename = f"{uuid.uuid4().hex}{ext}"
    temp_path     = UPLOAD_DIR / temp_filename

    try:
        file.save(str(temp_path))
        logger.info(f"Saved temp file: {temp_path}")

        # ── OCR + Parse ──
        data = ocr_engine.read(str(temp_path))

        warnings = []
        # เตือนถ้า field หลักหายไป
        for field in ["amount", "bank_name", "slip_date", "ref_no"]:
            if data.get(field) is None:
                warnings.append(f"Could not extract '{field}' from image")

        return jsonify({
            "success":  True,
            "data":     data,
            "warnings": warnings,
        }), 200

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return jsonify({"success": False, "error": str(e)}), 404

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

    except RuntimeError as e:
        logger.error(f"OCR failed: {e}")
        return jsonify({
            "success": False,
            "error":   "OCR processing failed",
            "detail":  str(e),
        }), 500

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500

    finally:
        # ลบไฟล์ชั่วคราวเสมอ
        if temp_path.exists():
            temp_path.unlink()
            logger.info(f"Cleaned up: {temp_path}")


# ── POST /ocr/parse-text  — รับ raw text คืน JSON (ไม่ใช้ OCR) ─────────────
@app.post("/ocr/parse-text")
def parse_raw_text():
    """
    รับ JSON body:  { "text": "raw OCR text here" }
    คืน parsed fields โดยไม่ต้องผ่าน Typhoon API
    ใช้สำหรับ test parser โดยไม่เสีย API quota
    """
    body = request.get_json(silent=True)
    if not body or "text" not in body:
        return jsonify({"success": False, "error": "JSON body with 'text' field required"}), 400

    try:
        data = slip_parser.parse(body["text"])
        return jsonify({"success": True, "data": data}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── Error Handlers ───────────────────────────────────────────────────────────
@app.errorhandler(413)
def file_too_large(e):
    return jsonify({
        "success": False,
        "error": f"File too large. Maximum size: {MAX_SIZE_MB}MB"
    }), 413


@app.errorhandler(404)
def not_found(e):
    return jsonify({"success": False, "error": "Endpoint not found"}), 404


# ── Run ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("OCR_SERVICE_PORT", 5000))
    logger.info("SlipScan OCR Service starting on http://0.0.0.0:%d", port)
    app.run(host="0.0.0.0", port=port, debug=False)
