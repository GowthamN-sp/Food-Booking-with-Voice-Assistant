# Savora — Food Ordering with Echo Voice Assistant

A full-stack food-ordering portfolio project using **React + Vite**, **Django**, **MySQL**, **Groq-powered voice-command interpretation**, browser speech recognition/text-to-speech, and a Razorpay integration that must be exercised in Test Mode before live use.

## Pages and behaviour

- `/`: public homepage and searchable/category-filtered menu; guest cart is available.
- `/about`: public project overview.
- `/cart`: guest-accessible cart; sign-in required at checkout.
- `/login`: sign-in and signup; restores the intended destination after login.
- `/orders` and `/profile`: authenticated routes.
- Unknown routes display a branded 404 page.
- Echo can filter the menu, navigate, update the cart, read a cart summary, and retrieve the signed-in user's latest order status. Passwords are not collected by voice.

## Stack

- Frontend: React, Vite, React Router, Lucide icons, browser speech APIs.
- Backend: Django REST-style JSON endpoints, MySQL, signed expiring API tokens.
- AI voice parsing: Groq API through an OpenAI-compatible client, with a safe rule-based fallback.
- Payments: server-created Razorpay Orders, server signature/payment verification and signed webhooks.

## Quick start

See [`PRODUCTION_SETUP.md`](PRODUCTION_SETUP.md) for complete setup, schema migration, menu price review, payment test steps, deployment environment variables, and the verification checklist.

Backend (from `Backend/`):

```bash
python manage.py migrate_savora_schema
python manage.py check
python manage.py runserver 127.0.0.1:8000
```

Frontend (from `FrontEnd/`):

```bash
npm ci
npm run lint
npm run build
npm run dev
```

## Required environment

Copy `Backend/.env.example` to `Backend/.env` and enter your own local database credentials and a newly generated Django secret. Copy `FrontEnd/.env.example` to `FrontEnd/.env` if you need to override `VITE_API_BASE_URL`. Do not commit `.env` files or secrets.

## Safety and release note

The current source uses an explicit compatibility command because the existing MySQL tables are legacy unmanaged tables. Back up MySQL before running it. Menu price suggestions are illustrative Bengaluru-oriented demo values and are preview-only by default; review them against real ingredient/portion costs before applying. Razorpay must remain in Test Mode until the complete payment and webhook test checklist has passed.
