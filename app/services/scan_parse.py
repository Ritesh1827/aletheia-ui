"""Scan payload parsing. Pure, deterministic, tested.

Rules:
- Plain supported serials (AL-XXX-0000 shape) pass through directly.
- Aletheia product URLs / structured payloads yield an explicit serial.
- Anything else is AMBIGUOUS: the raw value is shown and the user decides.
  The parser never guesses a serial from an arbitrary URL or payload.
"""

from __future__ import annotations

import re
from typing import Literal
from urllib.parse import parse_qs, urlparse

from pydantic import BaseModel, Field

ParseStatus = Literal["serial", "ambiguous"]

_SERIAL_RE = re.compile(r"^AL-[A-Z0-9]{2,8}-\d{3,6}$", re.IGNORECASE)
_ALETHEIA_HOSTS = {"verify.aletheia.example", "aletheia.example"}


class ScanParse(BaseModel):
    status: ParseStatus
    serial: str = ""
    raw: str = ""
    explanation: str = ""
    candidates: list[str] = Field(default_factory=list)


def _looks_like_serial(value: str) -> bool:
    return _SERIAL_RE.match(value.strip()) is not None


def _serial_candidates(text: str) -> list[str]:
    found = re.findall(r"AL-[A-Z0-9]{2,8}-\d{3,6}", text, flags=re.IGNORECASE)
    seen: list[str] = []
    for cand in found:
        upper = cand.upper()
        if upper not in seen:
            seen.append(upper)
    return seen


def parse_scan_payload(raw: str) -> ScanParse:
    value = raw.strip()
    if not value:
        return ScanParse(status="ambiguous", raw=raw,
                         explanation="Empty scan — nothing to verify. Try again or type the serial.")
    if _looks_like_serial(value):
        serial = value.upper()
        return ScanParse(status="serial", serial=serial, raw=value,
                         explanation=f"Plain serial recognized: {serial}.")
    if value.upper().startswith("AL:"):
        inner = value[3:].strip()
        if _looks_like_serial(inner):
            serial = inner.upper()
            return ScanParse(status="serial", serial=serial, raw=value,
                             explanation=f"Structured Aletheia payload — serial {serial}.")
        return ScanParse(status="ambiguous", raw=value,
                         explanation="Aletheia-prefixed payload without a recognizable serial. "
                                     "Confirm the value before verifying.")
    if "://" in value or value.lower().startswith("aletheia:"):
        try:
            parsed = urlparse(value if "://" in value else value.replace("aletheia:", "al://x/", 1))
            host = (parsed.hostname or "").lower()
            trusted = host in _ALETHEIA_HOSTS or host.endswith(".aletheia.example")
            qs = parse_qs(parsed.query)
            cands = _serial_candidates(parsed.path + " " + parsed.query)
            if trusted:
                for key in ("serial", "s", "id", "epc"):
                    vals = qs.get(key, [])
                    if vals and _looks_like_serial(vals[0]):
                        serial = vals[0].upper()
                        return ScanParse(status="serial", serial=serial, raw=value,
                                         explanation=f"Serial {serial} extracted from the product URL.")
                if cands:
                    return ScanParse(status="serial", serial=cands[0], raw=value,
                                     explanation=f"Serial {cands[0]} extracted from the Aletheia URL path.")
            if cands:
                return ScanParse(status="ambiguous", raw=value, candidates=cands,
                                 explanation="A serial-like value was found inside an unrecognized URL. "
                                             "Confirm it before verifying — it was not auto-selected.")
            return ScanParse(status="ambiguous", raw=value,
                             explanation="URL payload without a recognizable serial. "
                                         "Confirm the value before verifying; nothing was auto-selected.")
        except ValueError:
            return ScanParse(status="ambiguous", raw=value,
                             explanation="URL could not be parsed safely. Confirm the value before verifying.")
    cands = _serial_candidates(value)
    if len(cands) == 1 and len(value) <= 64:
        return ScanParse(status="ambiguous", raw=value, candidates=cands,
                         explanation=f"Found serial-like value {cands[0]} inside the payload. "
                                     "Confirm it before verifying — it was not auto-selected.")
    return ScanParse(status="ambiguous", raw=value, candidates=cands,
                     explanation="Unrecognized payload format. Edit or confirm the exact value to verify — "
                                 "the scanner never guesses a serial.")
