# Twilio WhatsApp integration

This guide explains how to connect Twilio WhatsApp to the Mwavuli backend so users can send messages to your WhatsApp number and receive content verification results (risk level, prebunking tip, and Swahili for HIGH/MEDIUM risk).

## Prerequisites

- A [Twilio](https://www.twilio.com) account
- Backend running and reachable via HTTPS (Twilio requires a public URL for the webhook)

## 1. Get Twilio credentials

1. Go to [Twilio Console](https://console.twilio.com).
2. On the **Dashboard** (home), find **Account Info**:
   - **Account SID** (starts with `AC`) → set as `TWILIO_ACCOUNT_SID`
   - **Auth Token** (click to reveal) → set as `TWILIO_AUTH_TOKEN`
3. For WhatsApp:
   - **Sandbox (testing):** Go to **Messaging** → **Try it out** → **Send a WhatsApp message**. Follow the steps to join the sandbox. The sandbox number (e.g. `+1 415 523 8886`) is your sender → set as `TWILIO_WHATSAPP_FROM=whatsapp:+14155238886`.
   - **Production:** Use your own Twilio WhatsApp-enabled number and set `TWILIO_WHATSAPP_FROM=whatsapp:+<your_number>`.

## 2. Configure the backend

In `backend/.env` (copy from `backend/.env.example` if needed):

```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
```

- `TWILIO_WHATSAPP_FROM` must start with `whatsapp:` and use E.164 format (e.g. `+14155238886`).
- Restart the backend after changing `.env`.

## 3. Set the webhook URL in Twilio

1. In Twilio Console: **Messaging** → **Try it out** → **Send a WhatsApp message** (or your WhatsApp Sender).
2. Under **When a message comes in**:
   - Set the URL to: `https://<your-backend-host>/api/v1/webhooks/twilio`
   - Method: **POST**
   - Example: if your backend is at `https://mwavuli-api.example.com`, use `https://mwavuli-api.example.com/api/v1/webhooks/twilio`.
3. Click **Save**.

Twilio will send a GET request to validate the URL; the backend responds with `200 OK` and "Mwavuli webhook OK". Incoming WhatsApp messages trigger a POST with the message body and sender; the backend analyzes the text, saves a report, and replies with the verification result.

## 4. Flow summary

- User sends a WhatsApp message to your Twilio number.
- Twilio POSTs to `/api/v1/webhooks/twilio` with `Body`, `From`, `To`, etc.
- Backend runs the same analyzer as `POST /api/v1/verify/text` (lexicon, Detoxify, Gemini).
- Report is saved to Firestore (same collection as API verification).
- User receives a WhatsApp reply: English message + prebunking tip; for HIGH/MEDIUM risk, Swahili is appended.

## 5. Behind a reverse proxy

If the backend is behind a proxy (e.g. nginx, load balancer), Twilio’s request signature validation uses the URL Twilio called. If validation fails (e.g. 403), the request might be reaching your app with an internal URL. In that case you can add an optional env var (future enhancement) such as `TWILIO_WEBHOOK_BASE_URL=https://your-public-host/api/v1/webhooks/twilio` and use it when validating the signature. Currently the backend uses `request.url`; ensure your proxy forwards the correct `Host` and scheme so the URL is correct, or signature validation can be skipped by not setting `TWILIO_AUTH_TOKEN` (not recommended for production).

## 6. Troubleshooting

- **No WhatsApp reply:** Ensure all three Twilio env vars are set and not placeholders (`your_*`). Check backend logs for "Twilio send error".
- **403 Invalid Twilio signature:** Use the exact same URL in Twilio that Twilio calls (including `https` and path). If behind a proxy, see section 5.
- **Webhook URL must be HTTPS:** Twilio requires a public HTTPS URL. For local testing you can use a tunnel (e.g. ngrok) and put that URL in Twilio.

## See also

- [Backend README](../README.md) – env vars table
- [API docs](http://localhost:8000/docs) when the backend is running – `GET/POST /api/v1/webhooks/twilio` under WhatsApp
