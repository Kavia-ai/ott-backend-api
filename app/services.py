import asyncio
from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Subscription, User
from app.schemas import MeResponse, PlanResponse, SubscriptionResponse
from app.security import hash_password, verify_password


@dataclass(frozen=True)
class Plan:
    """Immutable plan definition shared by pricing and checkout services."""

    slug: str
    name: str
    description: str
    monthly_price: str
    emoji: str


PLANS: dict[str, Plan] = {
    "basic": Plan(
        slug="basic",
        name="Basic",
        description=(
            "Enjoy an extensive library of movies and shows, featuring a range "
            "of content, including recently released titles."
        ),
        monthly_price="9.99",
        emoji="🎬",
    ),
    "standard": Plan(
        slug="standard",
        name="Standard",
        description=(
            "Access a wider selection of movies and shows, including most new "
            "releases and exclusive content."
        ),
        monthly_price="12.99",
        emoji="⭐",
    ),
    "premium": Plan(
        slug="premium",
        name="Premium",
        description=(
            "Access the widest selection of movies and shows, including all new "
            "releases and offline viewing."
        ),
        monthly_price="14.99",
        emoji="👑",
    ),
}


class UserService:
    """Coordinates user creation and credential validation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def register(
        self,
        *,
        display_name: str,
        email: str,
        password: str,
    ) -> User:
        normalized_email = email.lower()
        existing_user = await self.session.scalar(
            select(User).where(User.email == normalized_email)
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account already exists for this email address.",
            )

        user = User(
            display_name=display_name.strip(),
            email=normalized_email,
            password_hash=hash_password(password),
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def authenticate(self, *, email: str, password: str) -> User:
        user = await self.session.scalar(
            select(User).where(User.email == email.lower())
        )
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email or password is incorrect.",
            )
        return user


class SubscriptionService:
    """Coordinates plan listing, checkout simulation, and profile presentation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def list_plans(self) -> list[PlanResponse]:
        return [PlanResponse(**plan.__dict__) for plan in PLANS.values()]

    async def checkout(
        self,
        *,
        user: User,
        plan_slug: str,
        start_trial: bool,
    ) -> Subscription:
        plan = PLANS.get(plan_slug)
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The selected plan is not available.",
            )

        # This preserves the product's deliberate five-second payment experience
        # while leaving a clear seam for a real payment-provider integration.
        await asyncio.sleep(5)

        await self.session.execute(
            update(Subscription)
            .where(
                Subscription.user_id == user.id,
                Subscription.is_current.is_(True),
            )
            .values(is_current=False)
        )
        subscription = Subscription(
            user_id=user.id,
            plan_slug=plan.slug,
            status="trial" if start_trial else "active",
        )
        self.session.add(subscription)
        await self.session.commit()
        await self.session.refresh(subscription)
        return subscription

    async def build_profile(self, user: User) -> MeResponse:
        subscription = await self.session.scalar(
            select(Subscription)
            .where(
                Subscription.user_id == user.id,
                Subscription.is_current.is_(True),
            )
            .order_by(Subscription.created_at.desc())
        )
        return MeResponse(
            id=user.id,
            display_name=user.display_name,
            email=user.email,
            subscription=self._to_subscription_response(subscription)
            if subscription
            else None,
        )

    @staticmethod
    def _to_subscription_response(
        subscription: Subscription,
    ) -> SubscriptionResponse:
        plan = PLANS[subscription.plan_slug]
        return SubscriptionResponse(
            plan_slug=subscription.plan_slug,
            plan_name=plan.name,
            status=subscription.status,
            is_trial=subscription.status == "trial",
            emoji=plan.emoji,
            created_at=subscription.created_at,
        )
