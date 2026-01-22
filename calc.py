import streamlit as st
import math

# --- Page Config ---
st.set_page_config(page_title="Prop Risk Manager", page_icon="🎯", layout="centered")

# --- Constants & Settings ---
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

st.title("🎯 Prop Risk Manager")

# --- 1. Account Configuration ---
with st.expander("⚙️ Account Rules", expanded=False):
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

# Define Asset Options structure
ASSET_OPTIONS = {
    "comparisons": {
        "Nasdaq (NQ & MNQ)": {"mini": "NQ", "micro": "MNQ", "mini_val": 20, "micro_val": 2},
        "S&P 500 (ES & MES)": {"mini": "ES", "micro": "MES", "mini_val": 50, "micro_val": 5}
    },
    "singles": {
        "Only NQ (Mini)": {"name": "NQ", "val": 20, "type": "mini"},
        "Only MNQ (Micro)": {"name": "MNQ", "val": 2, "type": "micro"},
        "Only ES (Mini)": {"name": "ES", "val": 50, "type": "mini"},
        "Only MES (Micro)": {"name": "MES", "val": 5, "type": "micro"}
    }
}

# Create a flattened list for the dropdown
dropdown_options = list(ASSET_OPTIONS["comparisons"].keys()) + ["---"] + list(ASSET_OPTIONS["singles"].keys())

with c_asset:
    selected_option = st.selectbox("Instrument View:", dropdown_options)

# Handle Separator Selection
if selected_option == "---":
    st.warning("Please select a valid instrument.")
    st.stop()

# Determine if it's a Comparison or Single View
is_comparison = selected_option in ASSET_OPTIONS["comparisons"]

# Points Input
c_sl, c_tp = st.columns(2)
with c_sl:
    sl_pts = st.number_input("Stop Loss (Points):", 1.0, 500.0, 10.0, 0.5)
with c_tp:
    tp_pts = st.number_input("Take Profit (Points):", 1.0, 1000.0, 20.0, 0.5)


# --- LOGIC & RENDERING ---
st.divider()

# HELPER: Display Single Card
def render_card(title, qty, risk, reward, limit_warning=False, blow_warning=False):
    if qty == 0:
        st.error(f"❌ Stop too wide for **{title}**")
        return

    st.subheader(f"{title}")
    st.info(f"**Qty: {qty} Contracts**")
    
    col_a, col_b = st.columns(2)
    col_a.metric("Risk", f"-${risk:,.2f}")
    col_b.metric("Profit", f"+${reward:,.2f}")

    if limit_warning:
        st.warning(f"⚠️ Quantity capped at account limit.")
    if blow_warning:
        st.error(f"💀 **BLOWS ACCOUNT** (Risk > {max_dd})")
    elif daily_loss > 0 and risk > daily_loss:
        st.error(f"❌ **Exceeds Daily Loss** (${daily_loss})")

    # Consistency Check
    if stage == "Evaluation" and consistency_pct > 0:
        max_day = profit_target * consistency_pct
        if reward > max_day:
            st.warning(f"⚠️ **Consistency Risk:** Profit > ${max_day:,.0f}")
        else:
            st.caption(f"✅ Safe for consistency (<${max_day:,.0f})")


# ==========================================
# SCENARIO A: SIDE-BY-SIDE COMPARISON
# ==========================================
if is_comparison:
    data = ASSET_OPTIONS["comparisons"][selected_option]
    
    # Calculate Qty
    if "Risk Based" in calc_mode:
        risk_usd = st.number_input("Max Risk Amount ($):", value=500.0, step=10.0)
        
        q_mini = math.floor(risk_usd / (sl_pts * data["mini_val"]))
        q_mini = min(q_mini, limit_mini) # Cap limit
        
        q_micro = math.floor(risk_usd / (sl_pts * data["micro_val"]))
        q_micro = min(q_micro, limit_micro) # Cap limit
    else:
        c_q1, c_q2 = st.columns(2)
        q_mini = c_q1.number_input(f"Qty {data['mini']}", min_value=0, value=1)
        q_micro = c_q2.number_input(f"Qty {data['micro']}", min_value=0, value=0)

    # Render Side by Side
    st.subheader("📊 Comparison")
    col1, col2 = st.columns(2)
    
    with col1:
        risk_m = q_mini * sl_pts * data["mini_val"]
        reward_m = q_mini * tp_pts * data["mini_val"]
        render_card(f"🦁 {data['mini']}", q_mini, risk_m, reward_m, q_mini==limit_mini, risk_m > max_dd)

    with col2:
        risk_mi = q_micro * sl_pts * data["micro_val"]
        reward_mi = q_micro * tp_pts * data["micro_val"]
        render_card(f"🐭 {data['micro']}", q_micro, risk_mi, reward_mi, q_micro==limit_micro, risk_mi > max_dd)


# ==========================================
# SCENARIO B: SINGLE INSTRUMENT VIEW
# ==========================================
else:
    data = ASSET_OPTIONS["singles"][selected_option]
    limit = limit_mini if data["type"] == "mini" else limit_micro

    # Calculate Qty
    if "Risk Based" in calc_mode:
        risk_usd = st.number_input("Max Risk Amount ($):", value=500.0, step=10.0)
        qty = math.floor(risk_usd / (sl_pts * data["val"]))
        
        capped = False
        if qty > limit:
            qty = limit
            capped = True
    else:
        qty = st.number_input("Quantity:", min_value=1, value=1)
        if qty > limit:
            st.error(f"🚫 Limit is {limit} contracts.")
            st.stop()
        capped = False

    # Render Single Centered Card
    risk_val = qty * sl_pts * data["val"]
    reward_val = qty * tp_pts * data["val"]
    
    st.markdown("---")
    render_card(f"💎 {data['name']}", qty, risk_val, reward_val, capped, risk_val > max_dd)
