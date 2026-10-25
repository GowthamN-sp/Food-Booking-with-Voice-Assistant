# Savora Django API

Backend for the Savora food-ordering portfolio application. The API uses Django, MySQL, signed expiring bearer tokens, a Groq-compatible OpenAI client for optional voice intent parsing, and Razorpay for online payments.

## Prerequisites

- Python 3.11 or 3.12
- MySQL 8.x (or a compatible MySQL deployment)
- Node.js/npm for the separate Vite frontend
- Razorpay Test Mode credentials only for payment testing

## Local setup on Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Edit `.env` with the generated `DJANGO_SECRET_KEY`, local MySQL credentials, and exact frontend origin. Keep `DEBUG=True` only for local development. `.env` is ignored by Git and must never be committed.

## Existing database and schema

This project started with legacy MySQL tables. The Django model declarations remain `managed = False` to avoid accidentally replacing existing data. Before using this patch with your database:

1. Back up the database.
2. Inspect table/column names in the backup and confirm `users`, `FoodItems`, and `orders` match the expected legacy schema.
3. Run `python manage.py migrate_savora_schema`.
4. Run `python manage.py check` and `python manage.py test app`.
5. Check `http://localhost:8000/health/`; proceed only if it returns `status: ok` and `schemaReady: true`.

The compatibility migration adds required columns and cart storage, and attempts to backfill order ownership only when it can read a `user_id` from legacy `customer_details`. Review unowned legacy orders manually. Do not run a production migration without a verified backup.

## Menu pricing

Run `python manage.py update_savora_market_prices` to preview indicative demo prices. It does not write changes unless `--apply` is supplied. These values are not live market quotes or a profitability calculation: validate the actual dish/portion, supplier costs, taxes and delivery-platform commission. Unclassified items remain unchanged for manual review. Back up the database and approve every proposed value before running `python manage.py update_savora_market_prices --apply`.

## Run the API

```powershell
python manage.py runserver 127.0.0.1:8000
```

## Main endpoints

- `GET /` — menu with caller-specific cart quantities
- `GET /health/` — database/schema readiness probe
- `POST /signup/`, `POST /login/`, `POST /logout/<user_id>/` — account session endpoints
- `POST /session-cart/`, `GET /session-cart/<session_id>/`, `DELETE /session-cart/clear/<session_id>/` — guest/account cart operations
- `POST /session-cart/transfer/` — atomically merge a guest cart after authentication
- `POST /update-quantity/<food_id>/` — authenticated cart update
- `POST /create-order/` — create order from product IDs and quantities; server calculates prices
- `POST /verify-payment/` — verify the Razorpay payment against the saved order
- `POST /razorpay/webhook/` — verify and reconcile Razorpay events
- `GET /orders/<user_id>/` — authenticated owner's orders
- `POST /update-order-status/<order_id>/` — admin-email-restricted fulfillment update
- `POST /voice/` — validated voice command interpretation; rule-based fallback works without Groq

## Security notes

- API auth uses a signed, expiring bearer token; logout increments a token version to revoke older tokens. This is a compact legacy-compatible approach, not a substitute for a full security review.
- The compatibility migration hashes legacy plaintext password values in-place; the existing login code retains a fallback for recovery if migration has not completed. Remove that fallback once all account records are confirmed migrated.
- Set `SAVORA_ADMIN_EMAILS` only to trusted, controlled email addresses.
- Keep Razorpay Key Secret and webhook secret on the backend, never in `VITE_*` variables.
- Rate-limit login/signup and voice endpoints at the reverse proxy/host. Use HTTPS, exact `ALLOWED_HOSTS`, exact `CORS_ALLOWED_ORIGINS`, secure deployment settings, database backups and monitoring.
- Do not accept a payment as successful based only on a frontend callback. Verify the signature, saved gateway order, amount/currency and captured status; configure signed webhooks in Razorpay Test Mode.

## Deployment

Set environment variables in the host dashboard, including `DJANGO_SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, DB settings, and optional Groq/Razorpay settings. Run with a WSGI server from this directory, e.g. `gunicorn Backend.wsgi:application --bind 0.0.0.0:${PORT:-8000}`. Use the platform's supported way to schedule `python manage.py expire_savora_pending_orders --minutes 30` every 10 minutes so abandoned payment reservations do not remain indefinitely.

**Release status:** source repairs and static Python syntax checks do not prove deployment readiness. Test against a backup/restored MySQL database and Razorpay Test Mode before deploying or accepting real payments.
