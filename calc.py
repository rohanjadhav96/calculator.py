import streamlit as st
import math

# --- Page Config ---
st.set_page_config(page_title="Prop Account Manager", page_icon="🏦")

# --- Account Configuration Database ---
# Based on your screenshots
ACCOUNTS = {
    "Lucid Flex 50k": {
        "target": 3000,
        "consistency": 0.50,  # 50%
        "max_dd": 2000,
        "max_minis": 4,
        "max_micros": 40,
        "daily_loss": None  # Lucid Flex has no Daily Loss Limit
    },
    "Tradeify Select 50k": {
        "target": 2500,       # Lower target
        "consistency": 0.40,  # Stricter consistency (40%)
        "max_dd": 2000,
        "max_minis": 4,
        "max_micros": 40,
        "daily_loss": None  # Eval has no DLL
    }
}

# --- Constants ---
POINT_VALUE_NQ = 20.0
POINT_VALUE_MNQ = 2.0

st.title("🏦 Prop Account Risk Manager")

# --- Top Bar: Account Settings ---
with st.container():
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        account_choice = st.selectbox("Select Account:", list(ACCOUNTS.keys()))
    with c2:
        stage = st.selectbox("Stage:", ["Evaluation", "Funded"])
    with c3:
        # Just a visual indicator of the max size
        st.info(f"Max Size: **{ACCOUNTS[account_choice]['max_minis']} NQ**")

    # Load selected account rules
    rules = ACCOUNTS[account_choice]

# --- Calculator Mode ---
st.divider()
mode = st.radio(
    "Calculator Mode:",
    ["💰 Calculate P&L (Manual Size)", "🛡️ Calculate Max Size (Risk Based)"],
    horizontal=True
)

st.divider()

# ==========================================
# LOGIC BLOCK
# ==========================================

# 1. Inputs common to both modes
col_instr, col_pts = st.columns(2)
with col_instr:
    contract_type = st.radio("Instrument:", ["NQ (Mini)", "MNQ (Micro)"], horizontal=True)
    point_val = POINT_VALUE_NQ if contract_type == "NQ (Mini)" else POINT_VALUE_MNQ
    max_allowed_size = rules['max_minis'] if contract_type == "NQ (Mini)" else rules['max_micros']

with col_pts:
    stop_loss_pts = st.number_input("Stop Loss (Pts):", 1.0, 50.0, 10.0, 0.5)
    take_profit_pts = st.number_input("Take Profit (Pts):", 1.0, 100.0, 20.0, 0.5)

# 2. Mode Specific Inputs & Calcs
qty = 0
if "Manual Size" in mode:
    qty = st.number_input("Contract Quantity:", min_value=1, max_value=100, value=1)
    
    # HARD LIMIT CHECK
    if qty > max_allowed_size:
        st.error(f"🚫 **VIOLATION:** {qty} contracts exceeds the {account_choice} limit of {max_allowed_size}!")
        st.stop() # Stop execution here to prevent showing invalid numbers
        
elif "Risk Based" in mode:
    max_risk_usd = st.number_input("Max Risk ($):", 50.0, 2000.0, 300.0, 10.0)
    risk_per_contract = stop_loss_pts * point_val
    qty = math.floor(max_risk_usd / risk_per_contract)
    
    # HARD LIMIT CHECK
    if qty > max_allowed_size:
        st.warning(f"⚠️ **Limit Capped:** Your risk allows {qty} contracts, but the account limit is {max_allowed_size}. Setting to {max_allowed_size}.")
        qty = max_allowed_size

# 3. Final Calculations
total_risk = qty * stop_loss_pts * point_val
total_reward = qty * take_profit_pts * point_val

# ==========================================
# RESULTS DISPLAY
# ==========================================
st.subheader(f"📊 Results ({qty} Contracts)")

# Metrics
m1, m2, m3 = st.columns(3)
m1.metric("Total Risk", f"-${total_risk:,.2f}")
m2.metric("Total Profit", f"+${total_reward:,.2f}")
m3.metric("R:R Ratio", f"1 : {take_profit_pts/stop_loss_pts:.1f}")

# ==========================================
# PROP FIRM RULE CHECKS
# ==========================================
st.markdown("---")
st.subheader("👮 Rule Check")

c_rule1, c_rule2 = st.columns(2)

# Check 1: Drawdown / Daily Loss
with c_rule1:
    # Lucid/Tradeify Flex usually don't have DLL, but good to check against 'death' (Total DD)
    if total_risk > rules['max_dd']:
        st.error(f"💀 **Account Blown:** Risk (${total_risk}) > Max Drawdown (${rules['max_dd']})")
    elif total_risk > 1000:
        st.warning(f"⚠️ **High Risk:** Risking ${total_risk} in one trade is dangerous for a 50k account.")
    else:
        st.success(f"✅ Risk is safe (< $1000)")

# Check 2: Consistency (Evaluation Only)
with c_rule2:
    if stage == "Evaluation":
        # Calculate the max allowed profit in a single day
        max_day_limit = rules['target'] * rules['consistency']
        
        st.write(f"**Consistency Rule ({int(rules['consistency']*100)}%):**")
        if total_reward > max_day_limit:
            st.error(f"❌ **Profit Warning:** ${total_reward:,.0f} exceeds the single-day limit of ${max_day_limit:,.0f}!")
            st.caption(f"If you hit TP, this trade will count for >{int(rules['consistency']*100)}% of your target.")
        else:
            st.success(f"✅ Profit within limit (${max_day_limit:,.0f})")
    else:
        st.info("No Consistency Rule in Funded (Flex/Select).")

# Visual Progress Bar for Consistency
if stage == "Evaluation" and total_reward <= (rules['target'] * rules['consistency']) * 1.5:
    pct_of_limit = min(total_reward / (rules['target'] * rules['consistency']), 1.0)
    st.progress(pct_of_limit, text=f"Trade Profit vs Consistency Limit ({int(pct_of_limit*100)}%)")
