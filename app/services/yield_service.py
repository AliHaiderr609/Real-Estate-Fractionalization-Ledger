"""Batch rental yield distribution using Decimal arithmetic."""

from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import LedgerTransaction, Property, TokenLedger
from app.schemas import YieldPayoutItem

TWOPLACES = Decimal("0.01")


def _quantize_money(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def _quantize_percent(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def distribute_yield(
    db: Session,
    *,
    property_id: UUID,
    rental_income_amount: Decimal,
) -> tuple[Decimal, Decimal, list[YieldPayoutItem], list[UUID]]:
    """
    Look up all token holders for a property, compute ownership stakes,
    apply the platform fee, and write payout ledger transactions.
    """
    settings = get_settings()
    fee_rate = Decimal(settings.platform_fee_percent) / Decimal("100")

    property_row = db.execute(
        select(Property).where(Property.id == property_id).with_for_update()
    ).scalar_one_or_none()

    if property_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property {property_id} not found",
        )

    if property_row.tokens_minted <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No tokens have been minted for this property",
        )

    holders = (
        db.execute(
            select(TokenLedger)
            .where(
                TokenLedger.property_id == property_id,
                TokenLedger.token_balance > 0,
            )
            .with_for_update()
        )
        .scalars()
        .all()
    )

    if not holders:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No token holders found for this property",
        )

    platform_fee = _quantize_money(rental_income_amount * fee_rate)
    distributable = _quantize_money(rental_income_amount - platform_fee)

    # Ownership stake = holder balance / total minted supply so 100% of
    # the distributable amount is allocated across current token holders.
    denominator = property_row.tokens_minted

    payouts: list[YieldPayoutItem] = []
    transaction_ids: list[UUID] = []
    allocated = Decimal("0.00")

    for index, holder in enumerate(holders):
        ownership = holder.token_balance / denominator
        ownership_percent = _quantize_percent(ownership * Decimal("100"))

        if index == len(holders) - 1:
            # Last holder absorbs residual cents to keep sum exact.
            net_payout = _quantize_money(distributable - allocated)
        else:
            net_payout = _quantize_money(distributable * ownership)
            allocated += net_payout

        gross_payout = _quantize_money(rental_income_amount * ownership)

        tx = LedgerTransaction(
            property_id=property_id,
            owner_wallet=holder.owner_wallet,
            tx_type="yield_payout",
            amount=net_payout,
            token_amount=holder.token_balance,
            description=(
                f"Yield payout: {ownership_percent}% stake of "
                f"${rental_income_amount} (fee {settings.platform_fee_percent}%)"
            ),
        )
        db.add(tx)
        db.flush()

        payouts.append(
            YieldPayoutItem(
                owner_wallet=holder.owner_wallet,
                token_balance=holder.token_balance,
                ownership_percent=ownership_percent,
                gross_payout=gross_payout,
                net_payout=net_payout,
            )
        )
        transaction_ids.append(tx.id)

    # Record platform fee as its own audit row.
    fee_tx = LedgerTransaction(
        property_id=property_id,
        owner_wallet="PLATFORM",
        tx_type="fee",
        amount=platform_fee,
        token_amount=None,
        description=f"Platform service fee ({settings.platform_fee_percent}%)",
    )
    db.add(fee_tx)
    db.flush()
    transaction_ids.append(fee_tx.id)

    return platform_fee, distributable, payouts, transaction_ids
