import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    PreCheckoutQuery
)
from sqlalchemy import select

from .config import get_settings
from .db import SessionLocal
from .models import Plan
from .services import get_or_create_user, seed_catalog
from .payments import process_successful_payment

settings = get_settings()
bot = Bot(settings.bot_token)
dp = Dispatcher()


def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Открыть ISK", web_app={"url": settings.webapp_url})],
        [InlineKeyboardButton(text="🕵️ Sherlock", callback_data="sherlock")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
    ])


@dp.message(CommandStart())
async def start(message: Message):
    async with SessionLocal() as session:
        await get_or_create_user(session, {
            "id": message.from_user.id,
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
            "language_code": message.from_user.language_code,
        })
    await message.answer(
        "⚡ <b>ISK</b>\n\nМультисервисная платформа.\n\n"
        "Открой Mini App, чтобы пользоваться сервисами.",
        reply_markup=main_keyboard(),
    )


@dp.message(Command("plans"))
async def plans(message: Message):
    async with SessionLocal() as session:
        result = await session.execute(
            select(Plan).where(Plan.is_active == True).order_by(Plan.price_stars)
        )
        plans = result.scalars().all()

    text = ["🕵️ <b>SHERLOCK</b>", ""]
    for p in plans:
        text.append(f"<b>{p.name}</b> — {p.price_stars} ⭐ / {p.duration_days} дней")
        text.append(p.description)
        text.append("")
    await message.answer("\n".join(text))


@dp.message(Command("profile"))
async def profile(message: Message):
    async with SessionLocal() as session:
        user = await get_or_create_user(session, {
            "id": message.from_user.id,
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
            "language_code": message.from_user.language_code,
        })
    await message.answer(
        f"👤 <b>Профиль</b>\n\n"
        f"ID: <code>{user.telegram_id}</code>\n"
        f"Username: @{user.username or '—'}"
    )


@dp.callback_query(F.data == "sherlock")
async def sherlock_callback(callback):
    await callback.message.answer(
        "🕵️ Sherlock\n\nОткрой Mini App для выбора тарифа.",
        reply_markup=main_keyboard(),
    )
    await callback.answer()


@dp.callback_query(F.data == "profile")
async def profile_callback(callback):
    await profile(callback.message)
    await callback.answer()


@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    # Для production здесь стоит дополнительно проверить payload,
    # пользователя и ожидаемую сумму в БД.
    await query.answer(ok=True)


@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    payment = message.successful_payment

    async with SessionLocal() as session:
        ok, status = await process_successful_payment(
            bot=bot,
            session=session,
            telegram_user_id=message.from_user.id,
            payload=payment.invoice_payload,
            total_amount=payment.total_amount,
            currency=payment.currency,
            telegram_charge_id=payment.telegram_payment_charge_id,
            provider_charge_id=getattr(payment, "provider_payment_charge_id", None),
        )

    if ok:
        await message.answer(
            "✅ <b>Оплата подтверждена.</b>\n\n"
            "Доступ активирован. Открой ISK для продолжения."
        )
    else:
        logging.error("Payment processing failed: %s", status)
        await message.answer(
            "⚠️ Платёж получен, но автоматическая активация не завершилась. "
            "Обратись в поддержку."
        )


async def start_bot():
    async with SessionLocal() as session:
        await seed_catalog(session)

    logging.basicConfig(level=settings.log_level)
    await dp.start_polling(bot)
