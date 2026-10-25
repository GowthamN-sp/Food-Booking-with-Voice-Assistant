# Savora security setup and status

This file documents the security controls implemented in the patched source; it is not a guarantee that a deployment has been audited or is production-ready.

## Implemented in source

- New signup passwords use Django's password hashing and configured password validation.
- The compatibility schema command converts legacy plaintext password values to Django hashes in place. It recognizes existing Django hashes and is safe to rerun; users continue using their original passwords. Remove legacy plaintext fallback logic after confirming the migration completed across all rows.
- API authentication uses signed, expiring Django tokens. `users.token_version` allows logout to invalidate previously issued tokens.
- User order history and cart routes check the signed token and ownership.
- Checkout prices are recalculated using database catalogue prices; client-supplied amount/price is ignored.
- Order status changes are restricted to emails in `SAVORA_ADMIN_EMAILS` and validated transitions.
- Razorpay verification checks signature, gateway order association, amount, currency and captured status; webhooks validate `X-Razorpay-Signature` and reconcile captured/failed events idempotently.
- Environment secrets are read from backend environment settings; `.env` files must remain untracked.

## Required before deployment

1. Back up the database and run `python manage.py migrate_savora_schema` against the intended database.
2. Set a unique `DJANGO_SECRET_KEY`, `DEBUG=False`, exact `ALLOWED_HOSTS`, exact `CORS_ALLOWED_ORIGINS`, HTTPS security settings, and strong secrets in the host environment.
3. Set up and test Razorpay in Test Mode, including webhooks and payment capture status.
4. Run `python manage.py check`, `python manage.py test app`, `npm run lint`, `npm run build`, and the end-to-end checklist in `PRODUCTION_SETUP.md`.
5. Use a reverse proxy/host rate limiting for login/signup and configure appropriate monitoring/backups. Do not enable real payments until integration tests pass.
6. Review legacy orders with unknown owners. The schema command does not assign them to a guessed user.

The project still uses legacy unmanaged MySQL tables. It should be reviewed and operated carefully until a migration to fully Django-managed models, documented constraints and production integration tests is completed.
