"""Manual database connection check.

This script is intentionally not run automatically. Execute it only when a real
DATABASE_URL has been configured and a connection check is explicitly desired.
"""

import asyncio
import sys
from pathlib import Path

from sqlalchemy import text

# Permit `python tests/test_database_connection.py` from the backend root.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import close_database, engine


async def check_database_connection() -> None:
    """Open a connection and issue a harmless database version query."""
    async with engine.connect() as connection:
        database_version = await connection.scalar(text("SELECT version()"))
    print(f"Database connection succeeded: {database_version}")


async def main() -> None:
    """Run the connection check and always close the pool afterward."""
    try:
        await check_database_connection()
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(main())
