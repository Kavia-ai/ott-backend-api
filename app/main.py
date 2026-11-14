from contextlib import asynccontextmanager

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import close_database, create_tables_if_needed, get_database_session
from app.models import User
from app.schemas import (
    CheckoutRequest,
    LoginRequest,
    MeResponse,
    PlanResponse,
    RegisterRequest,
    SubscriptionResponse,
    TokenResponse,
)
from app.security import create_access_token, decode_access_token
from app.services import SubscriptionService, UserService


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize and clean up infrastructure owned by the application."""
    await create_tables_if_needed()
    yield
    await close_database()


settings = get_settings()
app = FastAPI(
    title="StreamVibe OTT API",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_database_session),
) -> User:
    """Resolve a valid bearer token to its persisted user."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
        )

    try:
        user_id = decode_access_token(credentials.credentials)
    except jwt.InvalidTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The access token is invalid or expired.",
        ) from error

    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The token user no longer exists.",
        )
    return user


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """Expose a minimal liveness endpoint."""
    return {"status": "ok"}


@app.post(
    "/api/v1/auth/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["auth"],
)
async def register(
    payload: RegisterRequest,
    session: AsyncSession = Depends(get_database_session),
) -> TokenResponse:
    """Create a user account and return an authenticated session token."""
    user = await UserService(session).register(
        display_name=payload.display_name,
        email=str(payload.email),
        password=payload.password,
    )
    return TokenResponse(access_token=create_access_token(user.id))


@app.post("/api/v1/auth/login", response_model=TokenResponse, tags=["auth"])
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_database_session),
) -> TokenResponse:
    """Authenticate an account and return an authenticated session token."""
    user = await UserService(session).authenticate(
        email=str(payload.email),
        password=payload.password,
    )
    return TokenResponse(access_token=create_access_token(user.id))


@app.get("/api/v1/me", response_model=MeResponse, tags=["profile"])
async def get_me(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database_session),
) -> MeResponse:
    """Return the current account with its selected plan, if any."""
    return await SubscriptionService(session).build_profile(user)


@app.get("/api/v1/plans", response_model=list[PlanResponse], tags=["plans"])
async def list_plans(
    session: AsyncSession = Depends(get_database_session),
) -> list[PlanResponse]:
    """Return the plans that may be selected by a user."""
    return SubscriptionService(session).list_plans()


@app.post(
    "/api/v1/subscriptions/checkout",
    response_model=SubscriptionResponse,
    tags=["subscriptions"],
)
async def checkout(
    payload: CheckoutRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database_session),
) -> SubscriptionResponse:
    """Simulate payment processing and enroll the user in the chosen plan."""
    subscription_service = SubscriptionService(session)
    subscription = await subscription_service.checkout(
        user=user,
        plan_slug=payload.plan_slug,
        start_trial=payload.start_trial,
    )
    return subscription_service._to_subscription_response(subscription)
