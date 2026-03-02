"""
Pydantic schemas for the analyze-json-transcript-with-summary endpoint
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class TranscriptAnalyzeRequest(BaseModel):
    json_path: str = Field(
        ...,
        min_length=1,
        description="Analiz edilecek JSON dosyasının tam yolu (transcriptText içermeli)",
    )


class TranscriptAnalyzeResponse(BaseModel):
    success: bool
    json_path: Optional[str] = None
    context_type: Optional[str] = None
    summary: Optional[str] = None
    transcript_txt_path: Optional[str] = None
    summary_error: Optional[str] = None
    error: Optional[str] = None
