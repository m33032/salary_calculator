import streamlit as st

st.set_page_config(page_title="Salary Calculator Pro", layout="wide", initial_sidebar_state="collapsed", page_icon="💼")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: #f8fafc !important; }
[data-testid="stAppViewContainer"] { background-color: #0f172a; }
[data-testid="stHeader"] { background-color: transparent; }
h1, h2, h3, h4, h5, h6 { font-family: 'Outfit', sans-serif !important; letter-spacing: -0.5px; color: #f8fafc !important; }
.stNumberInput input {
    border-radius: 8px !important; background-color: #1e293b !important;
    border: 1px solid rgba(255,255,255,0.08) !important; color: #f8fafc !important;
    transition: all 0.2s ease;
}
.stNumberInput input:focus { border-color: #8b5cf6 !important; box-shadow: 0 0 0 2px rgba(139,92,246,0.25) !important; }
.stNumberInput label, [data-testid="stWidgetLabel"] p { color: #94a3b8 !important; font-size: 0.82rem !important; font-weight: 500 !important; }
[data-testid="stMetric"] {
    background: #1e293b; border: 1px solid rgba(255,255,255,0.06);
    padding: 14px 18px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
[data-testid="stMetric"]:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(0,0,0,0.3); }
[data-testid="stMetricLabel"] p { font-weight: 600 !important; color: #64748b !important; font-size: 0.78rem !important; text-transform: uppercase; letter-spacing: 0.6px; }
[data-testid="stMetricValue"] div { font-family: 'Outfit', sans-serif !important; font-weight: 700 !important; font-size: 1.5rem !important; color: #f8fafc !important; }
[data-testid="stMetricDelta"] div { font-size: 0.78rem !important; }
.stButton > button { border-radius: 8px !important; font-weight: 600 !important; transition: all 0.2s ease !important; color: #f8fafc !important; }
.streamlit-expanderHeader p { font-weight: 600 !important; color: #94a3b8 !important; }
.stProgress > div > div { border-radius: 6px !important; }
[data-testid="stSidebar"] { background-color: #0b1120 !important; }
[data-testid="stToolbar"] { display: none !important; }
hr { border-color: rgba(255,255,255,0.05) !important; margin: 16px 0 !important; }
</style>
""", unsafe_allow_html=True)


# ── Tax Engine ─────────────────────────────────────────────────────────────────
# FY 2025-26 & FY 2026-27 slabs are IDENTICAL (Budget 2026 kept slabs unchanged)
SLABS = [
    (400_000,  0.00),
    (400_000,  0.05),  # 4L – 8L
    (400_000,  0.10),  # 8L – 12L
    (400_000,  0.15),  # 12L – 16L
    (400_000,  0.20),  # 16L – 20L
    (400_000,  0.25),  # 20L – 24L
    (float("inf"), 0.30),
]

# Surcharge thresholds (New Regime — capped at 25%; Old regime goes to 37%)
SURCHARGE_BRACKETS = [
    (5_00_00_000, 0.25),  # > 5 Cr
    (2_00_00_000, 0.25),  # 2 Cr – 5 Cr
    (1_00_00_000, 0.15),  # 1 Cr – 2 Cr
    (50_00_000,   0.10),  # 50L – 1 Cr
    (0,           0.00),
]

def get_surcharge_rate(taxable: float) -> float:
    for threshold, rate in SURCHARGE_BRACKETS:
        if taxable > threshold:
            return rate
    return 0.0

def compute_slab_rows(income: float) -> list:
    rows, remaining, lower = [], income, 0
    for width, rate in SLABS:
        if remaining <= 0:
            break
        amt = min(remaining, width)
        rows.append({"from": lower, "to": lower + amt, "rate": rate, "tax": amt * rate})
        lower += amt
        remaining -= amt
    return rows

def base_tax(income: float) -> float:
    return sum(r["tax"] for r in compute_slab_rows(income))


def marginal_relief_87a(income: float, raw_tax: float) -> float:
    """Rebate u/s 87A: zero tax up to ₹12L; marginal relief between 12L–~12.75L."""
    if income <= 1_200_000:
        return raw_tax
    if income <= 1_275_000:
        excess_income = income - 1_200_000
        tax_on_12L = 0.0  # tax at exactly 12L = 0 after rebate
        excess_tax = raw_tax - tax_on_12L
        if excess_tax > excess_income:
            return raw_tax - (excess_tax - excess_income)
    return raw_tax


def apply_marginal_relief_surcharge(income: float, tax_no_sc: float, sc_rate: float) -> tuple:
    """
    Marginal relief on surcharge: ensure incremental tax+surcharge from crossing
    a surcharge threshold does not exceed incremental income over that threshold.
    Returns (surcharge_after_relief, relief_amount).
    """
    if sc_rate == 0:
        return 0.0, 0.0

    # Find the threshold just crossed
    thresholds = [50_00_000, 1_00_00_000, 2_00_00_000, 5_00_00_000]
    threshold_crossed = 0
    for t in sorted(thresholds):
        if income > t:
            threshold_crossed = t

    if threshold_crossed == 0:
        return 0.0, 0.0

    # Tax at the threshold (with previous surcharge rate, no marginal relief there)
    tax_at_threshold = base_tax(float(threshold_crossed))
    prev_sc_rate = get_surcharge_rate(float(threshold_crossed - 1))
    tax_at_threshold_total = tax_at_threshold * (1 + prev_sc_rate)

    # Tax at current income with surcharge (before relief)
    surcharge_raw = tax_no_sc * sc_rate
    tax_current_total = tax_no_sc + surcharge_raw

    # Incremental income and incremental tax
    incremental_income = income - threshold_crossed
    incremental_tax = tax_current_total - tax_at_threshold_total

    if incremental_tax > incremental_income:
        relief = incremental_tax - incremental_income
        surcharge_after_relief = max(0.0, surcharge_raw - relief)
        return surcharge_after_relief, relief
    return surcharge_raw, 0.0


def full_tax(taxable: float) -> dict:
    """
    Returns full breakdown: base, after_87a, surcharge, cess, total, relief details.
    """
    bt = base_tax(taxable)
    bt_after_rebate = marginal_relief_87a(taxable, bt)
    rebate_applied = bt - bt_after_rebate

    sc_rate = get_surcharge_rate(taxable)
    sc, sc_relief = apply_marginal_relief_surcharge(taxable, bt_after_rebate, sc_rate)
    cess = (bt_after_rebate + sc) * 0.04
    total = bt_after_rebate + sc + cess

    return {
        "base_tax": bt,
        "rebate_87a": rebate_applied,
        "tax_after_rebate": bt_after_rebate,
        "surcharge_rate": sc_rate,
        "surcharge": sc,
        "surcharge_relief": sc_relief,
        "cess": cess,
        "total": total,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────
FIELDS = ["basic","hra","special","pf_employer","conveyance","lta","car",
          "medical","meal","other","telephone","education","gratuity",
          "variable_annual","rsu_annual_usd","usd_inr_rate"]

def get_val(key, default=0.0):
    v = st.query_params.get(key, default)
    try: return float(v)
    except: return default

def fmt(n): return f"₹ {n:,.0f}"
def pct(n): return f"{n:.2f}%"


# ── Session State / Clear ─────────────────────────────────────────────────────
if "initialized" not in st.session_state:
    st.session_state["initialized"] = True

if st.session_state.get("_clear_requested"):
    for f in FIELDS:
        default = 83.0 if f == "usd_inr_rate" else 0.0
        st.session_state[f] = default
        st.query_params[f] = str(default)
    st.session_state["_clear_requested"] = False


# ── Header ────────────────────────────────────────────────────────────────────
hcol1, hc_clear, hc_cache = st.columns([4.4, 0.8, 0.8])
with hcol1:
    st.markdown("<h1 style='margin-bottom:2px'>💼 Salary Calculator Pro</h1>", unsafe_allow_html=True)
    st.markdown("""
    <p style='color:#64748b;font-size:0.93rem;margin-top:0'>
        New Tax Regime · FY 2025-26 / FY 2026-27 (identical slabs) · 
        Rebate u/s 87A · Marginal relief on tax &amp; surcharge · Cess 4%
    </p>""", unsafe_allow_html=True)
with hc_clear:
    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    if st.button("🗑️ Clear All", use_container_width=True, help="Reset all fields to zero"):
        st.session_state["_clear_requested"] = True
        st.rerun()
with hc_cache:
    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    if st.button("🔄 Clear Cache", use_container_width=True, help="Clear Streamlit cache"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()

st.markdown("---")

# ── Inputs ────────────────────────────────────────────────────────────────────
col1, col2 = st.columns([2.2, 1], gap="large")

with col1:
    st.markdown("#### 💰 Fixed Earnings &nbsp;<span style='color:#64748b;font-size:0.85rem;font-weight:400'>(Monthly)</span>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        basic      = st.number_input("Basic Salary (₹)",      min_value=0.0, value=get_val("basic"),      step=1000.0, key="basic",      format="%.0f")
    with c2:
        hra        = st.number_input("HRA (₹)",               min_value=0.0, value=get_val("hra"),        step=1000.0, key="hra",        format="%.0f")
    with c3:
        special    = st.number_input("Special Allowance (₹)", min_value=0.0, value=get_val("special"),    step=1000.0, key="special",    format="%.0f")

    c4, c5, c6 = st.columns(3)
    with c4:
        pf_employer = st.number_input("PF – Employer (₹)",   min_value=0.0, value=get_val("pf_employer"), step=500.0, key="pf_employer", format="%.0f")
    with c5:
        gratuity    = st.number_input("Gratuity in CTC (₹)", min_value=0.0, value=get_val("gratuity"),    step=500.0, key="gratuity",    format="%.0f")
    with c6:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.info("💡 PF Employee = PF Employer (assumed equal)")

    st.markdown("#### 🗒️ Allowances &nbsp;<span style='color:#64748b;font-size:0.85rem;font-weight:400'>(Monthly)</span>", unsafe_allow_html=True)
    ca, cb, cc, cd = st.columns(4)
    with ca:
        conveyance = st.number_input("Conveyance (₹)", min_value=0.0, value=get_val("conveyance"), step=500.0, key="conveyance", format="%.0f")
        medical    = st.number_input("Medical (₹)",    min_value=0.0, value=get_val("medical"),    step=500.0, key="medical",    format="%.0f")
    with cb:
        lta        = st.number_input("LTA (₹)",        min_value=0.0, value=get_val("lta"),        step=500.0, key="lta",        format="%.0f")
        meal       = st.number_input("Meal Vouchers (₹)", min_value=0.0, value=get_val("meal"),    step=500.0, key="meal",       format="%.0f")
    with cc:
        telephone  = st.number_input("Telephone (₹)", min_value=0.0, value=get_val("telephone"),   step=500.0, key="telephone",  format="%.0f")
        education  = st.number_input("Education (₹)", min_value=0.0, value=get_val("education"),   step=500.0, key="education",  format="%.0f")
    with cd:
        car        = st.number_input("Car/Petrol (₹)", min_value=0.0, value=get_val("car"),        step=500.0, key="car",        format="%.0f")
        other      = st.number_input("Other (₹)",      min_value=0.0, value=get_val("other"),      step=500.0, key="other",      format="%.0f")

    st.markdown("#### 📈 Variable & Equity &nbsp;<span style='color:#64748b;font-size:0.85rem;font-weight:400'>(Annual)</span>", unsafe_allow_html=True)
    cv1, cv2, cv3 = st.columns(3)
    with cv1:
        variable_annual = st.number_input("Performance Bonus (₹)", min_value=0.0, value=get_val("variable_annual"), step=10000.0, key="variable_annual", format="%.0f")
    with cv2:
        rsu_annual_usd  = st.number_input("Annual RSU Value ($)",  min_value=0.0, value=get_val("rsu_annual_usd"),  step=1000.0,  key="rsu_annual_usd",  format="%.0f")
    with cv3:
        usd_inr_rate    = st.number_input("USD/INR Rate (₹)",      min_value=1.0, value=get_val("usd_inr_rate", 83.0), step=0.5, key="usd_inr_rate",    format="%.2f")

# Persist query params
for key in FIELDS:
    st.query_params[key] = str(st.session_state[key])


# ── Calculations ──────────────────────────────────────────────────────────────
other_allowances  = conveyance + medical + telephone + lta + meal + education + car + other
rsu_annual_inr    = rsu_annual_usd * usd_inr_rate
pf_employee       = pf_employer

monthly_gross     = basic + hra + pf_employer + special + other_allowances + gratuity
annual_fixed_ctc  = monthly_gross * 12
total_ctc         = annual_fixed_ctc + variable_annual + rsu_annual_inr

annual_pf_employer = pf_employer * 12
annual_pf_employee = pf_employee * 12
annual_gratuity    = gratuity * 12
annual_pf_both     = annual_pf_employer + annual_pf_employee

gross_salary_fixed = annual_fixed_ctc - annual_pf_employer - annual_gratuity
standard_deduction = 75_000
profession_tax_ann = 2_400  # ₹200/month

taxable_fixed = max(0.0, gross_salary_fixed - standard_deduction)
total_taxable = taxable_fixed + variable_annual + rsu_annual_inr

t_fixed = full_tax(taxable_fixed)
t_total = full_tax(total_taxable)

# Apply the effective surcharge rate of the total income to the fixed tax.
# This ensures the fixed salary bears its proportional share of the higher surcharge bracket
# triggered by variable/RSU income, giving a more accurate "average" monthly in-hand.
if t_total["tax_after_rebate"] > 0:
    eff_sc_rate = t_total["surcharge"] / t_total["tax_after_rebate"]
else:
    eff_sc_rate = 0.0

tax_fixed_base = t_fixed["tax_after_rebate"]
tax_fixed_sc = tax_fixed_base * eff_sc_rate
tax_fixed_cess = (tax_fixed_base + tax_fixed_sc) * 0.04
tax_fixed = tax_fixed_base + tax_fixed_sc + tax_fixed_cess

# Update t_fixed dict so UI metrics reflect the adjusted values
t_fixed["surcharge_rate"] = eff_sc_rate
t_fixed["surcharge"] = tax_fixed_sc
t_fixed["cess"] = tax_fixed_cess
t_fixed["total"] = tax_fixed

tax_total = t_total["total"]

tax_on_var_rsu = max(0.0, tax_total - tax_fixed)
total_var_rsu_inhand = variable_annual + rsu_annual_inr - tax_on_var_rsu

if (variable_annual + rsu_annual_inr) > 0:
    share_var = variable_annual / (variable_annual + rsu_annual_inr)
    variable_inhand = total_var_rsu_inhand * share_var
    rsu_inhand      = total_var_rsu_inhand * (1 - share_var)
else:
    variable_inhand = rsu_inhand = 0.0

annual_deductions    = annual_pf_both + annual_gratuity + profession_tax_ann + tax_fixed
annual_inhand_fixed  = annual_fixed_ctc - annual_deductions
monthly_inhand_fixed = annual_inhand_fixed / 12
total_annual_inhand  = annual_inhand_fixed + variable_inhand + rsu_inhand

eff_tax_rate  = (tax_total / total_taxable * 100) if total_taxable > 0 else 0.0
take_home_pct = (total_annual_inhand / total_ctc * 100) if total_ctc > 0 else 0.0


# ── Results Panel ─────────────────────────────────────────────────────────────
with col2:
    st.markdown("#### 📊 Results")

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(16,185,129,0.12),rgba(5,150,105,0.25));
                padding:22px 20px;border-radius:16px;border:1px solid rgba(52,211,153,0.3);
                text-align:center;margin-bottom:14px;">
        <p style="color:#34d399;margin:0;font-size:11px;text-transform:uppercase;font-weight:700;letter-spacing:2px;">Monthly In-Hand (Fixed)</p>
        <div style="color:#10b981;margin:6px 0 0;font-family:'Outfit',sans-serif;font-size:42px;font-weight:800;">
            ₹{monthly_inhand_fixed:,.0f}
        </div>
        <p style="color:#6ee7b7;margin:4px 0 0;font-size:12px;">+ EPF ₹{(pf_employer+pf_employee):,.0f}/mo credited</p>
    </div>
    """, unsafe_allow_html=True)

    st.metric("Fixed Annual CTC",       fmt(annual_fixed_ctc))
    st.metric("Total CTC (w/ Var+RSU)", fmt(total_ctc), delta=f"+{fmt(variable_annual+rsu_annual_inr)} variable")
    st.markdown("---")

    st.metric("PF – Both (Annual)",     fmt(annual_pf_both))
    st.metric("Income Tax (Fixed Only)", fmt(tax_fixed),
              delta=f"Eff. {pct(t_fixed['tax_after_rebate']/taxable_fixed*100 if taxable_fixed else 0)}")
    if tax_on_var_rsu > 0:
        st.metric("Tax on Var + RSU",   fmt(tax_on_var_rsu))
    st.markdown("---")

    st.metric("Annual In-Hand (Fixed)", fmt(annual_inhand_fixed))
    if variable_inhand:
        st.metric("Bonus In-Hand (Net)", fmt(variable_inhand))
    if rsu_inhand:
        st.metric("RSU In-Hand (Net)",   fmt(rsu_inhand))
    st.markdown("---")

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(139,92,246,0.12),rgba(124,58,237,0.22));
                padding:18px 20px;border-radius:14px;border:1px solid rgba(139,92,246,0.3);
                text-align:center;">
        <p style="color:#c4b5fd;margin:0;font-size:11px;text-transform:uppercase;font-weight:700;letter-spacing:1.5px;">Total Annual Net Pay</p>
        <div style="color:#a78bfa;margin:6px 0 4px;font-family:'Outfit',sans-serif;font-size:34px;font-weight:800;">
            ₹{total_annual_inhand:,.0f}
        </div>
        <p style="color:#7c3aed;margin:0;font-size:11px;">{pct(take_home_pct)} of Total CTC</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"**Effective Tax Rate: {pct(eff_tax_rate)}**")
    st.progress(min(int(eff_tax_rate), 100))

    # Surcharge / rebate warning badges
    if t_total["rebate_87a"] > 0:
        st.success(f"✅ Rebate u/s 87A applied: {fmt(t_total['rebate_87a'])}", icon=None)
    if t_total["surcharge_relief"] > 0:
        st.info(f"🛡️ Marginal relief on surcharge: {fmt(t_total['surcharge_relief'])}", icon=None)
        st.markdown(f"""
        <div style="background-color:rgba(56,189,248,0.1); border-left:3px solid #38bdf8; padding:10px 14px; border-radius:4px; font-size:0.85rem; color:#bae6fd; margin-bottom:14px; margin-top:4px;">
            <b>💡 Why is my in-hand salary flat?</b><br>
            When you cross a surcharge threshold (like ₹50L or ₹1 Cr), marginal relief caps your tax jump. 
            However, it does this by taking <b>exactly 100%</b> of your extra income as tax for a short "flat zone" (e.g., up to ~₹1.02 Cr). 
            Your in-hand salary won't increase until your income clears this zone. This is standard Indian tax law!
        </div>
        """, unsafe_allow_html=True)
    if t_total["surcharge"] > 0:
        st.warning(f"⚠️ Surcharge ({int(t_total['surcharge_rate']*100)}%): {fmt(t_total['surcharge'])}", icon=None)

    st.caption("📌 FY 2025-26 / FY 2026-27 · New Regime · Slabs identical both years")


# ── Bottom Expanders ──────────────────────────────────────────────────────────
st.markdown("---")
b1, b2 = st.columns(2, gap="large")

with b1:
    with st.expander("🧮 Tax Slab Breakdown (on Total Taxable Income)", expanded=False):
        if total_taxable > 0:
            st.markdown(f"**Taxable Income:** ₹{total_taxable:,.0f}")
            slab_rows = compute_slab_rows(total_taxable)
            lines = ""
            for r in slab_rows:
                if r["tax"] > 0 or r["from"] == 0:
                    to_str = f"₹{r['to']/1e5:.1f}L" if r['to'] < 1e9 else "∞"
                    label  = f"₹{r['from']/1e5:.1f}L – {to_str}"
                    lines += f"""<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.05)">
                        <span style="color:#94a3b8">{label} @ {int(r['rate']*100)}%</span>
                        <span style="font-weight:600">₹{r['tax']:,.0f}</span></div>"""
            st.markdown(lines, unsafe_allow_html=True)

            st.markdown(f"""
            <div style="margin-top:12px;padding:12px;background:rgba(139,92,246,0.1);border-radius:10px;font-size:0.9rem">
              <div style="display:flex;justify-content:space-between;padding:3px 0"><span style="color:#94a3b8">Base Tax (slab total)</span><span>₹{t_total['base_tax']:,.0f}</span></div>
              <div style="display:flex;justify-content:space-between;padding:3px 0"><span style="color:#34d399">Rebate u/s 87A</span><span style="color:#34d399">– ₹{t_total['rebate_87a']:,.0f}</span></div>
              <div style="display:flex;justify-content:space-between;padding:3px 0"><span style="color:#94a3b8">Tax after rebate</span><span>₹{t_total['tax_after_rebate']:,.0f}</span></div>
              <div style="display:flex;justify-content:space-between;padding:3px 0"><span style="color:#94a3b8">Surcharge ({int(t_total['surcharge_rate']*100)}%) before relief</span><span>₹{t_total['tax_after_rebate']*t_total['surcharge_rate']:,.0f}</span></div>
              <div style="display:flex;justify-content:space-between;padding:3px 0"><span style="color:#38bdf8">Marginal relief on surcharge</span><span style="color:#38bdf8">– ₹{t_total['surcharge_relief']:,.0f}</span></div>
              <div style="display:flex;justify-content:space-between;padding:3px 0"><span style="color:#94a3b8">Surcharge (after relief)</span><span>₹{t_total['surcharge']:,.0f}</span></div>
              <div style="display:flex;justify-content:space-between;padding:3px 0"><span style="color:#94a3b8">Health &amp; Education Cess (4%)</span><span>₹{t_total['cess']:,.0f}</span></div>
              <div style="display:flex;justify-content:space-between;margin-top:8px;padding-top:8px;border-top:1px solid rgba(255,255,255,0.1)"><b>Total Tax Payable</b><b style="color:#a78bfa">₹{t_total['total']:,.0f}</b></div>
            </div>
            """, unsafe_allow_html=True)

            # FY note
            st.markdown("""<p style="color:#475569;font-size:0.75rem;margin-top:8px">
            ℹ️ FY 2025-26 and FY 2026-27 use identical slabs (Budget 2026 made no changes to new regime slabs).
            </p>""", unsafe_allow_html=True)
        else:
            st.info("Enter salary details to see slab breakdown.")

with b2:
    with st.expander("📋 Annual Deduction Summary", expanded=False):
        if annual_fixed_ctc > 0:
            items = [
                ("PF – Employer",         annual_pf_employer),
                ("PF – Employee",         annual_pf_employee),
                ("Gratuity (in CTC)",     annual_gratuity),
                ("Standard Deduction",    standard_deduction),
                ("Profession Tax",        profession_tax_ann),
                ("Income Tax (Fixed)",    tax_fixed),
            ]
            lines = ""
            for label, val in items:
                lines += f"""<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.05)">
                    <span style="color:#94a3b8">{label}</span>
                    <span style="font-weight:600">₹{val:,.0f}</span></div>"""
            st.markdown(lines, unsafe_allow_html=True)
            st.markdown(f"""
            <div style="margin-top:12px;padding:10px 14px;background:rgba(16,185,129,0.08);border-radius:8px;display:flex;justify-content:space-between;font-size:0.9rem">
                <b>Fixed CTC</b><b>₹{annual_fixed_ctc:,.0f}</b></div>
            <div style="padding:8px 14px;background:rgba(16,185,129,0.05);border-radius:8px;display:flex;justify-content:space-between;margin-top:4px;font-size:0.9rem">
                <b style="color:#34d399">Annual In-Hand (Fixed)</b><b style="color:#34d399">₹{annual_inhand_fixed:,.0f}</b></div>
            """, unsafe_allow_html=True)

            if variable_annual + rsu_annual_inr > 0:
                st.markdown(f"""
                <div style="margin-top:10px;padding:12px;background:rgba(139,92,246,0.1);border-radius:10px;font-size:0.9rem">
                  <div style="display:flex;justify-content:space-between;padding:3px 0"><span style="color:#94a3b8">Gross Var + RSU</span><span>₹{variable_annual+rsu_annual_inr:,.0f}</span></div>
                  <div style="display:flex;justify-content:space-between;padding:3px 0"><span style="color:#94a3b8">Tax on Var + RSU</span><span>₹{tax_on_var_rsu:,.0f}</span></div>
                  <div style="display:flex;justify-content:space-between;padding:3px 0;border-top:1px solid rgba(255,255,255,0.08);margin-top:4px">
                    <b style="color:#a78bfa">Var + RSU In-Hand</b><b style="color:#a78bfa">₹{total_var_rsu_inhand:,.0f}</b></div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Enter salary details to see deduction summary.")
