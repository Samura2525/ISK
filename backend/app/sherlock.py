import time
from uuid import uuid4
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from .models import SherlockUsage, Plan
from .services import active_sherlock_plan, limit_for_plan


class SherlockProvider:
    async def run(self, query: str) -> str:
        # Заменяется реальным AI/search provider.
        return (
            "DEMO SHERLOCK\n\n"
            f"Получен запрос:\n{query}\n\n"
            "Это демонстрационный ответ. Подключи реальный provider "
            "в app/sherlock.py, сохранив тот же интерфейс."
        )


provider = SherlockProvider()


async def execute_sherlock(
    session: AsyncSession,
    user_id: int,
    query: str,
) -> tuple[bool, str]:
    plan = await active_sherlock_plan(session, user_id)
    plan_slug = plan.slug if plan else "free"
    limit = limit_for_plan(plan_slug)

    result = await session.execute(
        select(func.count(SherlockUsage.id)).where(
            SherlockUsage.user_id == user_id,
            SherlockUsage.created_at >= func.current_date(),
            SherlockUsage.status == "success",
        )
    )
    used = result.scalar_one()

    if used >= limit:
        return False, f"Лимит {plan_slug.upper()}: {limit} запросов в сутки."

    started = time.perf_counter()
    answer = await provider.run(query)
    elapsed = int((time.perf_counter() - started) * 1000)

    session.add(
        SherlockUsage(
            user_id=user_id,
            request_id=uuid4().hex,
            provider="demo",
            status="success",
            execution_ms=elapsed,
        )
    )
    await session.commit()

    return True, answer
