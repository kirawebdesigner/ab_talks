from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: tuple[int, ...]
    product_name: str
    product_description: str
    product_price: str
    payment_instructions: str
    telebirr_number: str
    bank_account_name: str
    bank_account_number: str
    delivery_message: str
    database_path: str
    public_base_url: str
    webhook_path: str
    webhook_secret: str
    port: int


def _parse_admin_ids(raw: str) -> tuple[int, ...]:
    admin_ids: list[int] = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            admin_ids.append(int(item))
        except ValueError as exc:
            raise RuntimeError(f"ADMIN_IDS contains a non-numeric id: {item}") from exc
    return tuple(admin_ids)


def load_config() -> Config:
    load_dotenv()
    return Config(
        bot_token=os.getenv("BOT_TOKEN", "missing-token").strip(),
        admin_ids=_parse_admin_ids(os.getenv("ADMIN_IDS", "")),
        product_name=os.getenv("PRODUCT_NAME", "Digital Product").strip(),
        product_description=os.getenv("PRODUCT_DESCRIPTION", "").strip(),
        product_price=os.getenv("PRODUCT_PRICE", "").strip(),
        payment_instructions=os.getenv("PAYMENT_INSTRUCTIONS", "").strip(),
        telebirr_number=os.getenv("TELEBIRR_NUMBER", "").strip(),
        bank_account_name=os.getenv("BANK_ACCOUNT_NAME", "").strip(),
        bank_account_number=os.getenv("BANK_ACCOUNT_NUMBER", "").strip(),
        delivery_message=os.getenv("DELIVERY_MESSAGE", "Payment confirmed.").strip(),
        database_path=os.getenv("DATABASE_PATH", "orders.db").strip(),
        public_base_url=os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/"),
        webhook_path=os.getenv("WEBHOOK_PATH", "/telegram/webhook").strip(),
        webhook_secret=os.getenv("WEBHOOK_SECRET", "").strip(),
        port=int(os.getenv("PORT", "9090")),
    )
