from datetime import datetime, timezone
from aiogram import Bot
from aiogram.types import LabeledPrice
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Plan, Payment
from .services import make_payload, activate_sherlock

UTC = timezone.utc


async def create_sherlock_invoice(
    bot: Bot,
    session: AsyncSession,
    user_id: int,
    plan: Plan,
) -> str:
    payload = await make_payload(user_id, plan.id)

    # Для Telegram Stars provider_token должен быть пустым.
    # subscription_period=2592000 (30 дней) можно включить,
    # если нужна именно Telegram-сторонняя автопродляемая Stars-подписка.
    # В MVP оставляем обычную 30-дневную покупку, чтобы не смешивать
    # entitlement ISK и Telegram recurring state.
    link = await bot.create_invoice_link(
        title=f"ISK {plan.name}",
        description=f"Доступ Sherlock {plan.name} на {plan.duration_days} дней",
        payload=payload,
        currency="XTR",
        prices=[LabeledPrice(label=plan.name, amount=plan.price_stars)],
    )

    session.add(
        Payment(
            user_id=user_id,
            payload=payload,
            product_type="sherlock_plan",
            product_id=plan.id,
            amount_stars=plan.price_stars,
            currency="XTR",
            status="pending",
        )
    )
    await session.commit()

    return link


async def process_successful_payment(
    bot,
    session: AsyncSession,
    telegram_user_id: int,
    payload: str,
    total_amount: int,
    currency: str,
    telegram_charge_id: str,
    provider_charge_id: str | None,
):
    result = await session.execute(
        select(Payment).where(Payment.payload == payload)
    )
    payment = result.scalar_one_or_none()

    if not payment:
        return False, "payment_not_found"

    if payment.status == "paid":
        return True, "already_processed"

    if payment.user_id != telegram_user_id:
        return False, "user_mismatch"

    if currency != "XTR" or total_amount != payment.amount_stars:
        return False, "amount_or_currency_mismatch"

    duplicate = await session.execute(
        select(Payment).where(Payment.telegram_charge_id == telegram_charge_id)
    )
    if duplicate.scalar_one_or_none():
        return True, "duplicate_charge"

    payment.status = "paid"
    payment.telegram_charge_id = telegram_charge_id
    payment.provider_charge_id = provider_charge_id
    payment.completed_at = datetime.now(UTC)

    if payment.product_type == "sherlock_plan":
        result = await session.execute(
            select(Plan).where(Plan.id == payment.product_id)
        )
        plan = result.scalar_one()
        await activate_sherlock(session, payment.user_id, plan)

    await session.commit()
    return True, "processed"
