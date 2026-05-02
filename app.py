from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

def calculate_tax_new_regime_25_26(income):
    """
    Calculates tax based on New Regime slabs (FY 2025-26).
    Slabs:
    0 - 4L        : Nil
    4L - 8L       : 5%
    8L - 12L      : 10%
    12L - 16L     : 15%
    16L - 20L     : 20%
    20L - 24L     : 25%
    > 24L         : 30%
    """
    tax = 0
    remaining = income

    # Slab Logic
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
    
    # Sec 87A Rebate: If taxable income <= 12L, Tax is Nil (up to 60k rebate)
    if income <= 1200000:
        tax = 0

    return tax

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.json
    
    # 1. Parse Inputs (Monthly)
    try:
        basic = float(data.get('basic', 0))
        hra = float(data.get('hra', 0))
        pf_employer = float(data.get('pf_employer', 0))
        special = float(data.get('special', 0))
        # Summing other small allowances for brevity in backend, passed individually from frontend
        other_allowances = (
            float(data.get('conveyance', 0)) +
            float(data.get('medical', 0)) +
            float(data.get('telephone', 0)) +
            float(data.get('lta', 0)) +
            float(data.get('meal', 0)) +
            float(data.get('education', 0)) +
            float(data.get('car', 0)) +
            float(data.get('other', 0))
        )
        gratuity = float(data.get('gratuity', 0))
        variable_annual = float(data.get('variable', 0))
        rsu_annual_usd = float(data.get('rsu', 0))
        usd_inr_rate = float(data.get('usd_inr_rate', 90))
    except ValueError:
        return jsonify({"error": "Invalid input format"}), 400

    rsu_annual_inr = rsu_annual_usd * usd_inr_rate

    # 2. Annualize Fixed Components
    monthly_fixed_components = basic + hra + pf_employer + special + other_allowances + gratuity
    annual_fixed_ctc = monthly_fixed_components * 12
    total_ctc = annual_fixed_ctc + variable_annual + rsu_annual_inr

    # 3. Tax Calculation Setup
    annual_pf_employer = pf_employer * 12
    annual_gratuity = gratuity * 12
    
    # Gross Salary for Tax (Fixed) = CTC - PF Employer - Gratuity
    # (Assuming PF Employer & Gratuity are exempt/not part of taxable salary usually)
    gross_salary_fixed = annual_fixed_ctc - annual_pf_employer - annual_gratuity
    
    # Deductions
    standard_deduction = 75000
    profession_tax_annual = 2500
    
    taxable_income_fixed = max(0, gross_salary_fixed - standard_deduction) 

    # 4. Calculate Tax on Fixed
    tax_fixed_base = calculate_tax_new_regime_25_26(taxable_income_fixed)

    # 5. Variable Component Logic (Marginal Tax)
    # We calculate tax on (Fixed + Variable) and subtract tax on (Fixed)
    total_taxable_income = taxable_income_fixed + variable_annual + rsu_annual_inr

    
    # Surcharge Calculation (Marginal)
    # Note: Surcharge is typically on Total Income. We base the rate on the total expected income.
    # Now decide surcharge rate:
    if total_taxable_income > 10000000:
        surcharge_rate = 0.15
    elif total_taxable_income > 5000000:
        surcharge_rate = 0.10
    else:
        surcharge_rate = 0

    # Surcharge on Fixed Income
    surcharge_fixed = tax_fixed_base * surcharge_rate
    final_tax_fixed = (tax_fixed_base + surcharge_fixed) * 1.04 # Adding 4% Cess

    # 6. Take Home (Fixed)
    # Deductions: PF (Both), PT, Tax
    pf_employee = pf_employer # Assuming 1:1
    annual_pf_employee = pf_employee * 12
    
    annual_deductions = annual_pf_employer + annual_pf_employee + annual_gratuity + profession_tax_annual + final_tax_fixed
    annual_take_home_fixed = annual_fixed_ctc - annual_deductions
    monthly_take_home_fixed = annual_take_home_fixed / 12

    # Tax on total taxable income
    tax_total_base = calculate_tax_new_regime_25_26(total_taxable_income)
    
    # Tax on variable
    surcharge_total = tax_total_base * surcharge_rate
    
    # Total Tax
    final_tax_total = (tax_total_base + surcharge_total) * 1.04
    
    # Tax on variable+rsu income
    tax_on_variable_plus_rsu = final_tax_total - final_tax_fixed
    total_variable_plus_rsu_in_hand = variable_annual + rsu_annual_inr - tax_on_variable_plus_rsu

    # variable/rsu separation in hand
    if (variable_annual + rsu_annual_inr) > 0:
        variable_in_hand = total_variable_plus_rsu_in_hand * variable_annual / (variable_annual + rsu_annual_inr)
        rsu_in_hand = total_variable_plus_rsu_in_hand - variable_in_hand
    else:
        variable_in_hand = 0
        rsu_in_hand = 0

    
    total_annual_take_home = annual_take_home_fixed + variable_in_hand + rsu_in_hand

    # 7. Format Response
    return jsonify({
        "fixed_ctc_monthly": monthly_fixed_components,
        "fixed_ctc_annual": annual_fixed_ctc,
        "total_ctc": total_ctc,
        "deductions": {
            "pf_employer": annual_pf_employer,
            "pf_employee": annual_pf_employee,
            "pt": profession_tax_annual,
            "tax": final_tax_fixed
        },
        "results": {
            "monthly_take_home_fixed": monthly_take_home_fixed,
            "annual_take_home_fixed": annual_take_home_fixed,
            "variable_in_hand": variable_in_hand,
            "rsu_in_hand": rsu_in_hand,
            "total_annual_take_home": total_annual_take_home
        }
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
