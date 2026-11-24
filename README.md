# Bantu Music 2.0 — Events and Ticketing API

FastAPI backend for artist-created events and free ticket giveaways. Swagger UI is the primary interface for trying the API. Account registration and login remain available because event creation and ticket claims require authentication; unrelated profile, directory, verification, follow, and admin routes are not mounted.

## Requirements and setup

- Python 3.11 or newer
- SQLite by default; SQLAlchemy supports changing `DATABASE_URL` to PostgreSQL

```powershell
cd Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m scripts.seed
python -m uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`. Interactive Swagger UI is at
`http://127.0.0.1:8000/docs`; ReDoc is at `http://127.0.0.1:8000/redoc`, and the OpenAPI
JSON is at `http://127.0.0.1:8000/openapi.json`.

### Environment variables

Set these in the environment or in `Backend/.env`:

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./bantu.db` | SQLAlchemy connection string |
| `JWT_SECRET` | development-only value | Signing secret; set a strong private value outside local development |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_MINUTES` | `60` | Bearer token lifetime |
| `ENV` | `development` | Environment label |
| `DEMO_PIN` | `1234` | PIN used only when creating demo seed accounts |
| `FAPSHI_PUBLIC_USER` | unset | Fapshi API user sent as the `apiuser` header |
| `FAPSHI_API_KEY` | unset | Fapshi API key sent as the `apikey` header |
| `FAPSHI_BASE_URL` | `https://sandbox.fapshi.com` | Fapshi sandbox or live API base URL |
| `FAPSHI_WEBHOOK_SECRET` | unset | Static secret configured in the Fapshi service dashboard |
| `FAPSHI_REDIRECT_URL` | `http://127.0.0.1:8000/payments/fapshi/callback` | Browser return URL; use a public HTTPS URL when deployed |

The existing Fapshi API user and key belong in `Backend/.env`. Add the webhook secret after setting the same value in your Fapshi service dashboard:

```dotenv
FAPSHI_PUBLIC_USER=your_sandbox_api_user
FAPSHI_API_KEY=your_sandbox_api_key
FAPSHI_BASE_URL=https://sandbox.fapshi.com
FAPSHI_WEBHOOK_SECRET=your_dashboard_webhook_secret
```

Use the sandbox URL and sandbox credentials for testing; live credentials require `https://live.fapshi.com`. Keep credentials backend-only and never commit `.env` (`Backend/.env` is ignored by Git). Set the Fapshi service webhook URL to `https://<public-host>/payments/fapshi/webhook`; local `127.0.0.1` is not reachable by Fapshi. Fapshi sends the static dashboard secret in `x-wh-secret` (it is not an HMAC signature). Hosted payment links expire after 24 hours, and payment-status requests are limited to six per minute per transaction. See the [Fapshi environment guide](https://docs.fapshi.com/en/api-reference/preliminary-knowledge/environment.md), [initiate-pay reference](https://docs.fapshi.com/en/api-reference/endpoint/initiate-pay.md), [payment-status reference](https://docs.fapshi.com/en/api-reference/endpoint/payment-status.md), and [webhook guide](https://docs.fapshi.com/en/api-reference/endpoint/webhook.md).

Tickets with `price_xaf: 0` remain free giveaways. Paid tickets must cost at least 100 XAF. They reserve one unit during checkout, and the reservation is released if Fapshi confirms failure or expiry. A successful payment is verified with Fapshi before one ticket claim is recorded. Each account may claim or buy at most one ticket per listing.
If a late provider update reports success after a prior payment was released and another payment already fulfilled that user's ticket, the duplicate payment is marked `paid_unfulfilled` and no second ticket is issued; review it for refund handling.

## Authentication and errors

Cameroon mobile numbers are stored as `+237` plus the 9-digit number beginning with `6`. PINs are salted PBKDF2 hashes. Login tokens are signed JWTs. After five failed PIN attempts, login is blocked for 15 minutes. PIN login is demo-grade; there is no SMS OTP or recovery flow. Artist accounts can create events and tickets; any authenticated account can claim one free ticket or purchase one paid ticket per listing. An artist can assign existing `collaborator` accounts to an event. Collaborators can view their assigned events but cannot manage events or tickets.

All API errors use `{"error":{"code":"...","message":"...","details":{...}}}`. Validation errors include field locations. Request bodies larger than 1 MiB are rejected.

## Endpoints

| Method | Path | Access | Purpose |
|---|---|---|---|
| `POST` | `/auth/register` | Public | Create a non-admin account |
| `POST` | `/auth/login` | Public | Sign in and receive a bearer token |
| `POST` | `/events` | Artist | Create an event |
| `GET` | `/events` | Public | List events; filter by event name or artist |
| `GET` | `/events/{event_id}` | Public | Get event details |
| `GET` | `/events/my-collaborations` | Collaborator | List events assigned to you |
| `POST` | `/events/{event_id}/collaborators` | Event owner | Assign a collaborator by user ID |
| `GET` | `/events/{event_id}/collaborators` | Owner/assigned collaborator | List collaborators on an event |
| `DELETE` | `/events/{event_id}/collaborators/{collaborator_id}` | Event owner | Remove a collaborator |
| `POST` | `/tickets` | Artist | Create a free giveaway or a paid ticket listing |
| `GET` | `/tickets` | Public | List tickets; filter by event, event name, status, or artist |
| `GET` | `/tickets/my` | Artist | List your tickets and remaining quantities |
| `GET` | `/tickets/{ticket_id}` | Public | Read a ticket listing |
| `POST` | `/tickets/{ticket_id}/claim` | Authenticated | Claim one available free ticket |
| `POST` | `/payments/tickets/{ticket_id}/checkout` | Authenticated | Start Fapshi checkout for a paid ticket |
| `GET` | `/payments/{payment_id}` | Payment owner | Verify and read your payment status |
| `POST` | `/payments/{payment_id}/cancel` | Payment owner | Cancel a pending payment and release its reservation |
| `GET` | `/payments/fapshi/callback` | Public | Reconcile the browser return from Fapshi |
| `POST` | `/payments/fapshi/webhook` | Fapshi | Verify payment status notifications |

### Try the API in Swagger

1. Start the backend using the setup command above and open `http://127.0.0.1:8000/docs`.
2. Expand `POST /auth/register`, choose **Try it out**, enter a phone, 4–6 digit PIN, role `artist`, name, and city, then execute it.
3. Use `POST /auth/login` with that phone and PIN. Copy the `access_token` from the response.
4. Click **Authorize**, paste the access token, and confirm. Swagger will send it as a bearer token to protected endpoints.
5. Create an event with `POST /events`:

   ```json
   {
     "event_name": "Douala Live",
     "description": "Live music and giveaways",
     "event_date": "2026-12-20T18:00:00Z",
     "venue": "Douala",
     "city": "Douala"
   }
   ```

6. Register another account with role `collaborator`. Use its returned `id` in `POST /events/{event_id}/collaborators`:

   ```json
   {
     "user_id": 2
   }
   ```

   The collaborator can use `GET /events/my-collaborations` to view assigned events. Only the owning artist can add/remove collaborators or create tickets for the event.

7. Create a free giveaway or paid listing with the event ID returned above and a ticket quantity. Use `price_xaf: 0` for a giveaway or an amount of at least 100 XAF for paid tickets:

   ```json
   {
     "event_id": 1,
     "event_name": "Douala Live",
     "total_quantity": 20,
     "price_xaf": 2500,
     "description": "Tickets for Douala Live"
   }
   ```

8. Use `GET /tickets` or `GET /tickets/my` to inspect availability. For a free listing, call `POST /tickets/{ticket_id}/claim`. For a paid listing, call `POST /payments/tickets/{ticket_id}/checkout`, open the returned `checkout_url`, then check `GET /payments/{payment_id}`. Fapshi sandbox test numbers include `670000000` for successful MTN Cameroon payments and `690000000` for successful Orange Cameroon payments. The ticket is issued only after server-side payment verification.
