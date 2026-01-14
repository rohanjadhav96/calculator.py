import streamlit as st

# --- Page Config ---
st.set_page_config(page_title="Lucid Flex NQ Calculator", page_icon="📈")

# --- Constants for Lucid Flex 50k Account ---
ACCOUNT_SIZE = 50000
MAX_DRAWDOWN_LIMIT = 2000  # $2000 EOD Trailing Drawdown
PROFIT_TARGET = 3000       # $3000 Target
DAILY_LOSS_LIMIT = 600     # Typical daily limit for 50k accounts (Check your dashboard to verify)
CONSISTENCY_PCT = 0.50     # 50% Consistency rule

# --- Contract Specs (CME Group) ---
# NQ = $20 per point
# MNQ = $2 per point
TICKS_PER_POINT = 4

st.title("📈 Lucid Flex NQ/MNQ Calculator")
st.markdown("For **50k Accounts** ($2k Drawdown / $3k Target)")

# --- User Inputs ---
col1, col2 = st.columns(2)

with col1:
    contract_type = st.radio("Select Contract:", ["NQ (Mini)", "MNQ (Micro)"])
    
with col2:
    quantity = st.number_input("Contract Quantity:", min_value=1, value=1, step=1)

# Set Multiplier based on selection
if contract_type == "NQ (Mini)":
    point_value = 20.0
else:
    point_value = 2.0

st.divider()

col3, col4 = st.columns(2)
with col3:
    stop_loss_pts = st.number_input("Stop Loss (Points):", min_value=0.0, value=10.0, step=0.25)
with col4:
    take_profit_pts = st.number_input("Take Profit (Points):", min_value=0.0, value=20.0, step=0.25)

# --- Calculations ---
risk_per_contract = stop_loss_pts * point_value
reward_per_contract = take_profit_pts * point_value

total_risk = risk_per_contract * quantity
total_reward = reward_per_contract * quantity

# --- Display Results ---
st.subheader("💰 Trade Outcome")

# Create 3 columns for metrics
m1, m2, m3 = st.columns(3)
m1.metric(label="Total Risk (Loss)", value=f"-${total_risk:,.2f}")
m2.metric(label="Total Reward (Profit)", value=f"+${total_reward:,.2f}")
m3.metric(label="Risk/Reward Ratio", value=f"1 : {take_profit_pts/stop_loss_pts if stop_loss_pts > 0 else 0:.1f}")

# --- Prop Firm Risk Checks ---
st.subheader("⚠️ Prop Firm Risk Checks")

# 1. Daily Loss Limit Check
if total_risk > DAILY_LOSS_LIMIT:
    st.error(f"❌ **DANGER:** This trade risk (${total_risk}) exceeds the typical daily loss limit (${DAILY_LOSS_LIMIT}).")
elif total_risk > (DAILY_LOSS_LIMIT * 0.8):
    st.warning(f"⚠️ **Caution:** You are risking close to the daily limit (${DAILY_LOSS_LIMIT}).")
else:
    st.success(f"✅ Trade is within daily risk limits.")

# 2. Consistency Rule Check
# 50% consistency means no single day can be > 50% of total profit target ($3000)
# This usually applies to withdrawals, but good to keep in mind.
max_single_day_profit = PROFIT_TARGET * CONSISTENCY_PCT
if total_reward > max_single_day_profit:
    st.warning(f"⚠️ **Consistency Warning:** A profit of ${total_reward} exceeds 50% of your total profit target (${max_single_day_profit}). This might impact your consistency rule if you hit TP.")
else:
    st.info(f"✅ Profit is within the 50% consistency buffer (${max_single_day_profit}).")

st.caption(f"Note: Calculations based on {contract_type} @ ${point_value}/point.")
