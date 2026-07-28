"""Unit tests for mint pool invariants and document parsing (SQLite)."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.services.document_parser import parse_deed_or_lease


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_mint_cannot_exceed_pool(client: TestClient):
    create = client.post(
        "/properties",
        json={"total_value": "1000000", "total_tokens": "1000", "address": "1 Test St"},
    )
    assert create.status_code == 201
    property_id = create.json()["id"]

    ok = client.post(
        "/mint-fractions",
        json={"property_id": property_id, "owner_wallet": "wallet-a", "token_amount": "600"},
    )
    assert ok.status_code == 200
    assert Decimal(ok.json()["tokens_remaining"]) == Decimal("400")

    overflow = client.post(
        "/mint-fractions",
        json={"property_id": property_id, "owner_wallet": "wallet-b", "token_amount": "500"},
    )
    assert overflow.status_code == 409

    fill = client.post(
        "/mint-fractions",
        json={"property_id": property_id, "owner_wallet": "wallet-b", "token_amount": "400"},
    )
    assert fill.status_code == 200
    assert Decimal(fill.json()["tokens_remaining"]) == Decimal("0")


def test_distribute_yield_uses_decimal_stakes(client: TestClient):
    create = client.post(
        "/properties",
        json={"total_value": "1000000", "total_tokens": "10000", "address": "2 Yield Ave"},
    )
    property_id = create.json()["id"]

    client.post(
        "/mint-fractions",
        json={"property_id": property_id, "owner_wallet": "alice", "token_amount": "2300"},
    )
    client.post(
        "/mint-fractions",
        json={"property_id": property_id, "owner_wallet": "bob", "token_amount": "7700"},
    )

    resp = client.post(
        "/distribute-yield",
        json={"property_id": property_id, "rental_income_amount": "5000"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert Decimal(body["platform_fee"]) == Decimal("125.00")  # 2.5%
    assert Decimal(body["distributable_amount"]) == Decimal("4875.00")

    payouts = {p["owner_wallet"]: p for p in body["payouts"]}
    assert Decimal(payouts["alice"]["ownership_percent"]) == Decimal("23.000000")
    # 23% of 4875 = 1121.25
    assert Decimal(payouts["alice"]["net_payout"]) == Decimal("1121.25")
    # Bob gets the residual so sum is exact
    assert Decimal(payouts["bob"]["net_payout"]) == Decimal("3753.75")
    assert sum(Decimal(p["net_payout"]) for p in body["payouts"]) == Decimal("4875.00")


def test_parse_deed_fallback_regex():
    text = """
    Residential Lease Agreement
    Property Address: 742 Evergreen Terrace, Springfield, IL 62704
    Landlord Name: Jane Doe Holdings LLC
    Monthly Rent: $5,000.00
    Lease Expiry Date: 2027-12-31
    """
    extracted = parse_deed_or_lease(text)
    assert "742 Evergreen" in extracted.property_address
    assert extracted.monthly_rent_value == Decimal("5000.00")
    assert "Jane Doe" in extracted.landlord_name
    assert str(extracted.lease_expiry_date) == "2027-12-31"


def test_onboard_property_document(client: TestClient):
    text = """
    Property Address: 100 Market Street, Austin, TX 78701
    Landlord: Acme Realty Partners
    Monthly Rent: $4200
    Lease Expiry Date: 2028-06-15
    """
    resp = client.post(
        "/onboard-property-document",
        json={"document_text": text, "total_value": "850000", "total_tokens": "850000"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["property"]["address"].startswith("100 Market")
    assert Decimal(body["extracted"]["monthly_rent_value"]) == Decimal("4200")


def test_investor_summary(client: TestClient):
    create = client.post(
        "/properties",
        json={"total_value": "500000", "total_tokens": "5000", "address": "9 Audit Rd"},
    )
    property_id = create.json()["id"]
    client.post(
        "/mint-fractions",
        json={"property_id": property_id, "owner_wallet": "investor-1", "token_amount": "500"},
    )
    summary = client.get("/investors/investor-1/summary")
    assert summary.status_code == 200
    data = summary.json()
    assert len(data["holdings"]) == 1
    assert data["holdings"][0]["property_id"] == property_id
