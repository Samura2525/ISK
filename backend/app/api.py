from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import telegram_user
from .bot import bot
from .db import get_session
from .models import User, Service, Plan, Subscription, Payment
from .payments import create_sherlock_invoice
from .services import get_or_create_user, active_sherlock_plan
from .sherlock import execute_sherlock

router = APIRouter(prefix="/api/v1")
UTC = timezone.utc


class SherlockQuery(BaseModel):
    query: str = Field(min_length=1, max_length=2000)


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/me")
async def me(
    tg_user=Depends(telegram_user),
    session: AsyncSession = Depends(get_session),
):
    user = await get_or_create_user(session, tg_user)
    plan = await active_sherlock_plan(session, user.id)

    return {
        "telegram_id": user.telegram_id,
        "username": user.username,
        "first_name": user.first_name,
        "sherlock_plan": plan.slug if plan else "free",
    }


@router.get("/services")
async def services(
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Service)
        .where(Service.is_active == True)
        .order_by(Service.sort_order)
    )
    return [
        {
            "slug": x.slug,
            "name": x.name,
            "description": x.description,
        }
        for x in result.scalars().all()
    ]


@router.get("/sherlock/plans")
async def sherlock_plans(
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Plan)
        .join(Service)
        .where(Service.slug == "sherlock", Plan.is_active == True)
        .order_by(Plan.price_stars)
    )
    return [
        {
            "id": p.id,
            "slug": p.slug,
            "name": p.name,
            "description": p.description,
            "price_stars": p.price_stars,
            "duration_days": p.duration_days,
        }
        for p in result.scalars().all()
    ]


@router.post("/sherlock/invoice")
async def sherlock_invoice(
    plan_id: int,
    tg_user=Depends(telegram_user),
    session: AsyncSession = Depends(get_session),
):
    user = await get_or_create_user(session, tg_user)

    result = await session.execute(
        select(Plan)
        .join(Service)
        .where(
            Plan.id == plan_id,
            Plan.is_active == True,
            Service.slug == "sherlock",
        )
    )
    plan = result.scalar_one_or_none()

    if not plan or plan.slug == "free":
        raise HTTPException(400, "This plan is not purchasable")

    link = await create_sherlock_invoice(bot, session, user.id, plan)
    return {"invoice_url": link}


@router.post("/sherlock/query")
async def sherlock_query(
    body: SherlockQuery,
    tg_user=Depends(telegram_user),
    session: AsyncSession = Depends(get_session),
):
    user = await get_or_create_user(session, tg_user)

    ok, answer = await execute_sherlock(session, user.id, body.query)
    if not ok:
        raise HTTPException(429, answer)

    return {"answer": answer}


@router.get("/subscriptions")
async def subscriptions(
    tg_user=Depends(telegram_user),
    session: AsyncSession = Depends(get_session),
):
    user = await get_or_create_user(session, tg_user)
    result = await session.execute(
        select(Subscription, Plan, Service)
        .join(Plan, Subscription.plan_id == Plan.id)
        .join(Service, Subscription.service_id == Service.id)
        .where(Subscription.user_id == user.id)
        .order_by(desc(Subscription.expires_at))
    )

    return [
        {
            "service": service.slug,
            "plan": plan.slug,
            "status": sub.status,
            "started_at": sub.started_at,
            "expires_at": sub.expires_at,
            "auto_renew": sub.auto_renew,
        }
        for sub, plan, service in result.all()
    ]


@router.get("/payments")
async def payments(
    tg_user=Depends(telegram_user),
    session: AsyncSession = Depends(get_session),
):
    user = await get_or_create_user(session, tg_user)
    result = await session.execute(
        select(Payment)
        .where(Payment.user_id == user.id)
        .order_by(desc(Payment.created_at))
        .limit(50)
    )

    return [
        {
            "id": p.id,
            "product_type": p.product_type,
            "amount_stars": p.amount_stars,
            "currency": p.currency,
            "status": p.status,
            "created_at": p.created_at,
            "completed_at": p.completed_at,
        }
        for p in result.scalars().all()
    ]
