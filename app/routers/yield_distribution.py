"""Rental yield distribution endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import DistributeYieldRequest, DistributeYieldResponse
from app.services.yield_service import distribute_yield

router = APIRouter(tags=["yield"])


@router.post("/distribute-yield", response_model=DistributeYieldResponse)
def distribute_yield_endpoint(
    payload: DistributeYieldRequest,
    db: Session = Depends(get_db),
) -> DistributeYieldResponse:
    platform_fee, distributable, payouts, transaction_ids = distribute_yield(
        db,
        property_id=payload.property_id,
        rental_income_amount=payload.rental_income_amount,
    )
    db.commit()

    return DistributeYieldResponse(
        property_id=payload.property_id,
        rental_income_amount=payload.rental_income_amount,
        platform_fee=platform_fee,
        distributable_amount=distributable,
        payouts=payouts,
        transaction_ids=transaction_ids,
    )
