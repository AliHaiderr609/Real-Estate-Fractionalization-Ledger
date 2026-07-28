"""
Live Ledger Auditing Dashboard — Streamlit UI for the RWA Fractionalization Engine.

Run:
    streamlit run app_dashboard.py
"""

from __future__ import annotations

import os
from decimal import Decimal

import httpx
import pandas as pd
import streamlit as st

API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

st.set_page_config(
    page_title="RWA Ledger Dashboard",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Source+Sans+3:wght@400;500;600&display=swap');

      :root {
        --ink: #1a2332;
        --slate: #3d4f63;
        --mist: #e8eef4;
        --paper: #f7f9fb;
        --accent: #0d6e6e;
        --accent-soft: #d4ecec;
        --line: #c5d0dc;
      }

      html, body, [class*="css"] {
        font-family: "Source Sans 3", sans-serif;
        color: var(--ink);
      }

      .stApp {
        background:
          radial-gradient(ellipse 80% 50% at 10% -10%, #d4ecec 0%, transparent 55%),
          radial-gradient(ellipse 60% 40% at 100% 0%, #e8eef4 0%, transparent 50%),
          linear-gradient(180deg, #f7f9fb 0%, #eef3f7 100%);
      }

      h1, h2, h3, .brand {
        font-family: "Fraunces", serif !important;
        letter-spacing: -0.02em;
      }

      .brand {
        font-size: 2.1rem;
        font-weight: 700;
        color: var(--ink);
        margin-bottom: 0.15rem;
      }

      .tagline {
        color: var(--slate);
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
      }

      div[data-testid="stMetric"] {
        background: rgba(255,255,255,0.72);
        border: 1px solid var(--line);
        border-radius: 10px;
        padding: 0.75rem 1rem;
      }

      .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
      }

      .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 8px 8px 0 0;
        font-weight: 600;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


def api_client() -> httpx.Client:
    return httpx.Client(base_url=API_BASE, timeout=30.0)


def fetch_properties() -> list[dict]:
    with api_client() as client:
        resp = client.get("/properties")
        resp.raise_for_status()
        return resp.json()


st.markdown('<div class="brand">RWA Fractionalization Ledger</div>', unsafe_allow_html=True)
st.markdown(
    '<p class="tagline">Audit ownership stakes, mint fractions, and distribute rental yield in real time.</p>',
    unsafe_allow_html=True,
)

admin_tab, investor_tab = st.tabs(["Admin View", "Investor View"])


# ── Admin View ──────────────────────────────────────────────────────────────
with admin_tab:
    st.subheader("Onboard a property")
    onboard_mode = st.radio(
        "Onboarding method",
        ["Manual entry", "Parse deed / lease document"],
        horizontal=True,
    )

    if onboard_mode == "Manual entry":
        with st.form("create_property_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                address = st.text_input("Property address")
                total_value = st.number_input("Total value (USD)", min_value=0.01, value=1_000_000.0, step=1000.0)
                landlord = st.text_input("Landlord name")
            with c2:
                total_tokens = st.number_input("Total token pool", min_value=0.01, value=1_000_000.0, step=1000.0)
                monthly_rent = st.number_input("Monthly rent (USD)", min_value=0.0, value=5000.0, step=100.0)
            submitted = st.form_submit_button("Create property", type="primary")
            if submitted:
                payload = {
                    "address": address or None,
                    "total_value": str(total_value),
                    "total_tokens": str(total_tokens),
                    "landlord_name": landlord or None,
                    "monthly_rent_value": str(monthly_rent) if monthly_rent else None,
                }
                try:
                    with api_client() as client:
                        resp = client.post("/properties", json=payload)
                        resp.raise_for_status()
                    st.success(f"Property created: `{resp.json()['id']}`")
                except httpx.HTTPError as exc:
                    st.error(f"Failed to create property: {exc}")
    else:
        with st.form("parse_document_form", clear_on_submit=False):
            document_text = st.text_area(
                "Paste raw text from deed or rental agreement",
                height=220,
                placeholder=(
                    "Residential Lease Agreement\n"
                    "Property Address: 742 Evergreen Terrace, Springfield, IL 62704\n"
                    "Landlord: Jane Doe Holdings LLC\n"
                    "Monthly Rent: $5,000.00\n"
                    "Lease Expiry Date: 2027-12-31"
                ),
            )
            c1, c2 = st.columns(2)
            with c1:
                doc_total_value = st.number_input(
                    "Tokenization value (USD)", min_value=0.01, value=1_000_000.0, key="doc_val"
                )
            with c2:
                doc_total_tokens = st.number_input(
                    "Token pool size", min_value=0.01, value=1_000_000.0, key="doc_tokens"
                )
            parse_submit = st.form_submit_button("Parse & onboard", type="primary")
            if parse_submit:
                try:
                    with api_client() as client:
                        resp = client.post(
                            "/onboard-property-document",
                            json={
                                "document_text": document_text,
                                "total_value": str(doc_total_value),
                                "total_tokens": str(doc_total_tokens),
                            },
                        )
                        if resp.status_code >= 400:
                            st.error(resp.json().get("detail", resp.text))
                        else:
                            data = resp.json()
                            st.success(f"Onboarded property `{data['property']['id']}`")
                            st.json(data["extracted"])
                except httpx.HTTPError as exc:
                    st.error(f"Onboarding failed: {exc}")

    st.divider()
    st.subheader("Mint fractions")
    try:
        properties = fetch_properties()
    except httpx.HTTPError:
        properties = []
        st.warning(f"Cannot reach API at `{API_BASE}`. Start the FastAPI server first.")

    if properties:
        prop_labels = {
            f"{p.get('address') or 'Untitled'} — {p['id'][:8]}… "
            f"({p['tokens_minted']}/{p['total_tokens']} minted)": p
            for p in properties
        }
        selected_label = st.selectbox("Property", list(prop_labels.keys()), key="mint_prop")
        selected = prop_labels[selected_label]
        with st.form("mint_form"):
            wallet = st.text_input("Owner wallet / user ID")
            amount = st.number_input("Token amount", min_value=0.00000001, value=1000.0, format="%.8f")
            mint_go = st.form_submit_button("Mint fractions", type="primary")
            if mint_go:
                try:
                    with api_client() as client:
                        resp = client.post(
                            "/mint-fractions",
                            json={
                                "property_id": selected["id"],
                                "owner_wallet": wallet,
                                "token_amount": str(amount),
                            },
                        )
                        if resp.status_code >= 400:
                            st.error(resp.json().get("detail", resp.text))
                        else:
                            data = resp.json()
                            st.success(
                                f"Minted {amount} tokens to `{wallet}`. "
                                f"Remaining pool: {data['tokens_remaining']}"
                            )
                except httpx.HTTPError as exc:
                    st.error(f"Mint failed: {exc}")

    st.divider()
    st.subheader("Distribute rental yield")
    if properties:
        yield_labels = {
            f"{p.get('address') or 'Untitled'} — {p['id'][:8]}…": p for p in properties
        }
        yield_label = st.selectbox("Property for yield", list(yield_labels.keys()), key="yield_prop")
        yield_prop = yield_labels[yield_label]
        with st.form("yield_form"):
            rental_income = st.number_input(
                "Rental income amount (USD)",
                min_value=0.01,
                value=float(yield_prop.get("monthly_rent_value") or 5000.0),
                step=100.0,
            )
            yield_go = st.form_submit_button("Execute distribution", type="primary")
            if yield_go:
                try:
                    with api_client() as client:
                        resp = client.post(
                            "/distribute-yield",
                            json={
                                "property_id": yield_prop["id"],
                                "rental_income_amount": str(rental_income),
                            },
                        )
                        if resp.status_code >= 400:
                            st.error(resp.json().get("detail", resp.text))
                        else:
                            data = resp.json()
                            st.success(
                                f"Distributed ${data['distributable_amount']} "
                                f"(platform fee ${data['platform_fee']}) to "
                                f"{len(data['payouts'])} holders."
                            )
                            st.dataframe(pd.DataFrame(data["payouts"]), use_container_width=True)
                except httpx.HTTPError as exc:
                    st.error(f"Distribution failed: {exc}")


# ── Investor View ───────────────────────────────────────────────────────────
with investor_tab:
    st.subheader("Portfolio lookup")
    wallet_query = st.text_input("Paste wallet / user ID", placeholder="0xABC… or investor-42")
    search_tx = st.text_input("Search ledger (optional)", placeholder="yield, mint, fee…")

    if st.button("Load portfolio", type="primary") and wallet_query.strip():
        try:
            params = {}
            if search_tx.strip():
                params["q"] = search_tx.strip()
            with api_client() as client:
                resp = client.get(f"/investors/{wallet_query.strip()}/summary", params=params)
                resp.raise_for_status()
                summary = resp.json()
        except httpx.HTTPError as exc:
            st.error(f"Could not load investor summary: {exc}")
            summary = None

        if summary:
            m1, m2, m3 = st.columns(3)
            m1.metric("Properties held", len(summary["holdings"]))
            m2.metric("Total yield earned", f"${Decimal(str(summary['total_yield_earned'])):,.2f}")
            m3.metric("Ledger rows", len(summary["transactions"]))

            st.markdown("##### Owned fractions")
            if summary["holdings"]:
                holdings_df = pd.DataFrame(summary["holdings"])
                holdings_df["ownership_percent"] = holdings_df["ownership_percent"].astype(float)
                st.dataframe(
                    holdings_df[
                        [
                            "property_id",
                            "address",
                            "token_balance",
                            "ownership_percent",
                            "property_value_share",
                        ]
                    ],
                    use_container_width=True,
                    column_config={
                        "ownership_percent": st.column_config.NumberColumn("Ownership %", format="%.6f%%"),
                        "property_value_share": st.column_config.NumberColumn("Value share ($)", format="$%.2f"),
                    },
                )
            else:
                st.info("No token holdings for this wallet.")

            st.markdown("##### Transaction ledger")
            if summary["transactions"]:
                tx_df = pd.DataFrame(summary["transactions"])
                st.dataframe(tx_df, use_container_width=True, hide_index=True)
            else:
                st.info("No transactions match this filter.")
