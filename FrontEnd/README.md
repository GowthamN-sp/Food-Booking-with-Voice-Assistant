# Savora frontend

React + Vite UI for Savora, a food-ordering application with Echo voice-assisted browsing/cart commands.

## Local setup

```powershell
Copy-Item .env.example .env
npm ci
npm run lint
npm run build
npm run dev
```

The default `VITE_API_BASE_URL` is `http://localhost:8000`. It is public configuration; never put database passwords, Groq keys, or Razorpay Key Secrets in Vite environment variables. Use `VITE_API_BASE_URL` for the deployed backend origin at build time.

## Routes

- `/` public homepage and menu
- `/about` project information
- `/cart` cart; authentication is required only to check out
- `/login` sign-in and account creation
- `/orders` and `/profile` require sign-in
- unknown paths show a branded 404 page

## Voice assistant

Echo uses browser speech recognition/text-to-speech where supported, a text command fallback, and validated Django command interpretation. Groq is optional; a rule-based fallback is used when the Groq key is not configured. Echo never requests a spoken password. Browser speech recognition availability varies by browser/OS and requires user permission.

## Release checklist

Verify guest and account carts, login/logout, menu loading/error states, responsive layout, order details, currency values and the Razorpay Test Mode flow against the backend. A successful Vite build does not prove payment or API correctness.
