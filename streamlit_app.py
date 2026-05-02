import streamlit as st

st.set_page_config(page_title="Salary Calculator Pro", layout="wide", initial_sidebar_state="expanded")

def calculate_tax_new_regime_25_26(income):
    tax = 0
    remaining = income

    if remaining > 2400000:
        tax += (remaining - 2400000) * 0.30
        remaining = 2400000
    if remaining > 2000000:
        tax += (remaining - 2000000) * 0.25
        remaining = 2000000
    if remaining > 1600000:
        tax += (remaining - 1600000) * 0.20
        remaining = 1600000
    if remaining > 1200000:
        tax += (remaining - 1200000) * 0.15
        remaining = 1200000
    if remaining > 800000:
        tax += (remaining - 800000) * 0.10
        remaining = 800000
    if remaining > 400000:
        tax += (remaining - 400000) * 0.05
        remaining = 400000
    
    if income <= 1200000:
        tax = 0

    return tax

st.title("✨ Salary Calculator Pro")
st.markdown("Enter your monthly details as per your offer letter. Tax is calculated based on FY 2025-26 (New Regime).")

col1, col2 = st.columns([2, 1])

with col1:
    st.header("Earnings (Monthly)")
    c1, c2 = st.columns(2)
    with c1:
        basic = st.number_input("Basic Salary (₹)", min_value=0.0, value=0.0, step=1000.0)
        special = st.number_input("Special Allowance (₹)", min_value=0.0, value=0.0, step=1000.0)
    with c2:
        hra = st.number_input("HRA (₹)", min_value=0.0, value=0.0, step=1000.0)
        pf_employer = st.number_input("PF (Employer) (₹)", min_value=0.0, value=0.0, step=1000.0)

    st.header("Allowances & Others (Monthly)")
    c3, c4, c5 = st.columns(3)
    with c3:
        conveyance = st.number_input("Conveyance (₹)", min_value=0.0, value=0.0, step=1000.0)
        lta = st.number_input("LTA (₹)", min_value=0.0, value=0.0, step=1000.0)
        car = st.number_input("Car / Petrol (₹)", min_value=0.0, value=0.0, step=1000.0)
    with c4:
        medical = st.number_input("Medical (₹)", min_value=0.0, value=0.0, step=1000.0)
        meal = st.number_input("Meal Vouchers (₹)", min_value=0.0, value=0.0, step=1000.0)
        other = st.number_input("Other (₹)", min_value=0.0, value=0.0, step=1000.0)
    with c5:
        telephone = st.number_input("Telephone (₹)", min_value=0.0, value=0.0, step=1000.0)
        education = st.number_input("Education (₹)", min_value=0.0, value=0.0, step=1000.0)
        gratuity = st.number_input("Gratuity (in CTC) (₹)", min_value=0.0, value=0.0, step=1000.0)

    st.header("Variable & Equity (Annual)")
    c6, c7, c8 = st.columns(3)
    with c6:
        variable_annual = st.number_input("Annual Performance Bonus (₹)", min_value=0.0, value=0.0, step=10000.0)
    with c7:
        rsu_annual_usd = st.number_input("Annual RSU Value ($)", min_value=0.0, value=0.0, step=1000.0)
    with c8:
        usd_inr_rate = st.number_input("USD/INR Rate (₹)", min_value=0.0, value=83.0, step=1.0)

# Backend calculations
other_allowances = conveyance + medical + telephone + lta + meal + education + car + other
rsu_annual_inr = rsu_annual_usd * usd_inr_rate

monthly_fixed_components = basic + hra + pf_employer + special + other_allowances + gratuity
annual_fixed_ctc = monthly_fixed_components * 12
total_ctc = annual_fixed_ctc + variable_annual + rsu_annual_inr

annual_pf_employer = pf_employer * 12
annual_gratuity = gratuity * 12

gross_salary_fixed = annual_fixed_ctc - annual_pf_employer - annual_gratuity
standard_deduction = 75000
profession_tax_annual = 2500

taxable_income_fixed = max(0, gross_salary_fixed - standard_deduction)
tax_fixed_base = calculate_tax_new_regime_25_26(taxable_income_fixed)

total_taxable_income = taxable_income_fixed + variable_annual + rsu_annual_inr

if total_taxable_income > 10000000:
    surcharge_rate = 0.15
elif total_taxable_income > 5000000:
    surcharge_rate = 0.10
else:
    surcharge_rate = 0

surcharge_fixed = tax_fixed_base * surcharge_rate
final_tax_fixed = (tax_fixed_base + surcharge_fixed) * 1.04

pf_employee = pf_employer
annual_pf_employee = pf_employee * 12
annual_deductions = annual_pf_employer + annual_pf_employee + annual_gratuity + profession_tax_annual + final_tax_fixed
annual_take_home_fixed = annual_fixed_ctc - annual_deductions
monthly_take_home_fixed = annual_take_home_fixed / 12

tax_total_base = calculate_tax_new_regime_25_26(total_taxable_income)
surcharge_total = tax_total_base * surcharge_rate
final_tax_total = (tax_total_base + surcharge_total) * 1.04

tax_on_variable_plus_rsu = final_tax_total - final_tax_fixed
total_variable_plus_rsu_in_hand = variable_annual + rsu_annual_inr - tax_on_variable_plus_rsu

if (variable_annual + rsu_annual_inr) > 0:
    variable_in_hand = total_variable_plus_rsu_in_hand * variable_annual / (variable_annual + rsu_annual_inr)
    rsu_in_hand = total_variable_plus_rsu_in_hand - variable_in_hand
else:
    variable_in_hand = 0
    rsu_in_hand = 0

total_annual_take_home = annual_take_home_fixed + variable_in_hand + rsu_in_hand

with col2:
    st.header("Results Summary")
    st.success(f"**Monthly In-Hand (Fixed):** ₹ {monthly_take_home_fixed:,.0f}")
    
    st.subheader("Breakdown Summary")
    st.metric("Fixed CTC (Annual)", f"₹ {annual_fixed_ctc:,.0f}")
    st.metric("Total CTC (Inc. Var)", f"₹ {total_ctc:,.0f}")
    
    st.markdown("---")
    st.metric("Annual PF (Both)", f"₹ {(annual_pf_employer + annual_pf_employee):,.0f}")
    st.metric("Income Tax (Fixed)", f"₹ {final_tax_fixed:,.0f}", delta_color="inverse")
    
    st.markdown("---")
    st.metric("Annual In-Hand (Fixed)", f"₹ {annual_take_home_fixed:,.0f}")
    st.metric("Variable In-Hand (Net)", f"₹ {variable_in_hand:,.0f}")
    st.metric("RSU in hand (Net)", f"₹ {rsu_in_hand:,.0f}")
    
    st.markdown("---")
    st.info(f"**Total Annual Net Pay: ₹ {total_annual_take_home:,.0f}**", icon="💰")
    
    st.caption("Tax Regime: FY 2025-26 (New)")
