"""Pydantic request/response schemas."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PropertyCreate(BaseModel):
    total_value: Decimal = Field(..., gt=0, description="Total property valuation in USD")
    total_tokens: Decimal = Field(..., gt=0, description="Total token pool for this property")
    address: str | None = None
    landlord_name: str | None = None
    monthly_rent_value: Decimal | None = Field(None, ge=0)
    lease_expiry_date: date | None = None


class PropertyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    address: str | None
    total_value: Decimal
    total_tokens: Decimal
    tokens_minted: Decimal
    landlord_name: str | None
    monthly_rent_value: Decimal | None
    lease_expiry_date: datetime | None
    created_at: datetime


class TokenLedgerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    property_id: UUID
    owner_wallet: str
    token_balance: Decimal
    purchase_timestamp: datetime


class MintFractionsRequest(BaseModel):
    property_id: UUID
    owner_wallet: str = Field(..., min_length=1, max_length=128)
    token_amount: Decimal = Field(..., gt=0, description="Number of tokens to mint to wallet")

    @field_validator("owner_wallet")
    @classmethod
    def normalize_wallet(cls, v: str) -> str:
        return v.strip()


class MintFractionsResponse(BaseModel):
    ledger_entry: TokenLedgerRead
    tokens_remaining: Decimal
    transaction_id: UUID


class DistributeYieldRequest(BaseModel):
    property_id: UUID
    rental_income_amount: Decimal = Field(..., gt=0, description="Gross rental income to distribute")


class YieldPayoutItem(BaseModel):
    owner_wallet: str
    token_balance: Decimal
    ownership_percent: Decimal
    gross_payout: Decimal
    net_payout: Decimal


class DistributeYieldResponse(BaseModel):
    property_id: UUID
    rental_income_amount: Decimal
    platform_fee: Decimal
    distributable_amount: Decimal
    payouts: list[YieldPayoutItem]
    transaction_ids: list[UUID]


class DeedExtract(BaseModel):
    """Strict structured output from LLM document parsing."""

    property_address: str
    monthly_rent_value: Decimal
    landlord_name: str
    lease_expiry_date: date


class OnboardDocumentRequest(BaseModel):
    document_text: str = Field(..., min_length=20, description="Raw text extract from deed/lease PDF")
    total_value: Decimal = Field(..., gt=0, description="Property valuation used for tokenization")
    total_tokens: Decimal = Field(..., gt=0, description="Token pool size for this property")


class OnboardDocumentResponse(BaseModel):
    extracted: DeedExtract
    property: PropertyRead


class LedgerTransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    property_id: UUID
    owner_wallet: str
    tx_type: str
    amount: Decimal
    token_amount: Decimal | None
    description: str | None
    created_at: datetime


class InvestorHolding(BaseModel):
    property_id: UUID
    address: str | None
    token_balance: Decimal
    total_tokens: Decimal
    ownership_percent: Decimal
    property_value_share: Decimal


class InvestorSummary(BaseModel):
    owner_wallet: str
    holdings: list[InvestorHolding]
    total_yield_earned: Decimal
    transactions: list[LedgerTransactionRead]
