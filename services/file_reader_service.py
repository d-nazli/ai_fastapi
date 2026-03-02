"""
File reader service — JSON transcript collection, DOCX, TXT reading
"""

from __future__ import annotations

import json
import os
from typing import Any, List, Optional, Tuple


def collect_transcripts(obj: Any) -> List[str]:
    """Recursively collects all transcriptText fields with speaker names."""
    texts: List[str] = []
    if isinstance(obj, dict):
        speaker = obj.get("userName") or obj.get("speaker") or obj.get("name")
        if "transcriptText" in obj and obj["transcriptText"]:
            content = str(obj["transcriptText"])
            texts.append(f"{speaker}: {content}" if speaker else content)
        for value in obj.values():
            texts.extend(collect_transcripts(value))
    elif isinstance(obj, list):
        for item in obj:
            texts.extend(collect_transcripts(item))
    return texts


def _find_transcript_text(obj: Any) -> Optional[str]:
    """Depth-first search for a single transcriptText value."""
    if isinstance(obj, dict):
        if "transcriptText" in obj:
            return obj["transcriptText"]
        for value in obj.values():
            result = _find_transcript_text(value)
            if result:
                return result
    elif isinstance(obj, list):
        for item in obj:
            result = _find_transcript_text(item)
            if result:
                return result
    return None


def extract_transcript_from_json(json_data: Any) -> Optional[str]:
    """
    Extracts transcript text from parsed JSON data.
    Tries collect_transcripts first, then falls back to single-field lookups.
    """
    all_texts = collect_transcripts(json_data)
    if all_texts:
        return "\n".join(all_texts)

    if isinstance(json_data, dict):
        if "transcriptText" in json_data:
            return str(json_data["transcriptText"])
        if "transcript" in json_data and isinstance(json_data["transcript"], dict):
            t = json_data["transcript"]
            if "text" in t:
                return str(t["text"])
            if "transcriptText" in t:
                return str(t["transcriptText"])
        if "data" in json_data and isinstance(json_data["data"], dict):
            if "transcriptText" in json_data["data"]:
                return str(json_data["data"]["transcriptText"])

    return _find_transcript_text(json_data)


def read_transcript_file(file_path: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Reads a transcript file (.json, .docx, .txt).
    Returns (text, None) on success or (None, error_message) on failure.
    """
    if not os.path.exists(file_path):
        return None, f"Dosya bulunamadı: {file_path}"

    try:
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                json_data = json.load(f)

            if isinstance(json_data, list):
                lines = []
                for item in json_data:
                    if isinstance(item, dict):
                        user_name = item.get("userName", "Bilinmeyen")
                        transcript = item.get("transcriptText", "")
                        if transcript:
                            lines.append(f"[{user_name}]: {transcript}")
                return ("\n".join(lines).strip(), None) if lines else (None, "JSON listesinde transcriptText bulunamadı")
            elif isinstance(json_data, dict):
                if "transcripts" in json_data:
                    lines = []
                    for item in json_data["transcripts"]:
                        user_name = item.get("userName", "Bilinmeyen")
                        transcript = item.get("transcriptText", "")
                        if transcript:
                            lines.append(f"[{user_name}]: {transcript}")
                    return ("\n".join(lines).strip(), None) if lines else (None, "transcripts listesinde metin bulunamadı")
                return json.dumps(json_data, ensure_ascii=False, indent=2), None
            return None, "Beklenmeyen JSON formatı"

        elif ext == ".docx":
            from docx import Document
            doc = Document(file_path)
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            return text, None

        elif ext == ".txt":
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read(), None

        else:
            return None, "Sadece .txt, .docx ve .json desteklenir"

    except json.JSONDecodeError as e:
        return None, f"JSON dosyası geçersiz: {str(e)}"
    except Exception as e:
        return None, f"Dosya okuma hatası: {str(e)}"
