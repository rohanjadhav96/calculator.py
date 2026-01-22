import streamlit as st
import math

# --- Page Config ---
st.set_page_config(page_title="Dual Prop Calculator", page_icon="⚖️")

# --- Constants & Settings ---
# Asset Groups (Mini & Micro paired)
ASSET_GROUPS = {
    "Nasdaq (NQ & MNQ)": {
        "mini_name": "NQ", "mini_val": 20.0,
        "micro_name": "MNQ", "micro_val": 2.0
    },
    "S&P 500 (ES & MES)": {
        "mini_name": "ES", "mini_val": 50.0,
        "micro_name": "MES", "micro_val": 5.0
    }
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

st.title("⚖️ NQ/MNQ & ES/MES Comparator")

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
        limit_mini = st.number_input("Max Minis", value=defaults["max_minis"], disabled=not is_custom)
        limit_micro = st.number_input("Max Micros", value=defaults["max_micros"], disabled=not is_custom)
        daily_loss = st.number_input("Daily Loss Limit ($)", value=defaults["daily_loss"], disabled=not is_custom)

# --- 2. Calculator Inputs ---
st.divider()

# Mode & Asset Selection
c_mode, c_asset = st.columns([1, 1])
with c_mode:
    calc_mode = st.radio("Mode:", ["🛡️ Calculate Quantity (Risk Based)", "💰 Calculate P&L (Manual Qty)"])
with c_asset:
    selected_group = st.selectbox("Asset Class:", list(ASSET_GROUPS.keys()))

# Get Asset Details
asset = ASSET_GROUPS[selected_group]

# Points Input
c_sl, c_tp = st.columns(2)
with c_sl:
    sl_pts = st.number_input("Stop Loss (Points):", 1.0, 500.0, 10.0, 0.5)
with c_tp:
    tp_pts = st.number_input("Take Profit (Points):", 1.0, 1000.0, 20.0, 0.5)

# Initialize Variables
mini_qty, micro_qty = 0, 0

# --- CALCULATION LOGIC ---

if "Risk Based" in calc_mode:
    # Input Risk
    risk_usd = st.number_input("Max Risk Amount ($):", value=500.0, step=10.0)
    
    # Calc Mini
    mini_risk_per_con = sl_pts * asset["mini_val"]
    mini_qty = math.floor(risk_usd / mini_risk_per_con)
    # Cap Mini
    if mini_qty > limit_mini: mini_qty = limit_mini
    
    # Calc Micro
    micro_risk_per_con = sl_pts * asset["micro_val"]
    micro_qty = math.floor(risk_usd / micro_risk_per_con)
    # Cap Micro
    if micro_qty > limit_micro: micro_qty = limit_micro

else:
    # Manual Input
    c_qty_mini, c_qty_micro = st.columns(2)
    with c_qty_mini:
        mini_qty = st.number_input(f"Qty {asset['mini_name']}:", min_value=0, value=1)
    with c_qty_micro:
        micro_qty = st.number_input(f"Qty {asset['micro_name']}:", min_value=0, value=0)


# --- 3. DISPLAY RESULTS (Side by Side) ---
st.divider()
st.subheader("📊 Trade Options Comparison")

col_mini, col_micro = st.columns(2)

# --- LEFT COLUMN: MINI (NQ/ES) ---
with col_mini:
    st.markdown(f"### 🦁 {asset['mini_name']} (Mini)")
    if mini_qty == 0:
        st.error("Stop Loss too wide for risk amount.")
    else:
        # Mini Math
        risk_mini = mini_qty * sl_pts * asset["mini_val"]
        reward_mini = mini_qty * tp_pts * asset["mini_val"]
        
        st.info(f"**Qty: {mini_qty} Contracts**")
        st.metric("Risk (Loss)", f"-${risk_mini:,.2f}")
        st.metric("Reward (Profit)", f"+${reward_mini:,.2f}")
        
        # Rule Checks
        if daily_loss > 0 and risk_mini > daily_loss:
            st.warning(f"⚠️ Exceeds Daily Loss (${daily_loss})")
        if risk_mini > max_dd:
            st.error(f"💀 BLOWS ACCOUNT (DD: {max_dd})")

# --- RIGHT COLUMN: MICRO (MNQ/MES) ---
with col_micro:
    st.markdown(f"### 🐭 {asset['micro_name']} (Micro)")
    if micro_qty == 0:
        st.error("Stop Loss too wide.")
    else:
        # Micro Math
        risk_micro = micro_qty * sl_pts * asset["micro_val"]
        reward_micro = micro_qty * tp_pts * asset["micro_val"]
        
        st.success(f"**Qty: {micro_qty} Contracts**")
        st.metric("Risk (Loss)", f"-${risk_micro:,.2f}")
        st.metric("Reward (Profit)", f"+${reward_micro:,.2f}")
        
        # Micro Benefit Calculation
        st.caption(f"💡 **Granularity:** You can trim this position in {micro_qty} parts.")

# --- 4. CONSISTENCY CHECK (Global) ---
if stage == "Evaluation" and consistency_pct > 0:
    st.divider()
    max_day = profit_target * consistency_pct
    st.write(f"**Consistency Limit:** ${max_day:,.0f}")
    
    # Check if Mini violates
    if mini_qty > 0:
        mini_reward = mini_qty * tp_pts * asset["mini_val"]
        if mini_reward > max_day:
            st.warning(f"⚠️ **{asset['mini_name']} Warning:** Hitting TP (${mini_reward:,.0f}) will exceed your daily consistency limit.")
        else:
            st.caption(f"✅ {asset['mini_name']} TP is safe.")
            
    # Check if Micro violates
    if micro_qty > 0:
        micro_reward = micro_qty * tp_pts * asset["micro_val"]
        if micro_reward > max_day:
            st.warning(f"⚠️ **{asset['micro_name']} Warning:** Hitting TP (${micro_reward:,.0f}) will exceed your daily consistency limit.")
