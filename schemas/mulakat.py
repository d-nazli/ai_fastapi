"""
Pydantic schemas for the mulakat-degerlendirme endpoint
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, EmailStr, Field


class MulakatDegerlendirmeRequest(BaseModel):
    userId: str = Field(..., min_length=1, description="Kullanıcı ID")
    firstName: str = Field(..., min_length=1, description="Adayın adı")
    lastName: str = Field(..., min_length=1, description="Adayın soyadı")
    email: EmailStr = Field(..., description="Adayın email adresi")
    transcriptPath: str = Field(
        default="",
        description="Mülakat transkript dosyasının tam yolu (.txt, .docx veya .json)",
    )


class MulakatDegerlendirmeResponse(BaseModel):
    success: bool
    userId: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    email: Optional[str] = None
    puanlamaTablosu: Optional[str] = None
    recruiterNotu: Optional[str] = None
    teknikYetkinlik: Optional[str] = None
    softSkillAnalizi: Optional[str] = None
    tasks: Optional[Dict[str, Any]] = None
    totalTime: Optional[float] = None
    totalTimeMinutes: Optional[float] = None
    webhookSent: Optional[bool] = None
    error: Optional[str] = None
