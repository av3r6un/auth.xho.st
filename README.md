# auth

Simple authentication service for user registration, login, token refresh, and token revocation.

## What it does

- Registers users with email and password
- Authenticates users and returns JWT tokens
- Refreshes access tokens with a refresh token
- Revokes refresh tokens
- Returns current user info for authenticated requests
- Exposes a JWKS endpoint for JWT verification

## Stack

- Python 3.14+
- `aiohttp`
- SQLAlchemy async
- Alembic
- JWT (`RS256`)
- `bcrypt`
- Docker

## API

- `POST /` - login
- `POST /register` - register a new user
- `POST /refresh` - refresh tokens
- `POST /revoke` - revoke a refresh token
- `POST /devices/master` - mark one of the user's devices as the master device
- `GET /me` - get current user info
- `GET /.well-known/jwks.json` - public keys for token verification
- `GET /health` - health check

## Auth flow

1. Register a user.
2. Log in with email and password.
3. Receive access and refresh tokens.
4. Use the access token in the `Authorization: Bearer <token>` header.
5. Use the refresh token to get a new token pair when needed.
6. Revoke the refresh token to end its validity.

New JWTs contain a signed `token_use` claim: `access` for access tokens and
`refresh` for refresh tokens. Auth keeps this claim optional for backwards
compatibility: legacy tokens without it remain accepted. If the claim is present,
authenticated endpoints require `access`, and `/refresh` requires `refresh` in
addition to the existing database checks for expiration, revocation and device binding.
Registry requires `token_use: "access"` and rejects legacy tokens without the claim.

## Data model

- `users` - account identity, password hash, roles, scopes, and status flags
- `refresh_tokens` - stored refresh token hashes with expiration, revoke state, and optional device binding
- `devices` - registered devices and their master-device status

## Local run

1. Create and fill a `.env` file with the required settings.
2. Install dependencies.
3. Run database migrations.
4. Start the app.

Example:

```bash
uv sync
alembic upgrade head
python main.py
```

The service runs on port `8090` by default.

## Using this auth server in another project

This service is meant to be used as a central auth provider. A client app or API can delegate login to this service, then trust the issued JWT access tokens.

### 1. Register an account

Create an account with the user's email address and password by sending a `POST` request to `/register`:

```http
POST /register HTTP/1.1
Content-Type: application/json

{
  "data": {
    "email": "user@example.com",
    "password": "secret"
  }
}
```

The request body must contain a `data` object with these fields:

- `email` - required account email. The service stores it in lowercase and enforces uniqueness.
- `password` - required account password. The service stores only a password hash; the plain-text password is not persisted.

On successful registration, the service generates a unique six-character user ID, assigns the default `user` role and `auth` scope, activates the account, and returns:

```json
{
  "status": "success",
  "body": true,
  "message": "Your account successfully created!"
}
```

Registration does not issue JWT tokens. After the account is created, use the same email and password with `POST /` to log in and receive an access token and refresh token.

If the email is already registered, the service returns HTTP `409 Conflict`:

```json
{
  "data": {
    "status": "error",
    "message": "Account already registered!"
  },
  "status": 409
}
```

Malformed or incomplete registration data returns HTTP `400` with an error response. The endpoint must be called over HTTPS in production, and clients should avoid logging the password or sending it anywhere except the auth service.

### 2. Log in against the auth server

Send user credentials to the auth server:

```http
POST / HTTP/1.1
Content-Type: application/json

{
  "data": {
    "email": "user@example.com",
    "password": "secret",
    "device_id": "phone-unique-id",
    "device_name": "My phone",
    "access_token_ttl": 3600
  }
}
```

`device_id` is optional for backwards compatibility. `access_token_ttl` is an optional lifetime in seconds and is bounded by `JWT_ACCESS_TOKEN_MIN_EXPIRES` and `JWT_ACCESS_TOKEN_MAX_EXPIRES` (defaults: 60 seconds and 30 days). The refresh token lifetime remains controlled by the server.

To mark a device as master, first log in with its `device_id`, then call:

```http
POST /devices/master
Authorization: Bearer <access_token>
Content-Type: application/json

{"data": {"device_id": "phone-unique-id", "device_name": "My phone"}}
```

Master devices use `JWT_MASTER_REFRESH_TOKEN_EXPIRES` (default: 365 days) for newly issued refresh tokens. Existing refresh tokens are not extended retroactively.

Successful response returns:

- `access_token`
- `refresh_token`
- `expires_at`
- basic user info

### 3. Store tokens in your project

- Keep the access token in memory or a short-lived secure store
- Keep the refresh token in a secure HTTP-only cookie or another protected storage
- Do not log tokens or expose them in frontend code unless that is an intentional design choice

### 4. Send the access token with protected requests

Use the access token in the `Authorization` header:

```http
Authorization: Bearer <access_token>
```

You can call this auth service directly:

- `GET /me` to fetch current user info

Or your own backend can accept the same token and validate it locally.

### 5. Verify tokens in your backend

Your backend should verify:

- signature
- `iss`
- `exp`
- `iat`
- `sub`

Public keys are available from:

```text
/.well-known/jwks.json
```

Python example with JWKS:

```python
import jwt
from jwt import PyJWKClient

AUTH_SERVER = "https://auth.example.com"
ISSUER = AUTH_SERVER

jwk_client = PyJWKClient(f"{AUTH_SERVER}/.well-known/jwks.json")

def verify_access_token(token: str) -> dict:
  signing_key = jwk_client.get_signing_key_from_jwt(token).key
  payload = jwt.decode(
    token,
    signing_key,
    algorithms=["RS256"],
    issuer=ISSUER,
    options={"require": ["exp", "iat", "iss", "sub"]},
  )
  if "token_use" in payload and payload["token_use"] != "access":
    raise jwt.InvalidTokenError("Access token required")
  return payload
```

### 6. Refresh tokens when access token expires

When the access token expires, send the refresh token to:

```http
POST /refresh
Content-Type: application/json

{
  "data": {
    "refresh_token": "<refresh_token>"
  }
}
```

This returns a new access token and refresh token pair.

### 7. Revoke refresh tokens on logout

On logout, revoke the refresh token:

```http
POST /revoke
Content-Type: application/json

{
  "data": {
    "refresh_token": "<refresh_token>"
  }
}
```

### Typical integration pattern

1. Frontend sends credentials to your backend.
2. Your backend calls this auth server for login.
3. Your backend stores or forwards tokens according to your security model.
4. Your backend validates access tokens on protected routes.
5. Your backend refreshes tokens when needed.

## Notes

- Passwords are stored as hashes.
- Refresh tokens are stored as hashes.
- Secrets, private keys, and environment-specific values should not be committed to the repository.
