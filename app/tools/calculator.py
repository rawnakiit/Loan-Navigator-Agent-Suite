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
    Calculates detailed Amortization Schedules, Total Repayments, and Interest Saved.
    """
    logger.info(f"Simulating prepayment: {prepayment_amount} on principal {principal}")

    monthly_rate = (annual_interest_rate / 100) / 12
    original_emi = calculate_emi(principal, annual_interest_rate, remaining_tenure_months)

    # 1. Generate original amortization schedule for accurate reference
    original_schedule = []
    balance = principal
    original_total_repayment = 0.0
    for month in range(1, remaining_tenure_months + 1):
        interest = round(balance * monthly_rate, 2)
        if month == remaining_tenure_months or (balance + interest) < original_emi:
            actual_payment = round(balance + interest, 2)
            principal_paid = round(balance, 2)
            balance = 0.0
        else:
            actual_payment = original_emi
            principal_paid = round(original_emi - interest, 2)
            balance = round(balance - principal_paid, 2)
        original_schedule.append({
            "month": month,
            "payment": actual_payment,
            "principal_paid": principal_paid,
            "interest_paid": interest,
            "remaining_balance": balance
        })
        original_total_repayment += actual_payment

    original_total_repayment = round(original_total_repayment, 2)

    if prepayment_amount >= principal:
        return {
            "status": "Loan Closed",
            "message": "The prepayment amount covers the entire outstanding balance. Your loan will be closed.",
            "original_total_repayment": original_total_repayment,
            "prepayment_amount": prepayment_amount
        }

    # New Principal after prepayment
    new_principal = principal - prepayment_amount

    # Option A: Reduce EMI (Keep tenure same)
    new_emi = calculate_emi(new_principal, annual_interest_rate, remaining_tenure_months)
    option_a_schedule = []
    balance = new_principal
    option_a_total_repayment = prepayment_amount # Prepayment is paid at the start
    for month in range(1, remaining_tenure_months + 1):
        if balance <= 0:
            break
        interest = round(balance * monthly_rate, 2)
        if month == remaining_tenure_months or (balance + interest) < new_emi:
            actual_payment = round(balance + interest, 2)
            principal_paid = round(balance, 2)
            balance = 0.0
        else:
            actual_payment = new_emi
            principal_paid = round(new_emi - interest, 2)
            balance = round(balance - principal_paid, 2)
        option_a_schedule.append({
            "month": month,
            "payment": actual_payment,
            "principal_paid": principal_paid,
            "interest_paid": interest,
            "remaining_balance": balance
        })
        option_a_total_repayment += actual_payment

    option_a_total_repayment = round(option_a_total_repayment, 2)
    option_a_interest_saved = round(original_total_repayment - option_a_total_repayment, 2)

    # Option B: Reduce Tenure (Keep EMI same)
    option_b_schedule = []
    balance = new_principal
    option_b_total_repayment = prepayment_amount
    month = 1
    while balance > 0 and month <= remaining_tenure_months:
        interest = round(balance * monthly_rate, 2)
        if (balance + interest) < original_emi:
            actual_payment = round(balance + interest, 2)
            principal_paid = round(balance, 2)
            balance = 0.0
        else:
            actual_payment = original_emi
            principal_paid = round(original_emi - interest, 2)
            balance = round(balance - principal_paid, 2)
        option_b_schedule.append({
            "month": month,
            "payment": actual_payment,
            "principal_paid": principal_paid,
            "interest_paid": interest,
            "remaining_balance": balance
        })
        option_b_total_repayment += actual_payment
        month += 1

    option_b_total_repayment = round(option_b_total_repayment, 2)
    option_b_interest_saved = round(original_total_repayment - option_b_total_repayment, 2)
    option_b_new_tenure_months = len(option_b_schedule)
    option_b_months_saved = remaining_tenure_months - option_b_new_tenure_months

    return {
        "status": "Success",
        "original_principal": principal,
        "prepayment_amount": prepayment_amount,
        "new_principal": new_principal,
        "original_emi": original_emi,
        "original_total_repayment": original_total_repayment,
        
        # Option A
        "option_a_new_emi": round(new_emi, 2),
        "option_a_total_repayment": option_a_total_repayment,
        "option_a_interest_saved": option_a_interest_saved,
        "option_a_schedule": option_a_schedule,
        
        # Option B
        "option_b_new_tenure_months": option_b_new_tenure_months,
        "option_b_months_saved": option_b_months_saved,
        "option_b_total_repayment": option_b_total_repayment,
        "option_b_interest_saved": option_b_interest_saved,
        "option_b_schedule": option_b_schedule
    }
