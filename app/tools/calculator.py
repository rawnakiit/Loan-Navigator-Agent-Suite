import logging
import math

logger = logging.getLogger(__name__)


def calculate_emi(principal: float, annual_interest_rate: float, tenure_months: int) -> float:
    """Calculates standard EMI."""
    if annual_interest_rate == 0:
        return principal / tenure_months

    monthly_rate = (annual_interest_rate / 100) / 12
    emi = principal * monthly_rate * ((1 + monthly_rate) ** tenure_months) / (((1 + monthly_rate) ** tenure_months) - 1)
    return round(emi, 2)


def calculate_prepayment_impact(principal: float, annual_interest_rate: float,
                                remaining_tenure_months: int, prepayment_amount: float) -> dict:
    """
    Simulates the two options a borrower has when making a prepayment:
    Option A: Keep tenure the same, reduce monthly EMI.
    Option B: Keep EMI the same, reduce total tenure.
    """
    logger.info(f"Simulating prepayment: {prepayment_amount} on principal {principal}")

    if prepayment_amount >= principal:
        return {
            "status": "Loan Closed",
            "message": "The prepayment amount covers the entire outstanding balance. Your loan will be closed."
        }

    # New Principal after prepayment
    new_principal = principal - prepayment_amount

    # Calculate original EMI for reference
    original_emi = calculate_emi(principal, annual_interest_rate, remaining_tenure_months)

    # Option A: Reduce EMI (Keep tenure same)
    new_emi = calculate_emi(new_principal, annual_interest_rate, remaining_tenure_months)

    # Option B: Reduce Tenure (Keep EMI same)
    monthly_rate = (annual_interest_rate / 100) / 12
    if monthly_rate > 0 and original_emi > (new_principal * monthly_rate):
        # Formula: n = -log(1 - (P * r) / EMI) / log(1 + r)
        new_tenure_raw = -math.log(1 - (new_principal * monthly_rate / original_emi)) / math.log(1 + monthly_rate)
        new_tenure_months = math.ceil(new_tenure_raw)
        tenure_reduction = remaining_tenure_months - new_tenure_months
    else:
        new_tenure_months = remaining_tenure_months
        tenure_reduction = 0

    return {
        "status": "Success",
        "original_principal": principal,
        "prepayment_amount": prepayment_amount,
        "new_principal": new_principal,
        "original_emi": original_emi,
        "option_a_new_emi": round(new_emi, 2),
        "option_b_new_tenure_months": new_tenure_months,
        "option_b_months_saved": tenure_reduction
    }
