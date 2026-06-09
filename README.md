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

## Data model

- `users` - account identity, password hash, roles, scopes, and status flags
- `refresh_tokens` - stored refresh token hashes with expiration and revoke state

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

### 1. Log in against the auth server

Send user credentials to the auth server:

```http
POST / HTTP/1.1
Content-Type: application/json

{
  "data": {
    "email": "user@example.com",
    "password": "secret"
  }
}
```

Successful response returns:

- `access_token`
- `refresh_token`
- `expires_at`
- basic user info

### 2. Store tokens in your project

- Keep the access token in memory or a short-lived secure store
- Keep the refresh token in a secure HTTP-only cookie or another protected storage
- Do not log tokens or expose them in frontend code unless that is an intentional design choice

### 3. Send the access token with protected requests

Use the access token in the `Authorization` header:

```http
Authorization: Bearer <access_token>
```

You can call this auth service directly:

- `GET /me` to fetch current user info

Or your own backend can accept the same token and validate it locally.

### 4. Verify tokens in your backend

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
    return jwt.decode(
        token,
        signing_key,
        algorithms=["RS256"],
        issuer=ISSUER,
        options={"require": ["exp", "iat", "iss", "sub"]},
    )
```

### 5. Refresh tokens when access token expires

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

### 6. Revoke refresh tokens on logout

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
