"""Property CRUD and investor query routes."""

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import LedgerTransaction, Property, TokenLedger
from app.schemas import (
    InvestorHolding,
    InvestorSummary,
    LedgerTransactionRead,
    PropertyCreate,
    PropertyRead,
)

router = APIRouter(tags=["properties"])


@router.post("/properties", response_model=PropertyRead, status_code=status.HTTP_201_CREATED)
def create_property(payload: PropertyCreate, db: Session = Depends(get_db)) -> Property:
    lease_dt = None
    if payload.lease_expiry_date is not None:
        lease_dt = datetime(
            payload.lease_expiry_date.year,
            payload.lease_expiry_date.month,
            payload.lease_expiry_date.day,
            tzinfo=timezone.utc,
        )

    prop = Property(
        total_value=payload.total_value,
        total_tokens=payload.total_tokens,
        address=payload.address,
        landlord_name=payload.landlord_name,
        monthly_rent_value=payload.monthly_rent_value,
        lease_expiry_date=lease_dt,
        tokens_minted=Decimal("0"),
    )
    db.add(prop)
    db.commit()
    db.refresh(prop)
    return prop


@router.get("/properties", response_model=list[PropertyRead])
def list_properties(db: Session = Depends(get_db)) -> list[Property]:
    return list(db.execute(select(Property).order_by(Property.created_at.desc())).scalars().all())


@router.get("/properties/{property_id}", response_model=PropertyRead)
def get_property(property_id: UUID, db: Session = Depends(get_db)) -> Property:
    prop = db.get(Property, property_id)
    if prop is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return prop


@router.get("/investors/{owner_wallet}/summary", response_model=InvestorSummary)
def investor_summary(
    owner_wallet: str,
    q: str | None = Query(None, description="Optional search filter over tx description/type"),
    db: Session = Depends(get_db),
) -> InvestorSummary:
    wallet = owner_wallet.strip()
    holdings_rows = (
        db.execute(
            select(TokenLedger, Property)
            .join(Property, Property.id == TokenLedger.property_id)
            .where(TokenLedger.owner_wallet == wallet, TokenLedger.token_balance > 0)
        )
        .all()
    )

    holdings: list[InvestorHolding] = []
    for ledger, prop in holdings_rows:
        ownership = ledger.token_balance / prop.total_tokens
        ownership_percent = (ownership * Decimal("100")).quantize(
            Decimal("0.000001"), rounding=ROUND_HALF_UP
        )
        value_share = (prop.total_value * ownership).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        holdings.append(
            InvestorHolding(
                property_id=prop.id,
                address=prop.address,
                token_balance=ledger.token_balance,
                total_tokens=prop.total_tokens,
                ownership_percent=ownership_percent,
                property_value_share=value_share,
            )
        )

    tx_query = select(LedgerTransaction).where(LedgerTransaction.owner_wallet == wallet)
    if q:
        like = f"%{q}%"
        tx_query = tx_query.where(
            (LedgerTransaction.description.ilike(like)) | (LedgerTransaction.tx_type.ilike(like))
        )
    tx_query = tx_query.order_by(LedgerTransaction.created_at.desc())
    transactions = list(db.execute(tx_query).scalars().all())

    total_yield = sum(
        (tx.amount for tx in transactions if tx.tx_type == "yield_payout"),
        Decimal("0.00"),
    )

    return InvestorSummary(
        owner_wallet=wallet,
        holdings=holdings,
        total_yield_earned=total_yield,
        transactions=[LedgerTransactionRead.model_validate(tx) for tx in transactions],
    )
