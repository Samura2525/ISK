import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl, unquote

from fastapi import HTTPException, Header
from .config import get_settings


def validate_telegram_init_data(init_data: str, max_age: int = 86400) -> dict:
    if not init_data:
        raise HTTPException(401, "Missing Telegram initData")

    settings = get_settings()
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)

    if not received_hash:
        raise HTTPException(401, "Missing Telegram hash")

    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(pairs.items())
    )

    secret_key = hmac.new(
        b"WebAppData",
        settings.bot_token.encode(),
        hashlib.sha256,
    ).digest()

    calculated = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(calculated, received_hash):
        raise HTTPException(401, "Invalid Telegram initData")

    auth_date = int(pairs.get("auth_date", "0"))
    if time.time() - auth_date > max_age:
        raise HTTPException(401, "Expired Telegram initData")

    user_raw = pairs.get("user")
    if not user_raw:
        raise HTTPException(401, "Telegram user missing")

    try:
        user = json.loads(unquote(user_raw))
    except json.JSONDecodeError:
        raise HTTPException(401, "Invalid Telegram user data")

    return user


async def telegram_user(
    x_telegram_init_data: str = Header(default="", alias="X-Telegram-Init-Data")
):
    return validate_telegram_init_data(x_telegram_init_data)
