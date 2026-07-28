"""Mint service with SELECT FOR UPDATE row locking to prevent over-minting."""

from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import LedgerTransaction, Property, TokenLedger


def mint_fractions(
    db: Session,
    *,
    property_id: UUID,
    owner_wallet: str,
    token_amount: Decimal,
) -> tuple[TokenLedger, Decimal, LedgerTransaction]:
    """
    Mint tokens to a wallet while guaranteeing the sum of distributed tokens
    never exceeds the property's total_tokens pool.

    Uses SELECT FOR UPDATE on the property row so concurrent mint requests
    serialize against the same pool counter.
    """
    # Lock the property row for the duration of this transaction.
    property_row = db.execute(
        select(Property).where(Property.id == property_id).with_for_update()
    ).scalar_one_or_none()

    if property_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property {property_id} not found",
        )

    tokens_remaining = property_row.total_tokens - property_row.tokens_minted
    if token_amount > tokens_remaining:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Insufficient token pool: requested {token_amount}, "
                f"remaining {tokens_remaining} of {property_row.total_tokens}"
            ),
        )

    # Also lock any existing ledger row for this (property, wallet) pair.
    ledger_entry = db.execute(
        select(TokenLedger)
        .where(
            TokenLedger.property_id == property_id,
            TokenLedger.owner_wallet == owner_wallet,
        )
        .with_for_update()
    ).scalar_one_or_none()

    if ledger_entry is None:
        ledger_entry = TokenLedger(
            property_id=property_id,
            owner_wallet=owner_wallet,
            token_balance=token_amount,
        )
        db.add(ledger_entry)
    else:
        ledger_entry.token_balance = ledger_entry.token_balance + token_amount

    property_row.tokens_minted = property_row.tokens_minted + token_amount

    tx = LedgerTransaction(
        property_id=property_id,
        owner_wallet=owner_wallet,
        tx_type="mint",
        amount=Decimal("0"),
        token_amount=token_amount,
        description=f"Minted {token_amount} tokens",
    )
    db.add(tx)
    db.flush()

    remaining_after = property_row.total_tokens - property_row.tokens_minted
    return ledger_entry, remaining_after, tx
