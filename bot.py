from __future__ import annotations

import logging
from enum import IntEnum

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import Config, load_config
from storage import Order, OrderStore

logging.basicConfig(
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class CheckoutState(IntEnum):
    NAME = 1
    PHONE = 2
    SCREENSHOT = 3


CONFIG: Config = load_config()
STORE = OrderStore(CONFIG.database_path)
PENDING_REJECTIONS: dict[int, int] = {}


def _is_admin(user_id: int | None) -> bool:
    return user_id in CONFIG.admin_ids


def _product_text() -> str:
    payment_lines = [
        f"<b>{CONFIG.product_name}</b>",
        CONFIG.product_description,
        "",
        f"<b>Price:</b> {CONFIG.product_price}",
        "",
        "<b>Payment</b>",
        CONFIG.payment_instructions,
        f"Telebirr: <code>{CONFIG.telebirr_number}</code>",
        f"Bank name: <code>{CONFIG.bank_account_name}</code>",
        f"Bank account: <code>{CONFIG.bank_account_number}</code>",
    ]
    return "\n".join(line for line in payment_lines if line is not None)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    keyboard = [[InlineKeyboardButton("Buy now", callback_data="buy")]]
    await update.effective_message.reply_text(
        _product_text(),
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def begin_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.message.reply_text("Send your full name.")
    return CheckoutState.NAME


async def collect_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.effective_message.text.strip()
    if len(name) < 2:
        await update.effective_message.reply_text("Please send your full name.")
        return CheckoutState.NAME
    context.user_data["name"] = name
    await update.effective_message.reply_text("Send your phone number.")
    return CheckoutState.PHONE


async def collect_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    phone = update.effective_message.text.strip()
    if len(phone) < 7:
        await update.effective_message.reply_text("Please send a valid phone number.")
        return CheckoutState.PHONE
    context.user_data["phone"] = phone
    await update.effective_message.reply_text("Upload the payment screenshot as a photo.")
    return CheckoutState.SCREENSHOT


async def collect_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    photo = update.effective_message.photo[-1]
    order = STORE.create_order(
        customer_chat_id=update.effective_chat.id,
        customer_user_id=user.id if user else None,
        customer_username=user.username if user else None,
        name=context.user_data["name"],
        phone=context.user_data["phone"],
        screenshot_file_id=photo.file_id,
    )
    await update.effective_message.reply_text(
        f"Order #{order.id} received. The seller will review your payment and reply here."
    )
    await _notify_admins(context, order)
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.effective_message.reply_text("Order cancelled. Send /start when you are ready.")
    return ConversationHandler.END


async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if not _is_admin(update.effective_user.id):
        await update.effective_message.reply_text("This command is only for admins.")
        return
    orders = STORE.list_pending()
    if not orders:
        await update.effective_message.reply_text("No pending orders.")
        return
    for order in orders:
        await update.effective_message.reply_photo(
            photo=order.screenshot_file_id,
            caption=_admin_caption(order),
            parse_mode=ParseMode.HTML,
            reply_markup=_admin_keyboard(order.id),
        )


async def handle_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id if query.from_user else None
    if not _is_admin(user_id):
        await query.answer("Admins only.", show_alert=True)
        return

    action, raw_order_id = query.data.split(":", 1)
    order_id = int(raw_order_id)

    if action == "approve":
        order = STORE.set_status(order_id, "approved")
        await context.bot.send_message(order.customer_chat_id, CONFIG.delivery_message)
        await query.answer("Approved.")
        await query.edit_message_caption(
            caption=f"{_admin_caption(order)}\n\n<b>Status:</b> approved",
            parse_mode=ParseMode.HTML,
        )
        return

    if action == "reject":
        PENDING_REJECTIONS[user_id] = order_id
        await query.answer("Send the rejection reason.")
        await query.message.reply_text(
            f"Send the reason for rejecting order #{order_id}. Use /cancel to stop."
        )


async def collect_rejection_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    user_id = update.effective_user.id
    if not _is_admin(user_id) or user_id not in PENDING_REJECTIONS:
        return
    reason = update.effective_message.text.strip()
    if not reason:
        await update.effective_message.reply_text("Send a short reason, or /cancel to stop.")
        return
    order_id = PENDING_REJECTIONS.pop(user_id)
    order = STORE.set_status(order_id, "rejected", reason)
    await update.effective_message.reply_text(f"Order #{order.id} rejected.")
    await update.get_bot().send_message(
        order.customer_chat_id,
        f"Order #{order.id} was rejected.\n\nReason: {reason}\n\nPlease contact the seller if this is a mistake.",
    )


async def cancel_admin_rejection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if update.effective_user:
        PENDING_REJECTIONS.pop(update.effective_user.id, None)
    await update.effective_message.reply_text("Cancelled.")


async def _notify_admins(context: ContextTypes.DEFAULT_TYPE, order: Order) -> None:
    for admin_id in CONFIG.admin_ids:
        try:
            await context.bot.send_photo(
                chat_id=admin_id,
                photo=order.screenshot_file_id,
                caption=_admin_caption(order),
                parse_mode=ParseMode.HTML,
                reply_markup=_admin_keyboard(order.id),
            )
        except Exception:
            logger.exception("Could not notify admin %s for order %s", admin_id, order.id)


def _admin_caption(order: Order) -> str:
    username = f"@{order.customer_username}" if order.customer_username else "No username"
    return (
        f"<b>New order #{order.id}</b>\n"
        f"Product: {CONFIG.product_name}\n"
        f"Name: {order.name}\n"
        f"Phone: <code>{order.phone}</code>\n"
        f"Telegram: {username}\n"
        f"Status: {order.status}"
    )


def _admin_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Approve", callback_data=f"approve:{order_id}"),
                InlineKeyboardButton("Reject", callback_data=f"reject:{order_id}"),
            ]
        ]
    )


def build_application() -> Application:
    application = Application.builder().token(CONFIG.bot_token).build()

    checkout = ConversationHandler(
        entry_points=[CallbackQueryHandler(begin_checkout, pattern="^buy$")],
        states={
            CheckoutState.NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_name)],
            CheckoutState.PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_phone)],
            CheckoutState.SCREENSHOT: [MessageHandler(filters.PHOTO, collect_screenshot)],
        },
        fallbacks=[CommandHandler("cancel", cancel_checkout)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("orders", admin_orders))
    application.add_handler(checkout)
    application.add_handler(CommandHandler("cancel", cancel_admin_rejection))
    application.add_handler(CallbackQueryHandler(handle_admin_action, pattern="^(approve|reject):"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, collect_rejection_reason))
    return application


def main() -> None:
    application = build_application()
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
