"""
Live Ledger Auditing Dashboard — Institutional Asset Management UI.

Run:
    streamlit run app_dashboard.py
"""

from __future__ import annotations

import math
import os
from decimal import Decimal

import httpx
import pandas as pd
import streamlit as st

API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
PAGE_SIZE = 8

st.set_page_config(
    page_title="RWA Institutional Ledger",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Design system ───────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

      :root {
        --bg: #0B0F19;
        --bg-alt: #0D1117;
        --surface: #161B22;
        --surface-2: #1C2128;
        --border: #30363D;
        --border-soft: #21262D;
        --text: #F0F6FC;
        --muted: #8B949E;
        --emerald: #2EA44F;
        --emerald-dim: rgba(46, 164, 79, 0.14);
        --indigo: #58A6FF;
        --indigo-dim: rgba(88, 166, 255, 0.12);
        --danger: #F85149;
        --amber: #D29922;
      }

      html, body, [class*="css"], .stApp {
        font-family: "IBM Plex Sans", sans-serif !important;
        color: var(--text);
      }

      .stApp {
        background:
          radial-gradient(ellipse 70% 45% at 0% 0%, rgba(88,166,255,0.07) 0%, transparent 55%),
          radial-gradient(ellipse 50% 35% at 100% 0%, rgba(46,164,79,0.05) 0%, transparent 50%),
          linear-gradient(180deg, #0B0F19 0%, #0D1117 100%);
      }

      /* Hide Streamlit chrome */
      #MainMenu, footer, header { visibility: hidden; }
      [data-testid="stToolbar"], [data-testid="stDecoration"] { display: none; }
      .block-container {
        padding-top: 1.25rem !important;
        padding-bottom: 3rem !important;
        max-width: 1280px;
      }

      /* Top bar */
      .topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        padding: 0.7rem 1.1rem;
        margin-bottom: 1.35rem;
        background: rgba(22, 27, 34, 0.92);
        border: 1px solid var(--border);
        border-radius: 10px;
        box-shadow: 0 8px 28px rgba(0,0,0,0.28);
        backdrop-filter: blur(8px);
      }
      .topbar-left {
        display: flex;
        align-items: center;
        gap: 0.85rem;
        min-width: 0;
      }
      .logo-mark {
        width: 34px;
        height: 34px;
        border-radius: 8px;
        background: linear-gradient(145deg, #1f6feb 0%, #238636 100%);
        display: grid;
        place-items: center;
        font-weight: 700;
        font-size: 0.95rem;
        color: #fff;
        letter-spacing: -0.04em;
        flex-shrink: 0;
      }
      .logo-text {
        display: flex;
        flex-direction: column;
        line-height: 1.15;
      }
      .logo-text strong {
        font-size: 0.95rem;
        font-weight: 600;
        color: var(--text);
        letter-spacing: 0.01em;
      }
      .logo-text span {
        font-size: 0.72rem;
        color: var(--muted);
        letter-spacing: 0.04em;
        text-transform: uppercase;
      }
      .net-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        padding: 0.35rem 0.75rem;
        border-radius: 999px;
        border: 1px solid var(--border);
        background: var(--surface-2);
        color: var(--muted);
        font-size: 0.78rem;
        font-family: "IBM Plex Mono", monospace;
        white-space: nowrap;
      }
      .net-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: var(--emerald);
        box-shadow: 0 0 0 3px var(--emerald-dim);
      }
      .wallet-chip {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.4rem 0.8rem;
        border-radius: 8px;
        border: 1px solid var(--border);
        background: var(--surface);
        color: var(--text);
        font-size: 0.8rem;
        font-family: "IBM Plex Mono", monospace;
      }
      .wallet-chip .avatar {
        width: 22px;
        height: 22px;
        border-radius: 50%;
        background: var(--indigo-dim);
        border: 1px solid rgba(88,166,255,0.35);
        display: grid;
        place-items: center;
        color: var(--indigo);
        font-size: 0.65rem;
        font-weight: 700;
      }

      /* Section chrome */
      .section-title {
        font-size: 1.05rem;
        font-weight: 600;
        color: var(--text);
        margin: 0 0 0.35rem 0;
        letter-spacing: -0.01em;
      }
      .section-sub {
        color: var(--muted);
        font-size: 0.86rem;
        margin-bottom: 1rem;
      }
      .panel {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1.15rem 1.25rem 1.25rem;
        margin-bottom: 1.1rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.22);
      }
      .panel-label {
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--muted);
        margin-bottom: 0.85rem;
      }

      /* KPI cards */
      .kpi-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 0.85rem;
        margin-bottom: 1.25rem;
      }
      @media (max-width: 900px) {
        .kpi-grid { grid-template-columns: 1fr; }
        .topbar { flex-wrap: wrap; }
      }
      .kpi-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1rem 1.1rem 1.05rem;
        box-shadow: 0 8px 24px rgba(0,0,0,0.24);
        position: relative;
        overflow: hidden;
      }
      .kpi-card::before {
        content: "";
        position: absolute;
        inset: 0 auto 0 0;
        width: 3px;
        background: var(--indigo);
      }
      .kpi-card.kpi-yield::before { background: var(--emerald); }
      .kpi-card.kpi-equity::before { background: var(--indigo); }
      .kpi-label {
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.07em;
        text-transform: uppercase;
        color: var(--muted);
        margin-bottom: 0.45rem;
      }
      .kpi-value {
        font-family: "IBM Plex Mono", monospace;
        font-size: 1.45rem;
        font-weight: 600;
        color: var(--text);
        letter-spacing: -0.02em;
        line-height: 1.2;
      }
      .kpi-hint {
        margin-top: 0.35rem;
        font-size: 0.75rem;
        color: var(--muted);
      }
      .kpi-value.accent-indigo { color: var(--indigo); }
      .kpi-value.accent-emerald { color: var(--emerald); }

      /* Tabs */
      .stTabs [data-baseweb="tab-list"] {
        gap: 0.4rem;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 0.35rem;
        margin-bottom: 0.5rem;
      }
      .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 7px;
        color: var(--muted) !important;
        font-weight: 600;
        font-size: 0.88rem;
        padding: 0.55rem 1rem;
      }
      .stTabs [aria-selected="true"] {
        background: var(--surface-2) !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
        box-shadow: inset 0 -2px 0 var(--indigo);
      }
      .stTabs [data-baseweb="tab-highlight"],
      .stTabs [data-baseweb="tab-border"] {
        display: none;
      }
      .stTabs [data-baseweb="tab-panel"] {
        padding-top: 1rem;
      }

      /* Inputs */
      .stTextInput input, .stNumberInput input, .stTextArea textarea,
      [data-baseweb="select"] > div {
        background-color: var(--bg-alt) !important;
        color: var(--text) !important;
        border-color: var(--border) !important;
        border-radius: 8px !important;
        font-family: "IBM Plex Sans", sans-serif !important;
      }
      .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
        border-color: var(--indigo) !important;
        box-shadow: 0 0 0 1px var(--indigo) !important;
      }
      label, .stRadio label, [data-testid="stWidgetLabel"] p {
        color: var(--muted) !important;
        font-size: 0.82rem !important;
        font-weight: 500 !important;
      }
      div[role="radiogroup"] label {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        padding: 0.35rem 0.7rem !important;
      }

      /* Buttons — secondary default, accent primary */
      .stButton > button, .stFormSubmitButton > button {
        background: #21262D !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        letter-spacing: 0.01em;
        transition: background 0.15s ease, border-color 0.15s ease;
        box-shadow: none !important;
      }
      .stButton > button:hover, .stFormSubmitButton > button:hover {
        background: #30363D !important;
        border-color: #484F58 !important;
        color: var(--text) !important;
      }
      .stButton > button[kind="primary"],
      .stFormSubmitButton > button[kind="primary"],
      button[data-testid="baseButton-primary"],
      .stButton > button[kind="primaryFormSubmit"],
      .stFormSubmitButton > button[data-testid="baseButton-primary"] {
        background: #1F6FEB !important;
        border: 1px solid #388BFD !important;
        color: #FFFFFF !important;
      }
      .stButton > button[kind="primary"]:hover,
      .stFormSubmitButton > button[kind="primary"]:hover,
      button[data-testid="baseButton-primary"]:hover {
        background: #388BFD !important;
        border-color: #58A6FF !important;
      }

      /* Metrics / alerts / dividers */
      div[data-testid="stMetric"] {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 0.75rem 1rem;
        box-shadow: 0 6px 18px rgba(0,0,0,0.2);
      }
      div[data-testid="stMetric"] label { color: var(--muted) !important; }
      div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-family: "IBM Plex Mono", monospace !important;
        color: var(--text) !important;
      }
      hr { border-color: var(--border-soft) !important; }
      .stAlert { border-radius: 8px !important; }

      /* Dataframes */
      [data-testid="stDataFrame"] {
        border: 1px solid var(--border);
        border-radius: 10px;
        overflow: hidden;
        background: var(--surface);
      }
      [data-testid="stDataFrame"] th {
        background: var(--surface-2) !important;
        color: var(--muted) !important;
        font-size: 0.72rem !important;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        padding: 0.65rem 0.75rem !important;
      }
      [data-testid="stDataFrame"] td {
        padding: 0.6rem 0.75rem !important;
        font-family: "IBM Plex Mono", monospace;
        font-size: 0.8rem !important;
      }

      /* Custom HTML table (ledger) */
      .ledger-table-wrap {
        border: 1px solid var(--border);
        border-radius: 10px;
        overflow: hidden;
        background: var(--surface);
        box-shadow: 0 8px 24px rgba(0,0,0,0.2);
      }
      table.ledger-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.82rem;
      }
      table.ledger-table thead th {
        text-align: left;
        background: var(--surface-2);
        color: var(--muted);
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        padding: 0.75rem 0.9rem;
        border-bottom: 1px solid var(--border);
      }
      table.ledger-table tbody td {
        padding: 0.7rem 0.9rem;
        border-bottom: 1px solid var(--border-soft);
        color: var(--text);
        font-family: "IBM Plex Mono", monospace;
        vertical-align: middle;
      }
      table.ledger-table tbody tr:last-child td { border-bottom: none; }
      table.ledger-table tbody tr:hover td { background: rgba(88,166,255,0.04); }
      .tx-pill {
        display: inline-block;
        padding: 0.15rem 0.5rem;
        border-radius: 999px;
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.03em;
        text-transform: uppercase;
        font-family: "IBM Plex Sans", sans-serif;
      }
      .tx-yield {
        color: var(--emerald);
        background: var(--emerald-dim);
        border: 1px solid rgba(46,164,79,0.3);
      }
      .tx-mint {
        color: var(--indigo);
        background: var(--indigo-dim);
        border: 1px solid rgba(88,166,255,0.3);
      }
      .tx-fee {
        color: var(--amber);
        background: rgba(210,153,34,0.12);
        border: 1px solid rgba(210,153,34,0.3);
      }
      .amt-pos { color: var(--emerald); font-weight: 600; }
      .amt-neu { color: var(--muted); }
      .pager-meta {
        color: var(--muted);
        font-size: 0.78rem;
        font-family: "IBM Plex Mono", monospace;
        margin-top: 0.55rem;
      }

      /* JSON / code */
      .stJson, pre {
        background: var(--bg-alt) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── API helpers (unchanged contracts) ───────────────────────────────────────
def api_client() -> httpx.Client:
    return httpx.Client(base_url=API_BASE, timeout=30.0)


def fetch_properties() -> list[dict]:
    with api_client() as client:
        resp = client.get("/properties")
        resp.raise_for_status()
        return resp.json()


def check_api_health() -> bool:
    try:
        with api_client() as client:
            resp = client.get("/health")
            return resp.status_code == 200
    except httpx.HTTPError:
        return False


def fmt_money(value: Decimal | float | str | int) -> str:
    return f"${Decimal(str(value)):,.2f}"


def fmt_tokens(value: Decimal | float | str | int) -> str:
    return f"{Decimal(str(value)):,.8f}".rstrip("0").rstrip(".")


def render_kpi_row(cards: list[dict]) -> None:
    classes = ["", "kpi-yield", "kpi-equity"]
    cells = []
    for i, card in enumerate(cards):
        accent = card.get("accent", "")
        value_class = f"kpi-value {accent}".strip()
        cells.append(
            f"""
            <div class="kpi-card {classes[i % 3]}">
              <div class="kpi-label">{card['label']}</div>
              <div class="{value_class}">{card['value']}</div>
              <div class="kpi-hint">{card.get('hint', '')}</div>
            </div>
            """
        )
    st.markdown(f'<div class="kpi-grid">{"".join(cells)}</div>', unsafe_allow_html=True)


def paginate_df(df: pd.DataFrame, page: int, page_size: int = PAGE_SIZE) -> tuple[pd.DataFrame, int]:
    total_pages = max(1, math.ceil(len(df) / page_size))
    page = max(1, min(page, total_pages))
    start = (page - 1) * page_size
    return df.iloc[start : start + page_size], total_pages


def render_ledger_html(df: pd.DataFrame) -> None:
    """Paginated-ready HTML table with color-coded transaction types."""
    if df.empty:
        st.info("No transactions match this filter.")
        return

    rows_html: list[str] = []
    for _, row in df.iterrows():
        tx_type = str(row.get("tx_type", ""))
        pill_class = {
            "yield_payout": "tx-yield",
            "mint": "tx-mint",
            "fee": "tx-fee",
        }.get(tx_type, "tx-mint")

        amount = Decimal(str(row.get("amount", 0) or 0))
        if tx_type == "yield_payout" and amount >= 0:
            amt_html = f'<span class="amt-pos">+{fmt_money(amount)}</span>'
        elif tx_type == "fee":
            amt_html = f'<span class="amt-neu">{fmt_money(amount)}</span>'
        elif amount > 0:
            amt_html = f'<span class="amt-pos">+{fmt_money(amount)}</span>'
        else:
            amt_html = f'<span class="amt-neu">{fmt_money(amount)}</span>'

        token_amt = row.get("token_amount")
        token_str = fmt_tokens(token_amt) if token_amt not in (None, "") else "—"
        created = str(row.get("created_at", ""))[:19].replace("T", " ")
        desc = str(row.get("description") or "—")
        if len(desc) > 64:
            desc = desc[:61] + "…"
        prop_id = str(row.get("property_id", ""))[:8] + "…"

        rows_html.append(
            f"""
            <tr>
              <td><span class="tx-pill {pill_class}">{tx_type}</span></td>
              <td>{amt_html}</td>
              <td>{token_str}</td>
              <td>{prop_id}</td>
              <td style="font-family:IBM Plex Sans,sans-serif;color:#8B949E">{desc}</td>
              <td>{created}</td>
            </tr>
            """
        )

    st.markdown(
        f"""
        <div class="ledger-table-wrap">
          <table class="ledger-table">
            <thead>
              <tr>
                <th>Type</th>
                <th>Amount</th>
                <th>Tokens</th>
                <th>Property</th>
                <th>Description</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {''.join(rows_html)}
            </tbody>
          </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Session defaults ────────────────────────────────────────────────────────
if "active_wallet" not in st.session_state:
    st.session_state.active_wallet = "institutional-ops"
if "investor_summary" not in st.session_state:
    st.session_state.investor_summary = None
if "holdings_page" not in st.session_state:
    st.session_state.holdings_page = 1
if "tx_page" not in st.session_state:
    st.session_state.tx_page = 1
if "payout_page" not in st.session_state:
    st.session_state.payout_page = 1
if "last_payouts" not in st.session_state:
    st.session_state.last_payouts = None

api_online = check_api_health()
net_label = "Mainnet Ledger Simulation Active" if api_online else "Ledger API Offline"
net_color = "#2EA44F" if api_online else "#F85149"

# ── Top bar ─────────────────────────────────────────────────────────────────
wallet_display = st.session_state.active_wallet
if len(wallet_display) > 18:
    wallet_short = wallet_display[:8] + "…" + wallet_display[-4:]
else:
    wallet_short = wallet_display

st.markdown(
    f"""
    <div class="topbar">
      <div class="topbar-left">
        <div class="logo-mark">RΞ</div>
        <div class="logo-text">
          <strong>Aetherium RWA Desk</strong>
          <span>Fractionalization &amp; Yield Control</span>
        </div>
      </div>
      <div class="net-pill">
        <span class="net-dot" style="background:{net_color};box-shadow:0 0 0 3px rgba(46,164,79,0.14);"></span>
        {net_label}
      </div>
      <div class="wallet-chip">
        <span class="avatar">OP</span>
        {wallet_short}
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Compact wallet / profile selector (enterprise control)
with st.expander("Operator profile & wallet context", expanded=False):
    st.session_state.active_wallet = st.text_input(
        "Active operator / wallet ID",
        value=st.session_state.active_wallet,
        help="Used as the default context for investor lookups and mint targets.",
    )

# ── Load properties once for KPIs + admin selectors ─────────────────────────
try:
    properties = fetch_properties()
    api_reachable = True
except httpx.HTTPError:
    properties = []
    api_reachable = False

tvl = sum((Decimal(str(p.get("total_value") or 0)) for p in properties), Decimal("0"))
active_props = len(properties)
tokens_outstanding = sum(
    (Decimal(str(p.get("tokens_minted") or 0)) for p in properties), Decimal("0")
)

# Investor equity preview from cached summary (if loaded)
equity_shares = Decimal("0")
yield_earned_kpi = Decimal("0")
if st.session_state.investor_summary:
    yield_earned_kpi = Decimal(str(st.session_state.investor_summary.get("total_yield_earned") or 0))
    equity_shares = sum(
        (
            Decimal(str(h.get("token_balance") or 0))
            for h in st.session_state.investor_summary.get("holdings", [])
        ),
        Decimal("0"),
    )

render_kpi_row(
    [
        {
            "label": "Total Value Locked",
            "value": fmt_money(tvl),
            "hint": f"{active_props} active propert{'y' if active_props == 1 else 'ies'}",
            "accent": "accent-indigo",
        },
        {
            "label": "Yield Distributed",
            "value": fmt_money(yield_earned_kpi),
            "hint": "From loaded investor portfolio context",
            "accent": "accent-emerald",
        },
        {
            "label": "Multi-Tenant Equity Shares",
            "value": fmt_tokens(equity_shares) if equity_shares else fmt_tokens(tokens_outstanding),
            "hint": "Loaded wallet tokens · else network minted supply",
            "accent": "accent-indigo",
        },
    ]
)

if not api_reachable:
    st.warning(f"Cannot reach API at `{API_BASE}`. Start the FastAPI server first.")

admin_tab, investor_tab = st.tabs(
    ["Institutional Admin Control Room", "Investor Equity Portfolio"]
)


# ── Admin View ──────────────────────────────────────────────────────────────
with admin_tab:
    st.markdown(
        '<div class="section-title">Property onboarding</div>'
        '<p class="section-sub">Register assets manually or extract structured fields from deed / lease text.</p>',
        unsafe_allow_html=True,
    )

    with st.container():
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
                    total_value = st.number_input(
                        "Total value (USD)", min_value=0.01, value=1_000_000.0, step=1000.0
                    )
                    landlord = st.text_input("Landlord name")
                with c2:
                    total_tokens = st.number_input(
                        "Total token pool", min_value=0.01, value=1_000_000.0, step=1000.0
                    )
                    monthly_rent = st.number_input(
                        "Monthly rent (USD)", min_value=0.0, value=5000.0, step=100.0
                    )
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
                        st.rerun()
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
                        "Tokenization value (USD)",
                        min_value=0.01,
                        value=1_000_000.0,
                        key="doc_val",
                    )
                with c2:
                    doc_total_tokens = st.number_input(
                        "Token pool size",
                        min_value=0.01,
                        value=1_000_000.0,
                        key="doc_tokens",
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

    st.markdown("---")
    st.markdown(
        '<div class="section-title">Mint fractions</div>'
        '<p class="section-sub">Allocate tokenized equity from a property pool to an investor wallet.</p>',
        unsafe_allow_html=True,
    )

    if properties:
        prop_labels = {
            f"{p.get('address') or 'Untitled'} — {p['id'][:8]}… "
            f"({p['tokens_minted']}/{p['total_tokens']} minted)": p
            for p in properties
        }
        selected_label = st.selectbox("Property", list(prop_labels.keys()), key="mint_prop")
        selected = prop_labels[selected_label]
        with st.form("mint_form"):
            wallet = st.text_input(
                "Owner wallet / user ID",
                value=st.session_state.active_wallet,
            )
            amount = st.number_input(
                "Token amount", min_value=0.00000001, value=1000.0, format="%.8f"
            )
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
                            st.rerun()
                except httpx.HTTPError as exc:
                    st.error(f"Mint failed: {exc}")
    elif api_reachable:
        st.info("No properties onboarded yet. Create one above to begin minting.")

    st.markdown("---")
    st.markdown(
        '<div class="section-title">Distribute rental yield</div>'
        '<p class="section-sub">Batch micro-payments to all token holders by exact ownership stake.</p>',
        unsafe_allow_html=True,
    )

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
                            st.session_state.last_payouts = data
                            st.session_state.payout_page = 1
                            st.success(
                                f"Distributed ${data['distributable_amount']} "
                                f"(platform fee ${data['platform_fee']}) to "
                                f"{len(data['payouts'])} holders."
                            )
                except httpx.HTTPError as exc:
                    st.error(f"Distribution failed: {exc}")

        if st.session_state.last_payouts:
            payouts_df = pd.DataFrame(st.session_state.last_payouts["payouts"])
            page_df, total_pages = paginate_df(
                payouts_df, st.session_state.payout_page, PAGE_SIZE
            )
            st.markdown(
                '<div class="section-title" style="font-size:0.95rem;margin-top:1rem">'
                "Distribution settlement grid</div>",
                unsafe_allow_html=True,
            )
            st.dataframe(
                page_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "owner_wallet": st.column_config.TextColumn("Wallet", width="medium"),
                    "token_balance": st.column_config.NumberColumn("Token balance", format="%.8f"),
                    "ownership_percent": st.column_config.NumberColumn(
                        "Ownership %", format="%.6f%%"
                    ),
                    "gross_payout": st.column_config.NumberColumn("Gross ($)", format="$%.2f"),
                    "net_payout": st.column_config.NumberColumn("Net payout ($)", format="$%.2f"),
                },
            )
            pc1, pc2, pc3 = st.columns([1, 2, 1])
            with pc1:
                if st.button("← Prev", key="payout_prev", disabled=st.session_state.payout_page <= 1):
                    st.session_state.payout_page -= 1
                    st.rerun()
            with pc2:
                st.markdown(
                    f'<div class="pager-meta" style="text-align:center">'
                    f"Page {st.session_state.payout_page} / {total_pages} · "
                    f"{len(payouts_df)} settlements</div>",
                    unsafe_allow_html=True,
                )
            with pc3:
                if st.button(
                    "Next →",
                    key="payout_next",
                    disabled=st.session_state.payout_page >= total_pages,
                ):
                    st.session_state.payout_page += 1
                    st.rerun()


# ── Investor View ───────────────────────────────────────────────────────────
with investor_tab:
    st.markdown(
        '<div class="section-title">Portfolio lookup</div>'
        '<p class="section-sub">Audit equity fractions, historic yield, and the full transaction ledger.</p>',
        unsafe_allow_html=True,
    )

    ic1, ic2 = st.columns([2, 2])
    with ic1:
        wallet_query = st.text_input(
            "Paste wallet / user ID",
            value=st.session_state.active_wallet,
            placeholder="0xABC… or investor-42",
            key="investor_wallet_input",
        )
    with ic2:
        search_tx = st.text_input(
            "Search ledger (optional)",
            placeholder="yield, mint, fee…",
            key="investor_search_input",
        )

    if st.button("Load portfolio", type="primary", key="load_portfolio_btn") and wallet_query.strip():
        try:
            params = {}
            if search_tx.strip():
                params["q"] = search_tx.strip()
            with api_client() as client:
                resp = client.get(
                    f"/investors/{wallet_query.strip()}/summary", params=params
                )
                resp.raise_for_status()
                st.session_state.investor_summary = resp.json()
                st.session_state.active_wallet = wallet_query.strip()
                st.session_state.holdings_page = 1
                st.session_state.tx_page = 1
                st.rerun()
        except httpx.HTTPError as exc:
            st.error(f"Could not load investor summary: {exc}")
            st.session_state.investor_summary = None

    summary = st.session_state.investor_summary
    if summary:
        m1, m2, m3 = st.columns(3)
        m1.metric("Properties held", len(summary["holdings"]))
        m2.metric(
            "Total yield earned",
            fmt_money(summary["total_yield_earned"]),
        )
        m3.metric("Ledger rows", len(summary["transactions"]))

        st.markdown(
            '<div class="section-title" style="font-size:0.95rem;margin-top:0.5rem">'
            "Owned fractions</div>",
            unsafe_allow_html=True,
        )
        if summary["holdings"]:
            holdings_df = pd.DataFrame(summary["holdings"])
            holdings_df["ownership_percent"] = holdings_df["ownership_percent"].astype(float)
            holdings_page_df, holdings_pages = paginate_df(
                holdings_df[
                    [
                        "property_id",
                        "address",
                        "token_balance",
                        "ownership_percent",
                        "property_value_share",
                    ]
                ],
                st.session_state.holdings_page,
                PAGE_SIZE,
            )
            st.dataframe(
                holdings_page_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "property_id": st.column_config.TextColumn("Property ID", width="medium"),
                    "address": st.column_config.TextColumn("Address", width="large"),
                    "token_balance": st.column_config.NumberColumn(
                        "Token balance", format="%.8f"
                    ),
                    "ownership_percent": st.column_config.NumberColumn(
                        "Ownership %", format="%.6f%%"
                    ),
                    "property_value_share": st.column_config.NumberColumn(
                        "Value share ($)", format="$%.2f"
                    ),
                },
            )
            hc1, hc2, hc3 = st.columns([1, 2, 1])
            with hc1:
                if st.button(
                    "← Prev",
                    key="holdings_prev",
                    disabled=st.session_state.holdings_page <= 1,
                ):
                    st.session_state.holdings_page -= 1
                    st.rerun()
            with hc2:
                st.markdown(
                    f'<div class="pager-meta" style="text-align:center">'
                    f"Page {st.session_state.holdings_page} / {holdings_pages} · "
                    f"{len(holdings_df)} holdings</div>",
                    unsafe_allow_html=True,
                )
            with hc3:
                if st.button(
                    "Next →",
                    key="holdings_next",
                    disabled=st.session_state.holdings_page >= holdings_pages,
                ):
                    st.session_state.holdings_page += 1
                    st.rerun()
        else:
            st.info("No token holdings for this wallet.")

        st.markdown(
            '<div class="section-title" style="font-size:0.95rem;margin-top:1rem">'
            "Transaction ledger</div>",
            unsafe_allow_html=True,
        )
        if summary["transactions"]:
            tx_df = pd.DataFrame(summary["transactions"])
            tx_page_df, tx_pages = paginate_df(tx_df, st.session_state.tx_page, PAGE_SIZE)
            render_ledger_html(tx_page_df)
            tc1, tc2, tc3 = st.columns([1, 2, 1])
            with tc1:
                if st.button(
                    "← Prev",
                    key="tx_prev",
                    disabled=st.session_state.tx_page <= 1,
                ):
                    st.session_state.tx_page -= 1
                    st.rerun()
            with tc2:
                st.markdown(
                    f'<div class="pager-meta" style="text-align:center">'
                    f"Page {st.session_state.tx_page} / {tx_pages} · "
                    f"{len(tx_df)} transactions</div>",
                    unsafe_allow_html=True,
                )
            with tc3:
                if st.button(
                    "Next →",
                    key="tx_next",
                    disabled=st.session_state.tx_page >= tx_pages,
                ):
                    st.session_state.tx_page += 1
                    st.rerun()
        else:
            st.info("No transactions match this filter.")
