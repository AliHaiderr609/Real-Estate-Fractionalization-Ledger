"""Token minting endpoint with concurrency-safe pool checks."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import MintFractionsRequest, MintFractionsResponse, TokenLedgerRead
from app.services.mint_service import mint_fractions

router = APIRouter(tags=["mint"])


@router.post("/mint-fractions", response_model=MintFractionsResponse)
def mint_fractions_endpoint(
    payload: MintFractionsRequest,
    db: Session = Depends(get_db),
) -> MintFractionsResponse:
    ledger_entry, tokens_remaining, tx = mint_fractions(
        db,
        property_id=payload.property_id,
        owner_wallet=payload.owner_wallet,
        token_amount=payload.token_amount,
    )
    db.commit()
    db.refresh(ledger_entry)
    db.refresh(tx)

    return MintFractionsResponse(
        ledger_entry=TokenLedgerRead.model_validate(ledger_entry),
        tokens_remaining=tokens_remaining,
        transaction_id=tx.id,
    )
