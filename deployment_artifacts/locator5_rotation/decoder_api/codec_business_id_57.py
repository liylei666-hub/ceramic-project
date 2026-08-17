#!/usr/bin/env python3
"""Pack a 5+6+6 digit ceramic business identifier into 57 payload bits."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime


PAYLOAD_BITS = 57
BCH_DATA_BITS = 61
CRC_BITS = BCH_DATA_BITS - PAYLOAD_BITS
MAX_IDENTIFIER_VALUE = 10**17 - 1
CRC4_POLYNOMIAL = 0b10011  # x^4 + x + 1


@dataclass(frozen=True)
class BusinessIdentifier:
    enterprise: str
    date: str
    serial: str

    @property
    def decimal(self) -> str:
        return f"{self.enterprise}{self.date}{self.serial}"

    def to_dict(self) -> dict[str, str]:
        return asdict(self) | {"decimal": self.decimal}


def _fixed_decimal(value: str | int, width: int, field: str) -> str:
    text = str(value)
    if not text.isdecimal():
        raise ValueError(f"{field} must contain decimal digits only")
    if len(text) > width:
        raise ValueError(f"{field} exceeds {width} decimal digits")
    return text.zfill(width)


def _validate_date(date_code: str) -> None:
    try:
        datetime.strptime(f"20{date_code}", "%Y%m%d")
    except ValueError as exc:
        raise ValueError(f"invalid YYMMDD date: {date_code}") from exc


def pack_identifier(
    enterprise: str | int,
    date_code: str | int,
    serial: str | int,
    *,
    validate_date: bool = True,
) -> str:
    """Return the canonical 57-bit representation of a 5+6+6 digit ID."""

    enterprise_text = _fixed_decimal(enterprise, 5, "enterprise")
    date_text = _fixed_decimal(date_code, 6, "date")
    serial_text = _fixed_decimal(serial, 6, "serial")
    if validate_date:
        _validate_date(date_text)

    value = int(f"{enterprise_text}{date_text}{serial_text}")
    if value > MAX_IDENTIFIER_VALUE:
        raise ValueError("identifier exceeds the 17-decimal-digit domain")
    return f"{value:0{PAYLOAD_BITS}b}"


def unpack_identifier(bits: str, *, validate_date: bool = True) -> BusinessIdentifier:
    """Decode 57 bits and restore the leading-zero-padded business fields."""

    if len(bits) != PAYLOAD_BITS or any(bit not in "01" for bit in bits):
        raise ValueError(f"payload must be exactly {PAYLOAD_BITS} binary digits")
    value = int(bits, 2)
    if value > MAX_IDENTIFIER_VALUE:
        raise ValueError("57-bit value is outside the 17-decimal-digit domain")

    decimal = f"{value:017d}"
    identifier = BusinessIdentifier(decimal[:5], decimal[5:11], decimal[11:])
    if validate_date:
        _validate_date(identifier.date)
    return identifier


def crc4(bits: str) -> str:
    """Calculate a four-bit CRC using polynomial x^4 + x + 1."""

    if not bits or any(bit not in "01" for bit in bits):
        raise ValueError("CRC input must be a non-empty binary string")
    remainder = int(bits, 2) << CRC_BITS
    for shift in range(len(bits) - 1, -1, -1):
        if remainder & (1 << (shift + CRC_BITS)):
            remainder ^= CRC4_POLYNOMIAL << shift
    return f"{remainder:0{CRC_BITS}b}"


def build_bch5_data(payload_bits: str) -> str:
    """Fill BCH-5's 61 data positions with 57 payload bits and CRC-4."""

    if len(payload_bits) != PAYLOAD_BITS or any(bit not in "01" for bit in payload_bits):
        raise ValueError(f"payload must be exactly {PAYLOAD_BITS} binary digits")
    return payload_bits + crc4(payload_bits)


def parse_bch5_data(data_bits: str, *, validate_date: bool = True) -> BusinessIdentifier:
    """Validate CRC-4 and decode a corrected 61-bit BCH-5 data section."""

    if len(data_bits) != BCH_DATA_BITS or any(bit not in "01" for bit in data_bits):
        raise ValueError(f"BCH-5 data must be exactly {BCH_DATA_BITS} binary digits")
    payload, expected_crc = data_bits[:PAYLOAD_BITS], data_bits[PAYLOAD_BITS:]
    if crc4(payload) != expected_crc:
        raise ValueError("CRC-4 check failed")
    return unpack_identifier(payload, validate_date=validate_date)


def encode_fields(
    enterprise: str | int,
    date_code: str | int,
    serial: str | int,
) -> tuple[str, str]:
    """Return (57-bit business payload, 61-bit BCH-5 input data)."""

    payload = pack_identifier(enterprise, date_code, serial)
    return payload, build_bch5_data(payload)

