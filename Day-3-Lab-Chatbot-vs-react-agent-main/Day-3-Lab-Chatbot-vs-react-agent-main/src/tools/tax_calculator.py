from typing import Union

# Bảng thuế VAT theo mã quốc gia (ISO 3166-1 alpha-2)
VAT_RATES = {
    "VN": 0.10,   # Việt Nam - 10%
    "US": 0.00,   # Mỹ - không có VAT liên bang
    "DE": 0.19,   # Đức - 19%
    "FR": 0.20,   # Pháp - 20%
    "GB": 0.20,   # Anh - 20%
    "JP": 0.10,   # Nhật - 10%
    "SG": 0.09,   # Singapore - 9%
    "AU": 0.10,   # Úc - 10%
    "TH": 0.07,   # Thái Lan - 7%
    "KR": 0.10,   # Hàn Quốc - 10%
    "CN": 0.13,   # Trung Quốc - 13%
    "IN": 0.18,   # Ấn Độ - 18% (GST)
}


def calc_tax(amount: Union[float, str], country_code: str) -> str:
    """
    Tính thuế VAT dựa trên số tiền và mã quốc gia.
    country_code phải là mã quốc gia 2 chữ cái (ISO 3166-1 alpha-2).
    Ví dụ: calc_tax(1000, VN) -> tính thuế 10% cho Việt Nam
    """
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return f"Error: Invalid amount '{amount}'. Must be a number."

    country_code = str(country_code).strip().upper()

    if country_code not in VAT_RATES:
        supported = ", ".join(VAT_RATES.keys())
        return (
            f"Error: Unknown country code '{country_code}'. "
            f"Supported codes: {supported}"
        )

    rate = VAT_RATES[country_code]
    tax_amount = amount * rate
    total = amount + tax_amount

    return (
        f"Tax calculation for {country_code}: "
        f"Amount={amount:.2f}, VAT rate={rate*100:.0f}%, "
        f"Tax={tax_amount:.2f}, Total={total:.2f}"
    )


TOOL_SPEC = {
    "name": "calc_tax",
    "description": (
        "Calculate VAT/tax for a given amount and country code (ISO 2-letter code). "
        "Supported countries: VN, US, DE, FR, GB, JP, SG, AU, TH, KR, CN, IN. "
        "Input format: calc_tax(amount, country_code). "
        "Example: calc_tax(500, VN)"
    ),
    "func": calc_tax,
}
