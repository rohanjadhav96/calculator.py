import streamlit as st
import math

# --- Page Config ---
st.set_page_config(page_title="Prop Calculator", page_icon="🧮")

# --- Constants & Settings ---
# Instrument Specs (Point Values)
INSTRUMENTS = {
    "NQ (Mini)": {"val": 20.0, "type": "mini"},
    "MNQ (Micro)": {"val": 2.0, "type": "micro"},
    "ES (Mini)": {"val": 50.0, "type": "mini"},
    "MES (Micro)": {"val": 5.0, "type": "micro"},
}

# Account Presets
PRESETS = {
    "Lucid Flex 50k": {
        "size": 50000, "target": 3000, "consistency": 0.50,
        "max_dd": 2000, "max_minis": 4, "max_micros": 40, "daily_loss": 0
    },
    "Tradeify Select 50k": {
        "size": 50000, "target": 2500, "consistency": 0.40,
        "max_dd": 2000, "max_minis": 4, "max_micros": 40, "daily_loss": 0
    },
    "🛠️ Custom / Other": {
        "size": 50000, "target": 3000, "consistency": 0.0,
        "max_dd": 2000, "max_minis": 10, "max_micros": 100, "daily_loss": 0
    }
}

st.title("🧮 Prop Calculator")

# --- 1. Account Configuration ---
with st.expander("⚙️ Account Rules & Settings", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        account_choice = st.selectbox("Select Account:", list(PRESETS.keys()))
    with c2:
        stage = st.selectbox("Stage:", ["Evaluation", "Funded"])

    # Load & Edit Rules
    defaults = PRESETS[account_choice]
    is_custom = (account_choice == "🛠️ Custom / Other")

    col1, col2, col3 = st.columns(3)
    with col1:
        acc_size = st.number_input("Account Size ($)", value=defaults["size"], disabled=not is_custom)
        max_dd = st.number_input("Max Drawdown ($)", value=defaults["max_dd"], disabled=not is_custom)
    with col2:
        profit_target = st.number_input("Profit Target ($)", value=defaults["target"], disabled=not is_custom)
        consistency_pct = st.number_input("Consistency %", value=defaults["consistency"], step=0.1, disabled=not is_custom)
    with col3:
        max_minis = st.number_input("Max Minis", value=defaults["max_minis"], disabled=not is_custom)
        max_micros = st.number_input("Max Micros", value=defaults["max_micros"], disabled=not is_custom)
        daily_loss = st.number_input("Daily Loss Limit ($)", value=defaults["daily_loss"], disabled=not is_custom)

# --- 2. Calculator Inputs ---
st.divider()

# Mode & Instrument Selection
c_mode, c_inst = st.columns([1, 1])
with c_mode:
    calc_mode = st.radio("Mode:", ["💰 Calculate P&L", "🛡️ Calculate Quantity"])
with c_inst:
    selected_inst = st.selectbox("Instrument:", list(INSTRUMENTS.keys()))

# Get Instrument Details
inst_data = INSTRUMENTS[selected_inst]
point_val = inst_data["val"]
limit_size = max_minis if inst_data["type"] == "mini" else max_micros

# Points Input
c_sl, c_tp = st.columns(2)
with c_sl:
    sl_pts = st.number_input("Stop Loss (Pts):", 1.0, 500.0, 10.0, 0.5)
with c_tp:
    tp_pts = st.number_input("Take Profit (Pts):", 1.0, 1000.0, 20.0, 0.5)

# Calculate Quantity
qty = 0
if "Calculate P&L" in calc_mode:
    qty = st.number_input("Quantity:", min_value=1, value=1)
    if qty > limit_size:
        st.error(f"🚫 **Limit Exceeded!** Max allowed for {inst_data['type']}s is {limit_size}.")
        st.stop()
else:
    risk_usd = st.number_input("Max Risk Amount ($):", value=300.0, step=10.0)
    risk_per_con = sl_pts * point_val
    qty = math.floor(risk_usd / risk_per_con)
    
    if qty > limit_size:
        st.warning(f"⚠️ **Capped at Limit:** Risk allows {qty}, but account limit is {limit_size}.")
        qty = limit_size
    elif qty == 0:
        st.error(f"❌ Stop loss too wide! Min risk for 1 contract is ${risk_per_con:.0f}.")
        st.stop()

# --- 3. Results ---
st.divider()
st.subheader(f"📊 Results: {qty} x {selected_inst}")

risk_total = qty * sl_pts * point_val
reward_total = qty * tp_pts * point_val

m1, m2, m3 = st.columns(3)
m1.metric("Total Risk", f"-${risk_total:,.2f}")
m2.metric("Total Profit", f"+${reward_total:,.2f}")
m3.metric("Risk per Contract", f"${sl_pts * point_val:.0f}")

# --- 4. Rule Checks ---
st.subheader("🛡️ Safety Check")

# Drawdown Check
dd_status = "✅ Safe"
if daily_loss > 0 and risk_total > daily_loss:
    st.error(f"❌ **Violates Daily Loss Limit** (${daily_loss})")
elif risk_total > max_dd:
    st.error(f"💀 **Account Blown** (Risk > Max DD ${max_dd})")
elif risk_total > (max_dd * 0.5):
    st.warning(f"⚠️ **High Risk:** Risking >50% of your drawdown space.")
else:
    st.success(f"✅ Risk is within drawdown limits.")

# Consistency Check (Eval Only)
if stage == "Evaluation" and consistency_pct > 0:
    max_day = profit_target * consistency_pct
    if reward_total > max_day:
        st.warning(f"⚠️ **Consistency Warning:** Profit (${reward_total:,.0f}) > Daily Limit (${max_day:,.0f}).")
        st.caption("If you hit TP, this trade might trigger a consistency review.")
    else:
        st.success(f"✅ Profit fits consistency rules (Limit: ${max_day:,.0f})")

# Funding Info
st.caption(f"Calculated using {selected_inst} @ ${point_val}/point.")
