"""AI-powered deed / rental agreement parser using structured Pydantic outputs."""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from openai import OpenAI

from app.config import get_settings
from app.schemas import DeedExtract

SYSTEM_PROMPT = """You are a real-estate document extraction engine.
Extract structured fields from property deeds and rental/lease agreements.
Return ONLY valid JSON matching this schema:
{
  "property_address": string,
  "monthly_rent_value": number,
  "landlord_name": string,
  "lease_expiry_date": "YYYY-MM-DD"
}
If a field is missing, use best-effort inference from context.
Never invent an address that is not present in the text.
For monthly_rent_value, strip currency symbols and commas.
"""


def _fallback_regex_extract(document_text: str) -> DeedExtract:
    """
    Lightweight offline extractor used when OPENAI_API_KEY is unset
    or the API call fails. Useful for demos and local development.
    """
    address_match = re.search(
        r"(?:property\s*(?:address|located at|situated at)|premises)\s*[:\-]?\s*(.+)",
        document_text,
        re.IGNORECASE,
    )
    rent_match = re.search(
        r"(?:monthly\s*rent|rent(?:al)?\s*(?:amount|of)?|base\s*rent)\s*[:\-]?\s*\$?\s*([\d,]+(?:\.\d{1,2})?)",
        document_text,
        re.IGNORECASE,
    )
    landlord_match = re.search(
        r"(?:landlord|lessor|owner)\s*(?:name)?\s*[:\-]?\s*([A-Za-z][A-Za-z\s\.\-']{1,80})",
        document_text,
        re.IGNORECASE,
    )
    expiry_match = re.search(
        r"(?:lease\s*(?:expir(?:y|es|ation)|end(?:s|ing)?|terminat(?:e|ion))\s*(?:date)?)\s*[:\-]?\s*"
        r"(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})",
        document_text,
        re.IGNORECASE,
    )

    if not (address_match and rent_match and landlord_match and expiry_match):
        raise ValueError(
            "Could not extract all required fields from document text. "
            "Provide clearer labels or configure OPENAI_API_KEY for LLM extraction."
        )

    rent_raw = rent_match.group(1).replace(",", "")
    try:
        rent = Decimal(rent_raw)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid rent value: {rent_raw}") from exc

    expiry_raw = expiry_match.group(1).strip()
    lease_expiry = _parse_date(expiry_raw)

    return DeedExtract(
        property_address=address_match.group(1).strip().rstrip("."),
        monthly_rent_value=rent,
        landlord_name=landlord_match.group(1).strip().rstrip(".,"),
        lease_expiry_date=lease_expiry,
    )


def _parse_date(value: str) -> date:
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y", "%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b %d %Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {value}")


def parse_deed_or_lease(document_text: str) -> DeedExtract:
    """
    Accept raw text from a deed or rental agreement and return a
    strictly validated DeedExtract via OpenAI structured outputs,
    falling back to regex extraction when no API key is configured.
    """
    settings = get_settings()
    text = document_text.strip()
    if len(text) < 20:
        raise ValueError("document_text is too short to parse")

    if not settings.openai_api_key:
        return _fallback_regex_extract(text)

    client = OpenAI(api_key=settings.openai_api_key)

    try:
        completion = client.beta.chat.completions.parse(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            response_format=DeedExtract,
            temperature=0,
        )
        parsed = completion.choices[0].message.parsed
        if parsed is None:
            # Some SDK paths return refusal / raw content instead of parsed.
            raw = completion.choices[0].message.content or "{}"
            data = json.loads(raw)
            return DeedExtract.model_validate(data)
        return parsed
    except Exception:
        # Degrade gracefully so onboarding still works offline.
        return _fallback_regex_extract(text)
