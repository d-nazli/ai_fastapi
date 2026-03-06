import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

from models.ai_log import AIMulakatRequestLog, AIMulakatTaskLog


class AILogService:

    # -----------------------------
    # REQUEST LOG OLUŞTUR
    # -----------------------------
    async def create_request_log(
        self,
        db: AsyncSession,
        user_id: str,
        endpoint: str,
        model_name: str,
        transcript_length: int,
        prompt_length: int,
        temperature: float
    ) -> str:

        request_id = str(uuid.uuid4())

        log = AIMulakatRequestLog(
            request_id=request_id,
            user_id=user_id,
            endpoint=endpoint,
            model_name=model_name,
            transcript_length=transcript_length,
            prompt_length=prompt_length,
            temperature=temperature,
            status="STARTED"
        )

        db.add(log)
        await db.commit()

        return request_id


    # -----------------------------
    # TASK LOG YAZ
    # -----------------------------
    async def create_task_log(
        self,
        db: AsyncSession,
        request_id: str,
        task_name: str,
        model_name: str,
        duration_ms: int,
        response_length: int,
        status: str,
        error_type: str | None = None,
        error_message: str | None = None
    ):

        log = AIMulakatTaskLog(
            request_id=request_id,
            task_name=task_name,
            model_name=model_name,
            duration_ms=duration_ms,
            response_length=response_length,
            status=status,
            error_type=error_type,
            error_message=error_message
        )

        db.add(log)
        await db.commit()


    # -----------------------------
    # REQUEST LOG GÜNCELLE
    # -----------------------------
    async def update_request_log(
        self,
        db: AsyncSession,
        request_id: str,
        status: str,
        total_response_time_ms: int,
        error_type: str | None = None
    ):

        stmt = (
            update(AIMulakatRequestLog)
            .where(AIMulakatRequestLog.request_id == request_id)
            .values(
                status=status,
                total_response_time_ms=total_response_time_ms,
                error_type=error_type
            )
        )

        await db.execute(stmt)
        await db.commit()


# global instance
ai_log_service = AILogService()