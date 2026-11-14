# StreamVibe OTT Backend

FastAPI backend for the `ott-frontend` StreamVibe application. It provides account authentication, the authenticated profile endpoint, plan discovery, and a simulated subscription checkout.

## Setup

1. Create and activate a Python virtual environment.
2. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. If `.env` does not already exist, copy `.env.example` to `.env`. Preserve an existing configured file.
4. Set `DATABASE_URL` to your PostgreSQL SQLAlchemy async URL. For example:

   ```text
   postgresql+asyncpg://username:password@host:5432/database_name
   ```

5. Replace `JWT_SECRET_KEY` with a strong random secret.
6. Start the API:

   ```powershell
   uvicorn app.main:app --reload --port 8000
   ```

At startup, SQLAlchemy creates the `users` and `subscriptions` tables if they do not already exist.
The database must be available before startup; user records contain password hashes, not plaintext passwords. Set `CORS_ORIGINS` to the exact browser origin used by Vite. The frontend API URL belongs in `ott-frontend/.env` and must end in `/api/v1`.

For an isolated local database instead of PostgreSQL, `DATABASE_URL=sqlite+aiosqlite:///./streamvibe.db` uses a SQLite file in the backend working directory. Do not use the example JWT secret outside local development.

## API contract

All application routes begin with `/api/v1`.

| Method | Route | Authentication | Purpose |
| --- | --- | --- | --- |
| `POST` | `/auth/register` | No | Create an account and receive an access token. |
| `POST` | `/auth/login` | No | Exchange email and password for an access token. |
| `GET` | `/me` | Bearer token | Retrieve the authenticated user and their current subscription. |
| `GET` | `/plans` | No | List available plan definitions. |
| `POST` | `/subscriptions/checkout` | Bearer token | Wait five seconds, then record a trial or active subscription. |

### Register request

```json
{
  "display_name": "Taylor",
  "email": "taylor@example.com",
  "password": "at-least-8-characters"
}
```

### Checkout request

```json
{
  "plan_slug": "premium",
  "start_trial": false
}
```

Valid `plan_slug` values are `basic`, `standard`, and `premium`. A `start_trial` value of `true` stores the subscription with a `trial` status; otherwise it is stored as `active`.
Checkout is a simulation, not a payment integration; yearly billing is not implemented.

## Integration test

Run `python -m unittest discover -s tests -p "test_api_integration.py"` from the backend directory. The test starts a local API using a temporary SQLite database and does not touch the configured database.

### Error behavior

- Invalid or missing credentials return `401`.
- Reusing an existing email returns `409`.
- A plan that does not exist returns `422`.
- Invalid request input returns FastAPI's standard `422` validation response.

## Database connection check

`tests/test_database_connection.py` is a dedicated database connectivity script. It is deliberately not part of the default test command and has not been executed. Run it only after you have populated `.env` and explicitly want to verify the connection:

```powershell
python tests/test_database_connection.py
```
