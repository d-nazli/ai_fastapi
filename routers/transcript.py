"""
POST /chat/analyze-json-transcript-with-summary/
JSON transcript → AI classification (MÜLAKAT / TOPLANTI) + summary
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Optional

from fastapi import APIRouter

from schemas.transcript import TranscriptAnalyzeRequest, TranscriptAnalyzeResponse
from services.file_reader_service import collect_transcripts, extract_transcript_from_json
from services.lm_studio_service import lm_studio_service
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from core import get_db
from services.ai_log_service import ai_log_service
import time


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["transcript"])


@router.post(
    "/analyze-json-transcript-with-summary/",
    response_model=TranscriptAnalyzeResponse,
)
async def analyze_json_transcript_with_summary(
    body: TranscriptAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
) -> TranscriptAnalyzeResponse:
    start_time = time.time()
    request_id = await ai_log_service.create_request_log(
    db=db,
    user_id="system",
    endpoint="/chat/analyze-json-transcript-with-summary",
    model_name="qwen",
    transcript_length=0,
    prompt_length=0,
    temperature=0.3
)
    json_path = body.json_path
    transcript_save_path: Optional[str] = None

    if not os.path.exists(json_path):
        return TranscriptAnalyzeResponse(
            success=False,
            error=f"JSON dosyası bulunamadı: {json_path}",
        )

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)
    except json.JSONDecodeError as e:
        return TranscriptAnalyzeResponse(success=False, error=f"JSON dosyası geçersiz: {e}")
    except Exception as e:
        return TranscriptAnalyzeResponse(success=False, error=f"JSON dosyası okunamadı: {e}")

    transcript = extract_transcript_from_json(json_data)

    if not transcript:
        return TranscriptAnalyzeResponse(
            success=False,
            error=(
                "JSON dosyasında transcriptText alanı bulunamadı. "
                'Lütfen JSON dosyasının "transcriptText" anahtarını içerdiğinden emin olun.'
            ),
        )

    transcript = str(transcript) if not isinstance(transcript, str) else transcript

    if len(transcript) < 10:
        return TranscriptAnalyzeResponse(success=False, error="Transcript boş veya çok kısa")

    try:
        base_name = os.path.splitext(os.path.basename(json_path))[0]
        transcript_save_path = os.path.join(os.path.dirname(json_path), f"{base_name}_transcript.txt")
        with open(transcript_save_path, "w", encoding="utf-8") as f:
            f.write(transcript)
        logger.info("Transcript saved: %s", transcript_save_path)
    except Exception as exc:
        logger.warning("Transcript save failed: %s", exc)

    context_type: Optional[str] = None
    summary: Optional[str] = None

    if len(transcript) < 50:
        return TranscriptAnalyzeResponse(
            success=True,
            json_path=json_path,
            context_type=None,
            summary=None,
            transcript_txt_path=transcript_save_path,
            summary_error="Özet çıkarılamadı (metin çok kısa veya hata oluştu)",
        )

    try:
        combined_prompt = _build_analysis_prompt(json_path, transcript)
        t0 = time.time()
        ai_response = await lm_studio_service.send_direct_message(
            prompt=combined_prompt,
            temperature=0.3,
            timeout=300,
        )

        context_type, summary = _parse_ai_response(ai_response, json_path)
        duration = int((time.time() - t0) * 1000)
        await ai_log_service.create_task_log(
    db=db,
    request_id=request_id,
    task_name="TRANSCRIPT_ANALYSIS",
    model_name="qwen",
    duration_ms=duration,
    response_length=len(ai_response) if ai_response else 0,
    status="SUCCESS",
)

    except Exception as exc:
        duration = int((time.time() - t0) * 1000)
        await ai_log_service.create_task_log(
    db=db,
    request_id=request_id,
    task_name="TRANSCRIPT_ANALYSIS",
    model_name="qwen",
    duration_ms=duration,
    response_length=0,
    status="FAILED",
    error_type=type(exc).__name__,
    error_message=str(exc),
)
        logger.exception("AI analysis error (JSON): %s", exc)
        return TranscriptAnalyzeResponse(success=False, error=f"AI analiz hatası: {exc}")
    total_time = int((time.time() - start_time) * 1000)
    await ai_log_service.update_request_log(
    db=db,
    request_id=request_id,
    status="SUCCESS",
    total_response_time_ms=total_time
)
    resp = TranscriptAnalyzeResponse(
        success=True,
        json_path=json_path,
        context_type=context_type,
        summary=summary if summary else None,
        transcript_txt_path=transcript_save_path,
    )
    if not summary:
        resp.summary_error = "Özet çıkarılamadı (metin çok kısa veya hata oluştu)"
    return resp


# ── HELPERS ───────────────────────────────────────────────


def _build_analysis_prompt(json_path: str, transcript: str) -> str:
    return f"""Sen uzman bir kurumsal analiz asistanısın. Aşağıdaki toplantı metnini analiz etmen gerekiyor.

ÖNEMLİ: TÜM YANITLARINI TÜRKÇE DİLİNDE VERMELİSİN. ÖZET MUTLAKA TÜRKÇE OLMALIDIR.

GÖREVLERİN:
1. VİDEO TÜRÜNÜ BELİRLE: Metnin içeriğine bakarak şu kategorilerden birini seç: "MÜLAKAT", "TOPLANTI" veya "DİĞER".

MÜLAKAT (İş Görüşmesi) İşaretleri:
- "Mülakat", "mülakat serisi", "mülakat videosu", "iş görüşmesi" kelimeleri geçiyor
- Kişi kendinden bahsediyor: "ben", "bana", "benim", "kendim"
- Özgeçmiş, CV, tecrübeler, eğitim geçmişi hakkında konuşuluyor
- "Aday", "başvuru", "pozisyon", "işe alım" kelimeleri geçiyor
- Soru-cevap formatında, bir kişi soruyor diğeri cevaplıyor
- Kişisel yetenekler, deneyimler, başarılar anlatılıyor
- "Neden bu pozisyonu istiyorsunuz?", "Hangi özellikleriniz var?" gibi sorular
- Tek bir kişi hakkında sorular soruluyor

TOPLANTI (Meeting) İşaretleri:
- Birden fazla kişi konuşuyor ve fikir alışverişi yapılıyor
- "Proje", "görev", "sorumluluk", "takım", "ekip" kelimeleri geçiyor
- Kararlar alınıyor, planlar yapılıyor
- "Toplantı", "meeting", "koordinasyon" kelimeleri geçiyor
- İş süreçleri, iş akışları, iş planları tartışılıyor
- Birden fazla kişi fikirlerini paylaşıyor
- Grup kararları, ortak çalışma konuları

2. ÖZET ÇIKAR: Metnin net, kısa ve akıcı bir özetini TÜRKÇE DİLİNDE yaz (Tek paragraf, 7-8 cümle). Üst düzey yöneticiler için rapor formatında, profesyonel ve kurumsal bir Türkçe dil kullan. Asla madde imi (bullet point) kullanma. Başlık, "Rapor:", "Özet:" gibi formatlama ekleme. ÖZET MUTLAKA TÜRKÇE OLMALIDIR, İNGİLİZCE YAZMA.

ÇIKTI FORMATI (Lütfen tam olarak bu formatı kullan, ayrıştırma için gereklidir):

JSON DOSYA YOLU: {json_path}
TÜR: [Seçtiğin Kategori - MÜLAKAT, TOPLANTI veya DİĞER]
ÖZET: [Özet Metni Buraya - MUTLAKA TÜRKÇE]

--- ANALİZ EDİLECEK METİN ---
{transcript}"""


def _parse_ai_response(full_response: str, json_path: str) -> tuple[Optional[str], Optional[str]]:
    """Parses AI output to extract TÜR and ÖZET fields.
    Handles both plain-text and JSON-formatted responses from LM Studio models.
    """
    import json as _json

    # 1) Try JSON parse first — some models (e.g. Qwen) return structured JSON
    try:
        stripped = full_response.strip()
        # Strip markdown code fences if present
        if stripped.startswith("```"):
            stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
            stripped = re.sub(r"\s*```$", "", stripped)
        data = _json.loads(stripped)
        if isinstance(data, dict):
            raw_type = str(data.get("TÜR", data.get("tur", data.get("Tür", "")))).upper()
            raw_summary = data.get("ÖZET", data.get("özet", data.get("Ozet", "")))
            context_type = _classify_type(raw_type)
            if raw_summary and len(str(raw_summary)) >= 20:
                return context_type, str(raw_summary).strip()
    except (_json.JSONDecodeError, ValueError, TypeError):
        pass

    # 2) Line-by-line parsing (original format)
    lines = full_response.strip().split("\n")
    context_type: Optional[str] = None
    summary_lines: list[str] = []
    found_type = False
    found_summary = False

    for line in lines:
        lu = line.upper().strip()

        if lu.startswith("TÜR:") and not found_type:
            raw = line.split(":", 1)[1].strip().replace(".", "").replace('"', "").replace("'", "").strip().upper()
            context_type = _classify_type(raw)
            if context_type:
                found_type = True

        elif lu.startswith("ÖZET:") and not found_summary:
            after = line.split(":", 1)[1].strip() if ":" in line else ""
            if after:
                summary_lines.append(after)
            found_summary = True

        elif found_summary:
            if lu.startswith("JSON DOSYA YOLU:") or lu.startswith("TÜR:"):
                break
            summary_lines.append(line)

    summary = " ".join(summary_lines).strip() if summary_lines else None
    if summary:
        summary = re.sub(
            r"^\s*\*{0,2}\s*(Rapor|Özet|Summary):\s*\*{0,2}\s*",
            "",
            summary,
            flags=re.IGNORECASE | re.MULTILINE,
        ).strip()

    if not found_type:
        upper = full_response.upper()
        if "MÜLAKAT" in upper or "MULAKAT" in upper:
            context_type = "MÜLAKAT"
        elif "TOPLANTI" in upper:
            context_type = "TOPLANTI"
        else:
            context_type = "TOPLANTI"

    if not summary or len(summary) < 20:
        cleaned = []
        for line in lines:
            lu = line.upper().strip()
            if not (lu.startswith("JSON DOSYA YOLU:") or lu.startswith("TÜR:") or lu.startswith("ÖZET:")):
                cleaned.append(line)
        if cleaned:
            summary = " ".join(cleaned).strip()
            summary = re.sub(
                r"^\s*\*{0,2}\s*(Rapor|Özet|Summary):\s*\*{0,2}\s*",
                "",
                summary,
                flags=re.IGNORECASE | re.MULTILINE,
            ).strip()

    return context_type, summary


def _classify_type(raw: str) -> Optional[str]:
    raw = raw.upper()
    if "MÜLAKAT" in raw or "MULAKAT" in raw:
        return "MÜLAKAT"
    if "TOPLANTI" in raw:
        return "TOPLANTI"
    if "DİĞER" in raw or "DIGER" in raw:
        return "DİĞER"
    return None
