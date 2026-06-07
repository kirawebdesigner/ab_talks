from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request
from telegram import Update

from bot import CONFIG, build_application

logger = logging.getLogger(__name__)
telegram_app = build_application()
telegram_ready = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    del app
    global telegram_ready
    try:
        await telegram_app.initialize()
        await telegram_app.start()
        if CONFIG.public_base_url:
            await telegram_app.bot.set_webhook(
                url=f"{CONFIG.public_base_url}{CONFIG.webhook_path}",
                secret_token=CONFIG.webhook_secret or None,
                allowed_updates=Update.ALL_TYPES,
            )
        telegram_ready = True
        logger.info("Telegram bot started")
    except Exception:
        telegram_ready = False
        logger.exception("Telegram bot startup failed")
    yield
    if telegram_ready:
        await telegram_app.stop()
        await telegram_app.shutdown()


app = FastAPI(title="Single Product Telegram Sales Bot", lifespan=lifespan)


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok", "service": "telegram-sales-bot"}


@app.get("/health")
async def health() -> dict[str, str | bool]:
    return {
        "status": "healthy",
        "telegram_ready": telegram_ready,
        "has_bot_token": CONFIG.bot_token != "missing-token",
        "has_admin_ids": bool(CONFIG.admin_ids),
        "has_public_base_url": bool(CONFIG.public_base_url),
        "has_delivery_message": bool(CONFIG.delivery_message),
    }


@app.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, bool]:
    if not telegram_ready:
        raise HTTPException(status_code=503, detail="Telegram bot is not ready")

    if CONFIG.webhook_secret and x_telegram_bot_api_secret_token != CONFIG.webhook_secret:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")

    update = Update.de_json(await request.json(), telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}
