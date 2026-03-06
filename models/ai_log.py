import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, Float, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID

from .base import BaseModel


class AIMulakatRequestLog(BaseModel):

    __tablename__ = "ai_mulakat_request_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    request_id = Column(String(100))

    user_id = Column(String(100))

    endpoint = Column(String(200))

    model_name = Column(String(100))

    transcript_length = Column(Integer)

    prompt_length = Column(Integer)

    temperature = Column(Float)

    total_response_time_ms = Column(Integer)

    status = Column(String(50))

    error_type = Column(String(200))

    created_at = Column(TIMESTAMP, default=datetime.utcnow)

class AIMulakatTaskLog(BaseModel):

    __tablename__ = "ai_mulakat_task_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    request_id = Column(String(100))

    task_name = Column(String(100))

    model_name = Column(String(100))

    duration_ms = Column(Integer)

    response_length = Column(Integer)

    status = Column(String(50))

    error_type = Column(String(100))

    error_message = Column(Text)

    created_at = Column(TIMESTAMP, default=datetime.utcnow)