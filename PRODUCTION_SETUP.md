# Savora — setup, migration, validation and deployment

Savora is a portfolio-ready food ordering application built from React + Vite, Django, MySQL, Groq-powered voice command interpretation, browser speech recognition/TTS, and an optional Razorpay checkout. This guide documents the complete patch's expectations. Do not accept live payments until the test checklist has passed.

## Important before you patch

1. Back up the whole project.
2. Back up the existing MySQL database (for example, with `mysqldump`) and confirm the backup file is readable.
3. Never put `.env`, MySQL passwords, Groq keys, or Razorpay secrets in GitHub.
4. The pricing command proposes illustrative mid-range Bengaluru demo prices. It is not a live quote from restaurants and is not a cost/margin analysis. Review every row before applying it.

## Project structure

```text
FoodApp/
  Backend/
    Backend/                     # Django settings, URLs, WSGI/ASGI
    app/                          # API views, legacy unmanaged models, commands, tests
    manage.py
    requirements.txt
    .env.example                  # Safe template only; copy to .env locally
  FrontEnd/
    public/                       # Public images and SVG fallbacks
    src/components/               # Pages and shared UI
    src/context/                  # Auth/cart state
    src/styles/                   # Savora design system
    src/utils/currency.js         # INR formatting
    .env.example                  # Vite public API URL only
    package.json
    index.html
  .gitignore
  PRODUCTION_SETUP.md
```

## Local setup (Windows PowerShell)

### 1. Backend environment

Open PowerShell in `FoodApp\Backend`:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `Backend\.env` with your own MySQL credentials and local settings. Generate a real random Django secret:

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Paste that value into `DJANGO_SECRET_KEY`. For local development only, keep `DEBUG=True`, `ALLOWED_HOSTS=localhost,127.0.0.1`, and `CORS_ALLOWED_ORIGINS=http://localhost:5173`. Do not use the sample placeholder values outside local development.

### 2. Prepare the existing MySQL schema

**Take a database backup first.** This project began with legacy tables marked `managed = False`, so the included compatibility command deliberately alters existing MySQL tables rather than pretending a fresh Django migration owns them.

```powershell
python manage.py migrate_savora_schema
python manage.py check
```

The command adds the missing order ownership/payment fields, a token revocation version, `FoodItems.TrackInventory`, cart table/index if missing, expands a too-short password column where necessary, hashes legacy plaintext passwords in place, and attempts a careful order-owner backfill from legacy `customer_details` JSON. Review its output. Password hashes remain compatible with existing passwords, but still take a backup first. Legacy orders that cannot be tied to a user are not automatically assigned to anyone.

The updated login/API code requires this schema command to complete successfully before you use it. Check the health endpoint at `http://localhost:8000/health/`; it must report `status: ok` and `schemaReady: true`.

### 3. Review menu prices

First run a **dry run** (no database values change):

```powershell
python manage.py update_savora_market_prices
```

Review every `PREVIEW` line. These are suggested portfolio/demo prices in rupees, not verified live local prices. Confirm serving size, ingredient costs, taxes, and nearby competitor prices. Then back up the database again if necessary and explicitly apply the suggestions:

```powershell
python manage.py update_savora_market_prices --apply
```

Unclassified menu items are shown for manual review and are left unchanged. This command changes only `FoodItems.Price`; it does not modify your schema.

Optionally seed additional example dishes if you need them:

```powershell
python manage.py seed_food_items
```

Review the inserted image paths. Images should exist under `FrontEnd/public/food/` and database `ImageName` values should start with `/food/`.

### 4. Start Django

```powershell
python manage.py runserver 127.0.0.1:8000
```

For local smoke testing, the API base URL is `http://localhost:8000`.

### 5. Frontend environment and build

In another PowerShell window:

```powershell
cd ..\FrontEnd
Copy-Item .env.example .env
npm ci
npm run lint
npm run build
npm run dev
```

Open the Vite URL, normally `http://localhost:5173`. `VITE_API_BASE_URL` is public frontend configuration, not a place for secrets. Restart Vite after changing `.env`.

## Login, cart, routes and page behaviour

- `/` is the public Savora landing page and menu. Guests can browse and use a session-scoped cart.
- `/about` is public.
- `/cart` is accessible to guests. Checkout redirects guests to `/login`; after sign-in the app returns to the intended page.
- `/login` provides sign-in and account creation. Existing legacy plain-text passwords are upgraded to Django password hashes when the correct password is used; monitor and remove legacy password support after the migration window.
- `/orders` and `/profile` require a valid signed token. Tokens expire after 12 hours; logout increments a server-side token version to invalidate prior tokens.
- Unknown paths use a branded not-found page.
- Cart quantities are kept in `session_carts`, separate from the shared `FoodItems` catalogue. Guest cart transfer is an atomic server endpoint so failed transfers do not partially duplicate the cart.
- Order totals are recalculated on the server from current database prices. A supplied browser total/price is never trusted.

## Inventory semantics

The compatibility migration adds `FoodItems.TrackInventory`. Existing rows with `Stock > 0` are marked as tracked; old rows at zero remain untracked until you explicitly decide to track them. When `TrackInventory = 1`, the backend validates stock even when `Stock = 0`, reserves stock during order creation, and releases it on failed/expired/cancelled orders. This prevents the last sold-out unit from becoming accidentally “untracked.” Seeded example rows opt into stock tracking.

Schedule abandoned Razorpay order cleanup every 10 minutes on your host (or use a scheduled task):

```powershell
python manage.py expire_savora_pending_orders --minutes 30
```

Use a scheduler/cron in the deployed environment; do not depend on a user keeping a page open.

## Razorpay test-mode setup

The payment integration is deliberately disabled until backend test credentials are supplied.

1. In the Razorpay Dashboard, switch to **Test Mode** and obtain the test Key ID and Key Secret.
2. Put `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` only in the backend environment. Never put the secret in `VITE_*` variables or committed files.
3. Enable automatic capture in the Razorpay dashboard for this integration, or separately implement and test an explicit capture call. Savora checks for `captured` status before treating payment as complete.
4. Expose your backend HTTPS URL for webhook delivery. Configure the webhook URL as `https://YOUR_API_DOMAIN/razorpay/webhook/`; subscribe at minimum to `payment.captured` and `payment.failed`, set a high-entropy webhook secret, and place it in `RAZORPAY_WEBHOOK_SECRET`. Configure Test Mode webhooks separately from Live Mode.
5. Run end-to-end tests with test keys: successful payment, failed payment, dismissed checkout, expired pending order, duplicate webhook delivery, amount mismatch, invalid signature, cross-user order verification, and COD.
6. Check both Savora's order page and the Razorpay Test Mode dashboard for the captured state. Do not fulfill an online order from the browser callback alone; payment status is verified server-side and reconciled through signed webhooks.

Razorpay's official docs require server-created Orders, server-side signature verification, checking payment capture status, and testing with Test Mode keys before live payments: https://razorpay.com/docs/server-integration/python/test-app/ and https://razorpay.com/docs/webhooks/ .

## Deploying to GitHub and a host

### Git hygiene

From the repository root:

```powershell
git status --short
git check-ignore FoodApp\Backend\.env FoodApp\FrontEnd\.env
```

Confirm that real `.env` files and keys are ignored and are not in `git status`. If a secret has ever been committed, rotate it even if you later remove it from the file.

If `FoodApp` is a Git submodule, first commit and push changes from inside `FoodApp`, then commit the updated submodule reference in the outer repository. A plain outer-repository push does not upload unpushed submodule changes.

### Backend host variables

Set environment variables in your host dashboard (do not commit them):

- `DJANGO_SECRET_KEY`: unique random secret
- `DEBUG=False`
- `ALLOWED_HOSTS`: backend hostname(s), no scheme
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- `CORS_ALLOWED_ORIGINS`: exact frontend origin(s), including `https://`
- `GROQ_API_KEY` and `GROQ_MODEL` if AI voice parsing is enabled
- `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` only after Test Mode passes
- `SAVORA_ADMIN_EMAILS`: comma-separated trusted admin emails for order status changes
- For HTTPS production, configure `SECURE_SSL_REDIRECT=True`, `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`, and review HSTS with your host/proxy setup.

Run the compatibility schema command once against a backed-up production database before switching traffic. Do not run sample price updates against production without human approval.

A typical Linux process command is:

```bash
gunicorn Backend.wsgi:application --bind 0.0.0.0:${PORT:-8000}
```

Use the path above with the working directory set to `FoodApp/Backend`. Ensure the host provides MySQL and installs `mysqlclient` build/runtime prerequisites. The frontend can be deployed as a static Vite site with `VITE_API_BASE_URL` set at build time. Redeploy/rebuild the frontend whenever that variable changes.

## Verification checklist

- [ ] `python manage.py check` succeeds.
- [ ] `/health/` reports schema ready.
- [ ] `python manage.py test app` passes.
- [ ] `npm run lint` succeeds.
- [ ] `npm run build` succeeds.
- [ ] New account password is stored as a hash, not plaintext.
- [ ] Incorrect password is rejected; logout invalidates the previous token.
- [ ] Guest carts are isolated; guest cart transfer works once without duplicates.
- [ ] User A cannot retrieve/update User B's orders or cart.
- [ ] Zero/unavailable prices are blocked at checkout; API ignores a fake client price/total.
- [ ] Stock-reserved quantities are restored for failed/expired/cancelled orders.
- [ ] COD order creation and status transitions work.
- [ ] Razorpay Test Mode success, failure, cancellation, signature, amount, captured status, and webhook paths pass.
- [ ] Mobile layouts, 404 navigation, voice text fallback, speech-permission errors, and keyboard use work.

## Remaining environment-dependent validation

This patch cannot access your actual MySQL data, Razorpay Dashboard, Groq credentials, DNS/hosting environment, or browser on your Windows machine. The code must still be run through the checklist above before calling the deployment production-ready. In particular, the example market prices need review, the database schema migration needs a backup and real execution, and Razorpay webhooks must be configured for the deployed HTTPS URL.
