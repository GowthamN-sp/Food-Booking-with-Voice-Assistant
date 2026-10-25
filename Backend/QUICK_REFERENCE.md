# Savora quick reference

## Local setup

```powershell
# From FoodApp/Backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Set a generated DJANGO_SECRET_KEY and local MySQL credentials in .env
python manage.py migrate_savora_schema
python manage.py check
python manage.py test app
python manage.py runserver 127.0.0.1:8000
```

Before using the migration command, create and verify a MySQL backup. Review and explicitly approve the demo price proposals before `python manage.py update_savora_market_prices --apply`.

## Frontend checks

```powershell
# From FoodApp/FrontEnd
npm ci
npm run lint
npm run build
npm run dev
```

## Must not be skipped before hosting

- `Backend/.env` and `FrontEnd/.env` are local-only; never commit secrets.
- Replace any exposed/committed credential and rotate the original secret.
- Set production `DEBUG=False`, a unique secret, exact allowed hosts/CORS origins, HTTPS settings and deployment secrets.
- Run Django tests and frontend lint/build; run end-to-end tests with a restored MySQL database.
- Configure Razorpay Test Mode credentials and a signed HTTPS webhook; test success, failure, cancellation, wrong amount/signature, duplicate event and retry before considering live payments.
- This project uses legacy unmanaged MySQL tables. Review the compatibility migration output and unowned legacy orders; do not call the project production-ready until all integration tests pass.
