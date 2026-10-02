from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot

from .models import User, Service, Plan, Subscription, Payment, SherlockUsage
from .config import get_settings

UTC = timezone.utc


async def get_or_create_user(session: AsyncSession, tg_user: dict) -> User:
    result = await session.execute(
        select(User).where(User.telegram_id == int(tg_user["id"]))
    )
    user = result.scalar_one_or_none()

    now = datetime.now(UTC)

    if not user:
        user = User(
            telegram_id=int(tg_user["id"]),
            username=tg_user.get("username"),
            first_name=tg_user.get("first_name"),
            language=tg_user.get("language_code"),
            last_activity=now,
        )
        session.add(user)
    else:
        user.username = tg_user.get("username")
        user.first_name = tg_user.get("first_name")
        user.language = tg_user.get("language_code")
        user.last_activity = now

    await session.commit()
    await session.refresh(user)
    return user


async def seed_catalog(session: AsyncSession):
    result = await session.execute(select(Service).where(Service.slug == "sherlock"))
    service = result.scalar_one_or_none()

    if not service:
        service = Service(
            slug="sherlock",
            name="Sherlock",
            description="Интеллектуальный сервис ISK",
            sort_order=1,
        )
        session.add(service)
        await session.flush()

        session.add_all([
            Plan(
                service_id=service.id,
                slug="free",
                name="FREE",
                description="Базовый доступ",
                price_stars=0,
                duration_days=36500,
                is_subscription=False,
            ),
            Plan(
                service_id=service.id,
                slug="pro",
                name="PRO",
                description="Расширенный доступ",
                price_stars=299,
                duration_days=30,
                is_subscription=True,
            ),
            Plan(
                service_id=service.id,
                slug="ultra",
                name="ULTRA",
                description="Максимальный лимит",
                price_stars=599,
                duration_days=30,
                is_subscription=True,
            ),
        ])
        await session.commit()


async def active_sherlock_plan(session: AsyncSession, user_id: int) -> Plan | None:
    now = datetime.now(UTC)
    result = await session.execute(
        select(Plan)
        .join(Subscription, Subscription.plan_id == Plan.id)
        .where(
            Subscription.user_id == user_id,
            Subscription.service_id == Service.id,
            Service.slug == "sherlock",
            Subscription.status == "active",
            Subscription.expires_at > now,
            Plan.slug != "free",
        )
        .order_by(Plan.price_stars.desc())
    )
    return result.scalars().first()


async def activate_sherlock(
    session: AsyncSession,
    user_id: int,
    plan: Plan,
    telegram_subscription_id: str | None = None,
):
    now = datetime.now(UTC)
    result = await session.execute(
        select(Subscription)
        .where(
            Subscription.user_id == user_id,
            Subscription.service_id == plan.service_id,
            Subscription.status == "active",
        )
        .order_by(Subscription.expires_at.desc())
    )
    current = result.scalars().first()

    start = now
    if current and current.expires_at > now:
        start = current.expires_at

    expires = start + timedelta(days=plan.duration_days)

    if current:
        current.plan_id = plan.id
        current.expires_at = expires
        current.started_at = min(current.started_at, now)
        current.telegram_subscription_id = telegram_subscription_id
    else:
        session.add(
            Subscription(
                user_id=user_id,
                service_id=plan.service_id,
                plan_id=plan.id,
                status="active",
                started_at=now,
                expires_at=expires,
                auto_renew=bool(telegram_subscription_id),
                telegram_subscription_id=telegram_subscription_id,
            )
        )

    await session.commit()


async def make_payload(user_id: int, plan_id: int) -> str:
    return f"sherlock:{user_id}:{plan_id}:{uuid4().hex}"


def limit_for_plan(plan_slug: str) -> int:
    settings = get_settings()
    return {
        "free": settings.sherlock_daily_limit_free,
        "pro": settings.sherlock_daily_limit_pro,
        "ultra": settings.sherlock_daily_limit_ultra,
    }.get(plan_slug, settings.sherlock_daily_limit_free)
