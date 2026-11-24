# TeamBright — SoundDNA Studio

Accounts, profiles, music discovery, SoundDNA audio analysis, Canary Spider release monitoring, career insights, event ticketing, and gate check-in for the CIMFEST 2026 Cameroon demo.

## Requirements and setup

- Python 3.11 or newer
- SQLite by default; SQLAlchemy supports changing `DATABASE_URL` to PostgreSQL

### Quick start

Run these commands from the repository root in PowerShell:

```powershell
cd Backend
$python = "C:/Users/BHGJJ/AppData/Local/Programs/Python/Python313/python.exe"
& $python -m pip install -r requirements.txt
$env:NUMBA_DISABLE_JIT = "1"
& $python seed_demo.py
& $python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The studio UI and API are available at `http://127.0.0.1:8000`; interactive OpenAPI docs are at `http://127.0.0.1:8000/docs`. The UI is served by the backend; the separate `Frontend/` directory is a Vite starter.

`NUMBA_DISABLE_JIT=1` avoids a Librosa/Numba crash that can occur while running audio analysis on Python 3.13 under Windows.

To create a general demo account set instead of the SoundDNA/Canary demo data:

```powershell
cd Backend
& $python -m scripts.seed
& $python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Stop the server with `Ctrl+C`.

## API-only run

The broadcast functionality is a backend API and does not require the Vite frontend. From the repository root:

```powershell
cd Backend
$python = "C:/Users/BHGJJ/AppData/Local/Programs/Python/Python313/python.exe"
& $python seed_demo.py
& $python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs` for Swagger UI or `http://127.0.0.1:8000/redoc` for Redoc. Interactive API calls use the `/auth/login` `access_token` as `Authorization: Bearer <token>`.

## Broadcast API lifecycle

1. Register or sign in as an artist/collaborator.
2. Register an audio track with `POST /api/tracks`.
3. Publicly discover eligible stations/DJs with `GET /api/broadcast/destinations`. Use `type`, `city`, `verified_only`, or `q` to filter results.
4. Send a track with `POST /api/broadcast/execute`, providing `track_id` and either `destination_id` or `destination_ids`.
5. Track owner reviews dispatches with `GET /api/broadcast/sent`.
6. Each receiver reviews dispatches with `GET /api/broadcast/inbox`.
7. The receiver updates a dispatch with `PATCH /api/broadcast/{dispatch_id}/status`.

Allowed status transitions are `sent -> delivered -> played`, or `sent/delivered -> declined`. A track owner cannot update a dispatch; only the receiving broadcaster or DJ can change its status.

### Tests

Run the complete backend suite from `Backend/`:

```powershell
$env:NUMBA_DISABLE_JIT = "1"
& $python -m pytest -q
```

Run only the Canary Spider or event/ticketing tests:

```powershell
$env:NUMBA_DISABLE_JIT="1"
& $python -m pytest tests/test_canary.py -q
& $python -m pytest tests/test_events.py tests/test_ticketing.py -q
```

To load the SoundDNA and Canary-specific demo account, benchmark, example demo versions, release, and weekly snapshots, run `python seed_demo.py` from `Backend/` instead of `python -m scripts.seed`. The demo login is `+237699556677` with PIN `5555`; generated WAV fixtures are in `Backend/demo_audio/`. Both seeders are safe to rerun for their own records. The general account seeder uses `DEMO_PIN` (default `1234`).

### Environment variables

Set these in the environment or in `Backend/.env`:

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./sounddna.db` | SQLAlchemy connection string |
| `JWT_SECRET` | development-only value | Signing secret; set a strong private value outside local development |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_MINUTES` | `60` | Bearer token lifetime |
| `ENV` | `development` | Environment label |
| `DEMO_PIN` | `1234` | PIN used only when creating demo seed accounts |

Use `python -m scripts.create_admin --name "Admin" --phone "690123456" --city "Yaoundé"` to create an administrator; the PIN is prompted without echo. The `seed` command also creates one local demo admin. Seeded organizations and accounts are explicitly marked `DEMO` and are never verified automatically.

## Authentication and errors

Cameroon mobile numbers are stored as `+237` plus the 9-digit number beginning with `6`. Registration and login accept the local number (for example, `690123456`) or an international `237`, `+237`, or `00237` prefix, with optional spaces or hyphens. PINs are salted PBKDF2 hashes. Login tokens are signed JWTs. After five failed PIN attempts, login is blocked for 15 minutes. PIN login is demo-grade; there is no SMS OTP or recovery flow.

All API errors use `{"error":{"code":"...","message":"...","details":{...}}}`. Validation errors include field locations. Request bodies larger than 1 MiB are rejected, except audio uploads (30 MiB maximum, plus multipart overhead).

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
| `POST` | `/songs` | Artist | Upload and publish an MP3 song (30 MiB maximum) |
| `GET` | `/songs/recent` | Public | List the latest active songs for fan and platform discovery |
| `GET` | `/songs/{song_id}/audio` | Public | Stream a published song |
| `GET` | `/songs/mine` | Authenticated | List the signed-in artist's published songs |
| `POST` | `/analyzer/viral-benchmarks` | Artist | Analyze and save an audience-proven viral benchmark |
| `POST` | `/analyzer/compare` | Artist | Compare a studio demo with an owned benchmark and save a version |
| `GET` | `/analyzer/my-studio` | Artist | List the signed-in artist's benchmarks and demo versions |
| `POST` | `/releases` | Artist | Publish a track release against an owned benchmark |
| `POST` | `/releases/{release_id}/airplay` | Verified broadcaster/DJ | Log official radio or TV airplay |
| `POST` | `/canary/crawl/{release_id}` | Artist | Submit a weekly Canary momentum snapshot |
| `GET` | `/advisor/dashboard` | Artist | Read trajectory, momentum status, and advisor insights |
| `POST` | `/advisor/insights/{insight_id}/acknowledge` | Artist | Acknowledge an owned advisor insight |
| `POST` | `/events` | Authenticated | Create a ticketed event |
| `GET` | `/events` | Authenticated | List the signed-in user's events |
| `POST` | `/events/{event_id}/collaborators` | Event owner | Assign a ticket seller and commission |
| `GET` | `/events/{event_id}/collaborators` | Event owner | List collaborators and ticket balances |
| `POST` | `/events/{event_id}/collaborators/{collaborator_id}/sales` | Event owner | Record tickets sold against an assignment |
| `POST` | `/api/events` | Artist/promoter | Create an approved-ticket workflow event |
| `POST` | `/api/events/{event_id}/decision` | Admin | Approve or reject an event |
| `POST` | `/api/events/{event_id}/ticket-tiers` | Event owner | Add a priced ticket tier |
| `POST` | `/api/events/{event_id}/tickets/mint` | Event owner | Mint signed QR tickets for a tier |
| `POST` | `/api/events/{event_id}/tickets/purchase` | Public | Purchase an available ticket and create payout records |
| `GET` | `/api/events/{event_id}/dashboard` | Event owner | Read capacity, sales, revenue, tiers, and collaborators |
| `GET` | `/api/events/{event_id}/availability` | Event owner | Read ticket availability metrics |
| `GET` | `/api/tickets/qr/{qr_token}` | Public | Render a sold or checked-in ticket QR image |
| `POST` | `/api/gate/scan` | Gate staff/authorized organizer | Validate or check in a ticket |
| `POST` | `/api/admin/users/{user_id}/gate-staff` | Admin | Promote a user to gate staff |
| `POST` | `/api/tracks` | Artist/collaborator | Register an audio track for broadcast |
| `GET` | `/api/tracks/mine` | Authenticated artist/collaborator | List owned tracks |
| `GET` | `/api/broadcast/destinations` | Public | Filter broadcasters and DJs for pitch dispatch |
| `GET` | `/api/broadcast/tracks` | Authenticated owner | List available owned tracks |
| `POST` | `/api/broadcast/execute` | Track owner | Send a track to one or more broadcasters/DJs |
| `GET` | `/api/broadcast/sent` | Track owner | List dispatched broadcasts |
| `GET` | `/api/broadcast/inbox` | Broadcaster/DJ | List received broadcasts |
| `PATCH` | `/api/broadcast/{dispatch_id}/status` | Receiver | Set a dispatch to delivered, played, or declined |

`/directory` accepts `role`, `city`, `genre`, `verified`, `q`, `limit` (1–50), and `offset`. Directory results include only active users with public artist, DJ, broadcaster, or promoter profiles.

Song uploads are stored as MP3 files in `Backend/uploads/songs`; the public song listing exposes audio URLs for in-browser playback.

## Event ticket collaborators

Create an event with `POST /events` using `title`, ISO-formatted `event_date`, `venue`, `ticket_price`, and `total_tickets`. Add collaborators through `POST /events/{event_id}/collaborators` with a `name`, exactly one contact field (`email` or `phone`), `commission_percent`, and `tickets_assigned`. Commission is calculated per ticket from the event's ticket price. Total assignments cannot exceed the event capacity.

The event owner records sales with `POST /events/{event_id}/collaborators/{collaborator_id}/sales` and `{"quantity": 3}`. The API tracks tickets sold and remaining, and rejects sales above the collaborator's allocation. Events and collaborator records are private to the user who created the event. Collaborators are stored as contact records; this feature does not create user accounts or send invitations.

## Event ticket lifecycle

For the full ticket workflow, an artist or promoter creates `POST /api/events`, an admin approves it with `POST /api/events/{event_id}/decision`, and the owner adds priced tiers with `POST /api/events/{event_id}/ticket-tiers`. Mint tickets with `POST /api/events/{event_id}/tickets/mint`, then accept purchases through `POST /api/events/{event_id}/tickets/purchase`. Each sale is assigned a signed QR token and split between the organizer, collaborator, and platform according to the configured fees.

Assign a collaborator account with `POST /api/events/{event_id}/collaborators` using a user ID, commission, quota, optional over-quota setting, and promo code. The collaborator accepts the offer through `POST /api/collaborators/{collaborator_id}/accept`. At the gate, send exactly one `ticket_code` or signed `qr_token` to `POST /api/gate/scan`. The endpoint permits an organizer or administrator, or a user promoted to `gate_staff` with `POST /api/admin/users/{user_id}/gate-staff`.

## SoundDNA Analyzer and Canary Spider

The Analyzer accepts WAV or MP3 files up to 30 MiB and 10 minutes long. It extracts musical features and compares a new demo with a benchmark owned by the signed-in artist. Analysis results and version numbers are saved; uploaded Analyzer audio is not retained. The comparison returns a readiness score, verdict, per-dimension scores, and suggested studio fixes. The scoring and Canary recommendations are deterministic signal/rule-based analysis, not a hosted generative-AI service.

The Analyzer workflow is:

1. Sign in as an artist and create a benchmark with `POST /analyzer/viral-benchmarks` (multipart fields: `title`, `genre`, optional `broadcast_stations_count` and `viral_reach_notes`, and `audio_file`).
2. Compare a studio demo with `POST /analyzer/compare` (multipart fields: owned `benchmark_id`, `demo_title`, and `audio_file`). Reusing a demo title creates the next version.
3. Read saved benchmarks and demo versions from `GET /analyzer/my-studio`.

The Canary workflow is:

1. Publish a track using `POST /releases` with a title and an owned `benchmark_id`.
2. Submit each week's manually collected stream, airplay, skip-rate, social-mention, and top-city data to `POST /canary/crawl/{release_id}`. A release can have only one snapshot per week.
3. Review momentum, trajectory, and generated insights in `GET /advisor/dashboard`; acknowledge an insight with `POST /advisor/insights/{insight_id}/acknowledge`.
4. Verified broadcasters and DJs can record official spins using `POST /releases/{release_id}/airplay`. An airplay log triggers advisor evaluation in a background task.

Advisor rules currently flag a stream decline of at least 25% week over week, an early skip rate above 35%, and a regional surge at 10 city spins or 100 social mentions. When none apply, the system creates a follow-up-window recommendation. Insights are created once per category for each weekly snapshot. Snapshot submission and weekly stream/social figures are manual inputs; this demo does not connect to streaming or social platform APIs.

### Try the seeded Analyzer and Advisor

After running `python seed_demo.py` and starting the backend, open `http://127.0.0.1:8000` and sign in as the demo artist. The Analyzer tab shows the seeded benchmark and two comparison versions. For an additional comparison, use `Backend/demo_audio/follow_up_demo_v1_weak.wav` or `Backend/demo_audio/follow_up_demo_v2_fixed.wav`. In the Advisor tab, publish a release or inspect the seeded Canary trajectory and insights.

The same flow can be exercised through the API. These PowerShell examples assume the seeded demo database and use the seeded artist's benchmark:

```powershell
$base = "http://127.0.0.1:8000"
$artist = (Invoke-RestMethod "$base/auth/login" -Method Post -ContentType "application/json" -Body '{"phone":"+237699556677","pin":"5555"}').access_token
$headers = @{ Authorization = "Bearer $artist" }
$studio = Invoke-RestMethod "$base/analyzer/my-studio" -Headers $headers
$benchmarkId = $studio.benchmarks[0].id

$release = Invoke-RestMethod "$base/releases" -Method Post -Headers $headers -ContentType "application/json" -Body (@{
    title = "Canary API demo"
    benchmark_id = $benchmarkId
} | ConvertTo-Json)
$releaseId = $release.id

Invoke-RestMethod "$base/canary/crawl/$releaseId" -Method Post -Headers $headers -ContentType "application/json" -Body (@{
    week_number = 1
    weekly_streams = 120000
    radio_tv_spins = 18
    early_skip_rate_pct = 19
    social_mentions = 70
    top_city = "Douala"
} | ConvertTo-Json)

Invoke-RestMethod "$base/advisor/dashboard" -Headers $headers
```

For multipart Analyzer uploads, use the browser UI or `curl.exe -F`; see `/docs` for the request schema and error responses.

## Broadcast API example

```powershell
# Sign in and receive a bearer token.
$artist = (curl.exe -s -X POST http://127.0.0.1:8000/auth/login -H "Content-Type: application/json" -d '{"phone":"690111111","pin":"1234"}' | ConvertFrom-Json).access_token

# Register a track.
$track = curl.exe -s -X POST http://127.0.0.1:8000/api/tracks -H "Authorization: Bearer $artist" -H "Content-Type: application/json" -d '{"title":"Buea Nights","genre":"Makossa","duration_seconds":185,"audio_url":"https://audio.example/buea-nights.mp3"}' | ConvertFrom-Json

# Discover and dispatch to destinations.
curl.exe -s "http://127.0.0.1:8000/api/broadcast/destinations?q=Radio"
curl.exe -s -X POST http://127.0.0.1:8000/api/broadcast/execute -H "Authorization: Bearer $artist" -H "Content-Type: application/json" -d '{"track_id":1,"destination_id":2,"note":"Please introduce the new single."}'

# Review sent dispatches.
curl.exe -s http://127.0.0.1:8000/api/broadcast/sent -H "Authorization: Bearer $artist"
```

A receiver updates dispatch status with:

```powershell
curl.exe -s -X PATCH http://127.0.0.1:8000/api/broadcast/1/status -H "Authorization: Bearer $station" -H "Content-Type: application/json" -d '{"status":"delivered"}'
```

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
