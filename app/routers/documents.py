"""Document onboarding endpoint — AI deed/lease parser integration."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Property
from app.schemas import OnboardDocumentRequest, OnboardDocumentResponse, PropertyRead
from app.services.document_parser import parse_deed_or_lease

router = APIRouter(tags=["documents"])


@router.post(
    "/onboard-property-document",
    response_model=OnboardDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def onboard_property_document(
    payload: OnboardDocumentRequest,
    db: Session = Depends(get_db),
) -> OnboardDocumentResponse:
    try:
        extracted = parse_deed_or_lease(payload.document_text)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    expiry_dt = datetime(
        extracted.lease_expiry_date.year,
        extracted.lease_expiry_date.month,
        extracted.lease_expiry_date.day,
        tzinfo=timezone.utc,
    )

    prop = Property(
        address=extracted.property_address,
        landlord_name=extracted.landlord_name,
        monthly_rent_value=extracted.monthly_rent_value,
        lease_expiry_date=expiry_dt,
        total_value=payload.total_value,
        total_tokens=payload.total_tokens,
    )
    db.add(prop)
    db.commit()
    db.refresh(prop)

    return OnboardDocumentResponse(
        extracted=extracted,
        property=PropertyRead.model_validate(prop),
    )
