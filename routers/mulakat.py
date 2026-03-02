"""
POST /chat/mulakat-degerlendirme/
Interview transcript → 4 parallel AI analyses + webhook
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter

from core.settings import settings
from schemas.mulakat import MulakatDegerlendirmeRequest, MulakatDegerlendirmeResponse
from services.file_reader_service import read_transcript_file
from services.lm_studio_service import lm_studio_service
from services.webhook_service import fire_and_forget_webhook

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["mulakat"])

MAX_TEXT_LENGTH = 15000
AI_TEMPERATURE = 0.3

# ── PROMPTS ───────────────────────────────────────────────

PROMPT_SCORING = """Aşağıdaki mülakat özetini profesyonel bir İnsan Kaynakları (İK) uzmanı gibi analiz et.

BÖLÜM 1: PUANLAMA TABLOSU
Her kriteri şu formatta yaz: Kriter Adı: (Puan/5) - {candidate_name}'in [açıklama].

Kriterler: İletişim Becerisi, Motivasyon ve Tutku, Kültürel Uyum, Analitik/Düşünsel Beceriler, Profesyonel Tutum, Geçmiş Deneyim Uyumu, Liderlik ve Girişimcilik, Zayıflıklarla Başa Çıkma Yetisi, Uzun Vadeli Potansiyel, Genel Etki / İzlenim

Genel Ortalama Puan ve İK Genel Yorum ekle."""

PROMPT_RECRUITER = """Aşağıdaki mülakat özetini profesyonel bir İnsan Kaynakları (İK) uzmanı gibi analiz et.

BÖLÜM 2: RECRUITER NOTU
Başlıklar: Aday Adı, Pozisyon, Genel Yorum, Dikkat Çeken Güçlü Yönler, Geliştirme Alanları, Değerlendirme Önerisi"""

PROMPT_TECHNICAL = """Aşağıdaki mülakat özetini teknik yetkinlik açısından analiz et.

BÖLÜM 3: TEKNİK YETKİNLİK
Kategoriler: Programlama Dilleri, Teknolojiler/Framework'ler, Projeler, Problem Çözme, Öğrenme Yeteneği
Her kategori için puanlama yap."""

PROMPT_SOFT_SKILLS = """Aşağıdaki mülakat özetini soft skill açısından analiz et.

BÖLÜM 4: SOFT SKILL ANALİZİ
Beceriler: İletişim Tarzı, Takım Çalışması, Liderlik, Adaptasyon, Zaman Yönetimi, Stres Yönetimi, Yaratıcılık, Empati
Her beceri için puanlama yap. Kesinlikle Türkçe cevap ver."""


# ── ENDPOINT ──────────────────────────────────────────────


@router.post(
    "/mulakat-degerlendirme/",
    response_model=MulakatDegerlendirmeResponse,
)
async def mulakat_degerlendirme(
    body: MulakatDegerlendirmeRequest,
) -> MulakatDegerlendirmeResponse:
    user_id = body.userId
    first_name = body.firstName
    last_name = body.lastName
    email = body.email
    transcript_path = body.transcriptPath
    candidate_full_name = f"{first_name} {last_name}"

    logger.info(
        "mulakat-degerlendirme request: userId=%s, name=%s, path=%s",
        user_id,
        candidate_full_name,
        transcript_path,
    )

    if not transcript_path:
        return MulakatDegerlendirmeResponse(
            success=False,
            error="transcriptPath alanı gereklidir",
        )

    if not os.path.isabs(transcript_path):
        base = settings.transcript_base_dir
        if base:
            transcript_path = os.path.join(base, transcript_path)

    interview_text, error = read_transcript_file(transcript_path)
    if error:
        logger.warning("File read error: %s", error)
        return MulakatDegerlendirmeResponse(success=False, error=error)

    if not interview_text:
        return MulakatDegerlendirmeResponse(success=False, error="Dosya içeriği boş")

    if len(interview_text) > MAX_TEXT_LENGTH:
        interview_text = interview_text[:MAX_TEXT_LENGTH]

    start_time = time.time()

    async def _analyze(prompt: str, task_name: str) -> Dict[str, Any]:
        t0 = time.time()
        try:
            full_prompt = (
                "Sen uzman bir İK analistisin. Markdown kullan. "
                "Sadece final sonucu ver, düşünme adımlarını gösterme.\n\n"
                + prompt
            )
            content = await lm_studio_service.send_direct_message(
                prompt=full_prompt,
                temperature=AI_TEMPERATURE,
                timeout=1200,
            )
            dur = round(time.time() - t0, 1)
            return {
                "status": "success" if content else "failed",
                "content": content,
                "duration": dur,
                "error": None if content else "Boş yanıt",
            }
        except Exception as exc:
            dur = round(time.time() - t0, 1)
            err = "Context limiti aşıldı" if "Context size" in str(exc) else str(exc)
            return {"status": "failed", "content": None, "duration": dur, "error": err}

    suffix = f"\n\n--- METİN ---\n{interview_text}"

    scoring_task = _analyze(
        PROMPT_SCORING.format(candidate_name=candidate_full_name) + suffix,
        "SCORING",
    )
    recruiter_task = _analyze(
        PROMPT_RECRUITER.format(candidate_name=candidate_full_name) + suffix,
        "RECRUITER",
    )
    technical_task = _analyze(PROMPT_TECHNICAL + suffix, "TECHNICAL")
    soft_task = _analyze(PROMPT_SOFT_SKILLS + suffix, "SOFT_SKILLS")

    scoring, recruiter, technical, soft_skills = await asyncio.gather(
        scoring_task, recruiter_task, technical_task, soft_task
    )

    total_time = time.time() - start_time

    tasks_status = {
        "scoring": {"status": scoring["status"], "duration": scoring["duration"], "error": scoring["error"]},
        "recruiter": {"status": recruiter["status"], "duration": recruiter["duration"], "error": recruiter["error"]},
        "technical": {"status": technical["status"], "duration": technical["duration"], "error": technical["error"]},
        "soft_skills": {"status": soft_skills["status"], "duration": soft_skills["duration"], "error": soft_skills["error"]},
    }

    webhook_payload = {
        "userId": user_id,
        "firstName": first_name,
        "lastName": last_name,
        "email": email,
        "recruiterNotu": recruiter["content"],
        "teknikYetkinlik": technical["content"],
        "puanlamaTablosu": scoring["content"],
        "softSkillAnalizi": soft_skills["content"],
        "totalTime": round(total_time, 2),
    }

    fire_and_forget_webhook(webhook_payload)

    return MulakatDegerlendirmeResponse(
        success=True,
        userId=user_id,
        firstName=first_name,
        lastName=last_name,
        email=email,
        puanlamaTablosu=scoring["content"],
        recruiterNotu=recruiter["content"],
        teknikYetkinlik=technical["content"],
        softSkillAnalizi=soft_skills["content"],
        tasks=tasks_status,
        totalTime=round(total_time, 2),
        totalTimeMinutes=round(total_time / 60, 1),
        webhookSent=True,
    )
