# Single Product Telegram Sales Bot

This is a simple Telegram bot for selling one digital product with manual Ethiopian payment verification.

## Flow

1. Customer opens the bot from a Telegram channel.
2. Bot shows the product, price, Telebirr/bank details, and a `Buy now` button.
3. Customer sends name, phone number, and payment screenshot.
4. Seller/admin receives the order inside Telegram.
5. Admin taps `Approve` or `Reject`.
6. If approved, the customer automatically receives the configured delivery message.
7. If rejected, the admin sends a reason and the bot forwards it to the customer.

## Setup

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token.
2. Copy `.env.example` to `.env`.
3. Fill in:
   - `BOT_TOKEN`
   - `ADMIN_IDS`
   - product details
   - payment numbers
   - `DELIVERY_MESSAGE`
4. Install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

5. Run the bot:

```powershell
python bot.py
```

## Deploy on Choreo

This project includes a Dockerfile and `.choreo/component.yaml`, so create a Choreo service from this Git repository using the Dockerfile build path.

Choreo expects the service endpoint details in `.choreo/component.yaml` for Dockerfile/Python services. The endpoint is public, REST, base path `/`, and port `9090`.

Set these environment variables in Choreo before deployment:

```env
BOT_TOKEN=your_botfather_token
ADMIN_IDS=7711678340
PRODUCT_NAME=FM26
PRODUCT_DESCRIPTION=Digital download delivered after payment confirmation.
PRODUCT_PRICE=500 ETB
PAYMENT_INSTRUCTIONS=Pay with Telebirr or bank transfer, then send your name, phone number, and payment screenshot.
TELEBIRR_NUMBER=09xxxxxxxx
BANK_ACCOUNT_NAME=Seller Name
BANK_ACCOUNT_NUMBER=1000xxxxxxxx
DELIVERY_MESSAGE=Payment confirmed. Download link: https://example.com/download
PUBLIC_BASE_URL=https://your-choreo-public-service-url
WEBHOOK_PATH=/telegram/webhook
WEBHOOK_SECRET=choose-a-random-secret
DATABASE_PATH=/tmp/orders.db
```

After Choreo deploys, open the public service URL in the browser. `/health` should return `{"status":"healthy"}`. On startup, the bot sets its Telegram webhook to:

```text
PUBLIC_BASE_URL + WEBHOOK_PATH
```

For the first Choreo deploy, you usually need to deploy once, copy the generated public service URL, set `PUBLIC_BASE_URL`, then redeploy so Telegram receives the correct webhook URL.

## Getting Admin IDs

Send any message to [@userinfobot](https://t.me/userinfobot) from the seller/admin Telegram account. Put the numeric id in `ADMIN_IDS`.

For multiple admins, separate ids with commas:

```env
ADMIN_IDS=123456789,987654321
```

## Notes

- The bot stores orders in SQLite using `orders.db` by default.
- In Choreo, use `DATABASE_PATH=/tmp/orders.db` for the demo. This is temporary container storage, so use Choreo storage or a managed database before handling real customers.
- Payment checking is manual. The bot does not connect to Telebirr or banks.
- Only sell products the seller has permission to distribute.
