import asyncio
from sqlalchemy import text
from core.db import engine

async def main():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        print("DB_OK:", result.scalar_one())

asyncio.run(main())