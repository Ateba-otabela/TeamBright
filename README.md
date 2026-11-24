# Bantu Music 2.0 — Module 1

Accounts, profiles, manual verification, directory discovery, and artist follows for the CIMFEST Hackathon 2026 Cameroon demo. Module 1 is implemented in `Backend/`; later modules are intentionally out of scope.

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

The API is available at `http://127.0.0.1:8000`; OpenAPI docs are at `/docs`.

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

Use `python -m scripts.create_admin --name "Admin" --phone "690123456" --city "Yaoundé"` to create an administrator; the PIN is prompted without echo. The `seed` command also creates one local demo admin. Seeded organizations and accounts are explicitly marked `DEMO` and are never verified automatically.

## Authentication and errors

Cameroon mobile numbers are stored as `+237` plus the 9-digit number beginning with `6`. PINs are salted PBKDF2 hashes. Login tokens are signed JWTs. After five failed PIN attempts, login is blocked for 15 minutes. PIN login is demo-grade; there is no SMS OTP or recovery flow.

All API errors use `{"error":{"code":"...","message":"...","details":{...}}}`. Validation errors include field locations. Request bodies larger than 1 MiB are rejected.

## Endpoints

| Method | Path | Access | Purpose |
|---|---|---|---|
| `POST` | `/auth/register` | Public | Create a non-admin account |
| `POST` | `/auth/login` | Public | Sign in and receive a bearer token |
| `GET` | `/me` | Authenticated | Read own account |
| `PATCH` | `/me` | Authenticated | Update own name and city |
| `POST` | `/me/change-pin` | Authenticated | Change PIN |
| `PUT` | `/profile` | Eligible roles | Create/update own public profile |
| `GET` | `/profiles/{user_id}` | Public | Read a profile (phone private except to owner/admin) |
| `POST` | `/verification-requests` | Artist/DJ/broadcaster/promoter | Submit verification evidence |
| `GET` | `/verification-requests/mine` | Authenticated | List own requests |
| `GET` | `/admin/verification-requests` | Admin | Paginated verification queue |
| `POST` | `/admin/verification-requests/{id}/decision` | Admin | Approve or reject; writes audit row |
| `GET` | `/admin/audit` | Admin | Paginated admin audit log |
| `GET` | `/directory` | Public | Filter profiles by role, city, genre, verified, and display-name query |
| `POST` | `/follows/{artist_id}` | Authenticated | Follow an artist (idempotent) |
| `DELETE` | `/follows/{artist_id}` | Authenticated | Unfollow an artist |
| `GET` | `/me/following` | Authenticated | List followed artists |
| `GET` | `/artists/{id}/followers` | Public | Read follower count only |

`/directory` accepts `role`, `city`, `genre`, `verified`, `q`, `limit` (1–50), and `offset`. Directory results include only active users with public artist, DJ, broadcaster, or promoter profiles.

## Scenario with curl

Run the API first. The examples below assume the seeded demo admin has phone `+237690000001` and PIN `1234`.

```powershell
# Register an artist, station, and fan. Save their returned IDs.
curl.exe -X POST http://127.0.0.1:8000/auth/register -H "Content-Type: application/json" -d '{"name":"Buea Artist","phone":"690111111","pin":"1234","role":"artist","city":"Buea"}'
curl.exe -X POST http://127.0.0.1:8000/auth/register -H "Content-Type: application/json" -d '{"name":"Yaoundé Demo Radio","phone":"690222222","pin":"1234","role":"broadcaster","city":"Yaoundé"}'
curl.exe -X POST http://127.0.0.1:8000/auth/register -H "Content-Type: application/json" -d '{"name":"Demo Fan","phone":"690333333","pin":"1234","role":"fan","city":"Douala"}'

# Sign in as the station and add its required broadcaster details.
$station = (curl.exe -s -X POST http://127.0.0.1:8000/auth/login -H "Content-Type: application/json" -d '{"phone":"690222222","pin":"1234"}' | ConvertFrom-Json).access_token
curl.exe -X PUT http://127.0.0.1:8000/profile -H "Authorization: Bearer $station" -H "Content-Type: application/json" -d '{"display_name":"Yaoundé Demo Radio","station_name":"Yaoundé Demo Radio","medium":"radio","genres":["radio"]}'
curl.exe -X POST http://127.0.0.1:8000/verification-requests -H "Authorization: Bearer $station" -H "Content-Type: application/json" -d '{"evidence_text":"Demo station evidence"}'

# Sign in as admin, approve the pending request, then search for the verified station.
$admin = (curl.exe -s -X POST http://127.0.0.1:8000/auth/login -H "Content-Type: application/json" -d '{"phone":"+237690000001","pin":"1234"}' | ConvertFrom-Json).access_token
curl.exe -X POST http://127.0.0.1:8000/admin/verification-requests/1/decision -H "Authorization: Bearer $admin" -H "Content-Type: application/json" -d '{"decision":"approve","note":"Demo flow"}'
curl.exe "http://127.0.0.1:8000/directory?role=broadcaster&city=Yaound%C3%A9&verified=true&q=Radio"
```

For production, replace the local demo accounts, use a private `JWT_SECRET`, run behind HTTPS, and add an SMS OTP/account recovery provider. Verification decisions are manual in this module.
