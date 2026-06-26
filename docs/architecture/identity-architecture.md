# Identity Architecture

## Ownership

ResearchMind does not own authentication.

ResearchMind owns application users.

| Identity Provider owns | ResearchMind owns     |
|------------------------|-----------------------|
| Passwords              | Research Sessions     |
| MFA                    | Documents             |
| OAuth / PKCE           | Reports               |
| JWT issuance           | Preferences           |
|                        | Memory                |

---

## Authentication Flow (Cognito Hosted UI + PKCE)

```
Browser
  │
  │  1. User clicks "Sign in"
  ▼
Next.js Frontend
  │
  │  2. Generate code_verifier + code_challenge (PKCE)
  │     Redirect to Cognito Hosted UI with code_challenge
  ▼
AWS Cognito Hosted UI
  │
  │  3. User authenticates (password, MFA, social, etc.)
  │     Cognito issues short-lived authorization code
  │     Redirects to callback URL
  ▼
http://localhost:3000/auth/callback?code=<authorization_code>
  │
  │  4. Frontend reads ?code= from URL
  │     POSTs to backend with code + code_verifier
  │
  │     POST /api/v1/auth/callback
  │     { "code": "...", "redirect_uri": "...", "code_verifier": "..." }
  ▼
FastAPI (ResearchMind API)  ←── POST /api/v1/auth/callback
  │
  │  5. Backend exchanges code with Cognito token endpoint
  │
  │     POST {COGNITO_DOMAIN}/oauth2/token
  │     { grant_type, code, redirect_uri, client_id, code_verifier }
  ▼
AWS Cognito Token Endpoint
  │
  │  6. Returns { id_token, access_token, refresh_token, expires_in }
  ▼
FastAPI → returns TokenResponse to Frontend
  │
  │  7. Frontend stores id_token (memory or httpOnly cookie)
  ▼
Next.js Frontend
  │
  │  8. All subsequent API requests include:
  │     Authorization: Bearer <id_token>
  ▼
FastAPI Protected Endpoint
```

---

## Per-Request Authorization Flow

```
Request
  │
  ▼
Authorization: Bearer <id_token>
  │
  ▼
app/auth/dependencies.py → get_current_user()
  │
  ▼
JWTVerifier.verify()
  │  - Fetch JWKS from Cognito (cached)
  │  - Validate signature, expiry, issuer, audience
  │  - Assert token_use == "id"
  ▼
CognitoAuthenticationProvider.normalize_claims()
  │  - Maps Cognito claims → provider-agnostic identity
  ▼
UserService.sync_user()
  │  - Upsert user in PostgreSQL on first login / claim changes
  ▼
Current User (app/models/user.py)
  │
  ▼
Protected Endpoint
```

---

## Key Configuration

| Variable                | Purpose                                              |
|-------------------------|------------------------------------------------------|
| `COGNITO_USER_POOL_ID`  | Used to construct the JWKS URL and token issuer      |
| `COGNITO_APP_CLIENT_ID` | Audience claim validation + token exchange           |
| `COGNITO_DOMAIN`        | Hosted UI domain for `/oauth2/token` exchange        |
| `COGNITO_CLIENT_SECRET` | Only for confidential app clients (optional)         |
| `AWS_REGION`            | Used in issuer URL construction                      |

---

## Provider Abstraction

The JWT verification layer is provider-agnostic. Adding a new identity
provider (Google, GitHub, etc.) requires only:

1. A new class implementing `app/auth/providers/base.py → AuthenticationProvider`
2. Wiring it into `app/auth/dependencies.py`

No changes to `JWTVerifier`, `UserService`, or any protected endpoints.

---

## Implementation

The following files make up the authentication layer:

| File | Role |
|------|------|
| `app/auth/providers/base.py` | Abstract contract all identity providers must implement |
| `app/auth/providers/cognito.py` | Cognito-specific issuer, audience, JWKS URL, claims normalization |
| `app/auth/jwt.py` | Fetches JWKS, verifies JWT signature/expiry/audience/issuer |
| `app/auth/dependencies.py` | FastAPI dependency — extracts Bearer token and returns `User` |
| `app/services/auth.py` | Exchanges Cognito authorization code for tokens (HTTP call) |
| `app/services/user.py` | `sync_user()` — upserts user on every login |
| `app/schemas/auth.py` | `CallbackRequest` and `TokenResponse` Pydantic models |
| `app/api/v1/auth.py` | `POST /auth/callback` and `GET /auth/me` endpoints |

### Token types

Cognito issues two tokens on every login. Only the `id_token` is accepted here:

| Token | `token_use` claim | Used for |
|-------|-------------------|----------|
| `id_token` | `"id"` | Sent as `Authorization: Bearer` — **this is what the API accepts** |
| `access_token` | `"access"` | Calling AWS services directly — rejected by this API |

The check lives in `app/auth/jwt.py` — any token where `token_use != "id"` is
rejected with `401 Invalid token type`.

---

## Testing Without a Frontend

The full auth flow can be exercised manually using only a browser and curl.
The authorization code is **single-use and expires in ~10 minutes**, so
complete all steps quickly.

### Step 1 — Get an authorization code

Open the Cognito Hosted UI login URL in your browser. Replace the values
from your `.env`:

```
https://<COGNITO_DOMAIN>/login
  ?client_id=<COGNITO_APP_CLIENT_ID>
  &response_type=code
  &scope=openid+email+profile
  &redirect_uri=http://localhost:3000/auth/callback
```

Example (single line):
```
https://us-east-19chs0pt6p.auth.us-east-1.amazoncognito.com/login?client_id=1r4at7v1s9nr9jqots6gl15ht&response_type=code&scope=openid+email+profile&redirect_uri=http://localhost:3000/auth/callback
```

Log in. The browser will try to redirect to `http://localhost:3000/auth/callback?code=XXXX`.
That page will not load (no frontend running), but the `code` value is visible in the URL bar.
Copy it.

### Step 2 — Exchange the code for tokens

```bash
curl -X POST http://localhost:8000/api/v1/auth/callback \
  -H "Content-Type: application/json" \
  -d '{
    "code": "PASTE_CODE_HERE",
    "redirect_uri": "http://localhost:3000/auth/callback"
  }'
```

Response:
```json
{
  "id_token": "eyJ...",
  "access_token": "eyJ...",
  "refresh_token": "...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

### Step 3 — Call a protected endpoint

```bash
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <id_token>"
```

Expected response:
```json
{
  "id": "23be7148-8d69-4249-8b1e-8ebfd84ae0f8",
  "email": "you@example.com",
  "username": "...",
  "full_name": null,
  "avatar_url": null,
  "provider": "cognito",
  "verified": true
}
```

Alternatively, use the Swagger UI at `http://localhost:8000/docs` — click
**Authorize**, paste the `id_token` as the Bearer value, then try any
protected endpoint.

---

## AWS Cognito App Client Setup

The Cognito App Client must be configured correctly or token exchange will fail.

In the AWS Console → Cognito → User Pools → your pool → App clients → your client:

| Setting | Required value |
|---------|---------------|
| OAuth 2.0 grant types | **Authorization code grant** must be checked |
| OpenID Connect scopes | `openid`, `email`, `profile` |
| Allowed callback URLs | `http://localhost:3000/auth/callback` |
| Client secret | Leave blank for public clients (SPAs) |

### Common errors during token exchange

| Error | Cause | Fix |
|-------|-------|-----|
| `unauthorized_client` | "Authorization code grant" not enabled | Enable it in the app client OAuth settings |
| `unauthorized_client` | App client has a secret but none was sent | Set `COGNITO_CLIENT_SECRET` in `.env` |
| `invalid_grant` | Authorization code expired or already used | Get a fresh code from step 1 |
| `invalid_grant` | `redirect_uri` mismatch | Ensure the `redirect_uri` in the POST body exactly matches the one in the Cognito app client |
| `401 Invalid token type` | Sent `access_token` instead of `id_token` | Use the `id_token` from the callback response |

---

## Issues Encountered During Initial Setup

### 1. Logger crash turning 401s into 500s

**File:** `app/exceptions/handlers.py`

Python's `logging` module reserves `"message"` as a built-in `LogRecord` field.
Passing it via `extra={"message": ...}` raises:

```
KeyError: "Attempt to overwrite 'message' in LogRecord"
```

This caused the exception handler itself to crash, so every `UnauthorizedException`
(which should return a clean 401) became an unhandled 500.

**Fix:** Renamed the key to `"error_message"` in the `extra` dict.

### 2. Alembic at head but table missing

`alembic current` reported the migration as applied (`43dc35ceb875 (head)`),
but the `users` table did not exist in the database. The `alembic_version`
tracking table had been stamped without the migration actually running.

**Symptoms:**
```
sqlalchemy.exc.ProgrammingError: relation "users" does not exist
```

**Fix:**
```bash
uv run alembic stamp base   # clear the false "head" stamp
uv run alembic upgrade head # actually run the migration
```

**Verify the table exists:**
```bash
psql postgresql://researchmind:researchmind@localhost:5432/researchmind -c "\dt"
```
