import streamlit as st
import math

# --- Page Config ---
st.set_page_config(page_title="Universal Prop Calculator", page_icon="🧮")

# --- Default Presets (Lucid & Tradeify) ---
PRESETS = {
    "Lucid Flex 50k": {
        "size": 50000,
        "target": 3000,
        "consistency": 0.50,
        "max_dd": 2000,
        "max_minis": 4,
        "max_micros": 40,
        "daily_loss": 0  # 0 = No Limit
    },
    "Tradeify Select 50k": {
        "size": 50000,
        "target": 2500,
        "consistency": 0.40,
        "max_dd": 2000,
        "max_minis": 4,
        "max_micros": 40,
        "daily_loss": 0
    },
    "🛠️ Custom / Other": {
        "size": 50000,
        "target": 3000,
        "consistency": 0.0,
        "max_dd": 2000,
        "max_minis": 10,
        "max_micros": 100,
        "daily_loss": 0
    }
}

# --- Constants ---
POINT_VALUE_NQ = 20.0
POINT_VALUE_MNQ = 2.0

st.title("🧮 Universal Prop Calculator")

# --- Account Selection & Configuration ---
with st.expander("⚙️ Account Settings", expanded=True):
    col_sel, col_stage = st.columns(2)
    with col_sel:
        account_choice = st.selectbox("Select Account / Mode:", list(PRESETS.keys()))
    with col_stage:
        stage = st.selectbox("Current Stage:", ["Evaluation", "Funded"])

    # Load defaults from preset
    defaults = PRESETS[account_choice]

    # If Custom is selected, show inputs. If not, show inputs but disabled (read-only)
    is_custom = (account_choice == "🛠️ Custom / Other")

    c1, c2, c3 = st.columns(3)
    with c1:
        acc_size = st.number_input("Account Size ($)", value=defaults["size"], disabled=not is_custom)
        max_dd = st.number_input("Max Drawdown ($)", value=defaults["max_dd"], disabled=not is_custom)
    with c2:
        profit_target = st.number_input("Profit Target ($)", value=defaults["target"], disabled=not is_custom)
        consistency_pct = st.number_input("Consistency % (0 = None)", value=defaults["consistency"], step=0.1, disabled=not is_custom)
    with c3:
        max_minis = st.number_input("Max Minis (NQ)", value=defaults["max_minis"], disabled=not is_custom)
        daily_loss = st.number_input("Daily Loss Limit ($) (0=None)", value=defaults["daily_loss"], disabled=not is_custom)

    # Max micros usually 10x minis, but let custom mode edit it
    max_micros = st.number_input("Max Micros (MNQ)", value=defaults["max_micros"], disabled=not is_custom)

# --- Calculator Logic ---
st.divider()

# Mode Selection
calc_mode = st.radio("Calculator Mode:", ["💰 Calculate P&L (Manual Size)", "🛡️ Calculate Max Size (Risk Based)"], horizontal=True)

# Common Inputs
c_instr, c_pts = st.columns(2)
with c_instr:
    contract_type = st.radio("Instrument:", ["NQ (Mini)", "MNQ (Micro)"], horizontal=True)
    point_val = POINT_VALUE_NQ if contract_type == "NQ (Mini)" else POINT_VALUE_MNQ
    limit_size = max_minis if contract_type == "NQ (Mini)" else max_micros

with c_pts:
    sl_pts = st.number_input("Stop Loss (Pts):", 1.0, 200.0, 10.0, 0.5)
    tp_pts = st.number_input("Take Profit (Pts):", 1.0, 500.0, 20.0, 0.5)

# Mode Specific Logic
qty = 0
if "Manual Size" in calc_mode:
    qty = st.number_input("Quantity:", min_value=1, value=1)
    if qty > limit_size:
        st.error(f"🚫 Exceeds Max Size! Limit is {limit_size}.")
        st.stop()
else:
    risk_usd = st.number_input("Max Risk ($):", value=300.0, step=10.0)
    risk_per_con = sl_pts * point_val
    qty = math.floor(risk_usd / risk_per_con)
    if qty > limit_size:
        st.warning(f"⚠️ Capped at max size {limit_size}.")
        qty = limit_size

# --- Results ---
st.divider()
st.subheader(f"📊 Results: {qty} Contracts")

risk_total = qty * sl_pts * point_val
reward_total = qty * tp_pts * point_val

m1, m2, m3 = st.columns(3)
m1.metric("Risk", f"-${risk_total:,.2f}")
m2.metric("Reward", f"+${reward_total:,.2f}")
m3.metric("R:R", f"1:{tp_pts/sl_pts:.1f}")

# --- Rule Checks ---
st.subheader("🛡️ Safety Check")

# 1. Drawdown / Daily Loss
if daily_loss > 0 and risk_total > daily_loss:
    st.error(f"❌ Violates Daily Loss Limit (${daily_loss})")
elif risk_total > max_dd:
    st.error(f"💀 Account Blown (Risk > Max DD ${max_dd})")
else:
    st.success("✅ Risk parameters safe")

# 2. Consistency (Only in Eval)
if stage == "Evaluation" and consistency_pct > 0:
    max_day = profit_target * consistency_pct
    st.write(f"**Consistency Limit:** ${max_day:,.0f} ({int(consistency_pct*100)}%)")
    
    if reward_total > max_day:
        st.warning(f"⚠️ Profit (${reward_total:,.0f}) exceeds consistency limit! This trade might not fully count.")
    else:
        st.success("✅ Profit within consistency limit")
elif stage == "Funded":
    st.info("ℹ️ Consistency rules usually removed in Funded stage (verify with firm).")
