import streamlit as st
import math

# --- Page Config ---
st.set_page_config(page_title="Lucid Flex Position Sizer", page_icon="⚖️")

# --- Constants ---
# NQ = $20 per point, MNQ = $2 per point
POINT_VALUE_NQ = 20.0
POINT_VALUE_MNQ = 2.0

st.title("⚖️ Lucid Flex 50k Calculator")

# --- Mode Selection ---
mode = st.radio(
    "What do you want to calculate?",
    ["💰 Calculate P&L (I know my Qty)", "🛡️ Calculate Quantity (I know my Risk $)"],
    horizontal=True
)

st.divider()

# ==========================================
# MODE 1: Calculate Quantity (Risk Based)
# ==========================================
if "Calculate Quantity" in mode:
    st.subheader("🛡️ Risk-Based Position Sizer")
    
    col1, col2 = st.columns(2)
    with col1:
        contract_type = st.radio("Select Instrument:", ["NQ (Mini)", "MNQ (Micro)"])
    with col2:
        max_risk_usd = st.number_input("Max Loss Allowed ($):", min_value=10.0, value=300.0, step=10.0)

    col3, col4 = st.columns(2)
    with col3:
        stop_loss_pts = st.number_input("Stop Loss (Points):", min_value=1.0, value=10.0, step=0.5)
    with col4:
        take_profit_pts = st.number_input("Take Profit (Points):", min_value=1.0, value=20.0, step=0.5)

    # Logic
    point_val = POINT_VALUE_NQ if contract_type == "NQ (Mini)" else POINT_VALUE_MNQ
    risk_per_contract = stop_loss_pts * point_val
    
    # Calculate Max Quantity (Rounded Down)
    if risk_per_contract > 0:
        suggested_qty = math.floor(max_risk_usd / risk_per_contract)
    else:
        suggested_qty = 0

    # Display Result
    st.markdown("### 🎯 Recommended Position Size")
    
    if suggested_qty == 0:
        st.error(f"❌ **Stop Loss is too wide!** You cannot trade even 1 contract within your ${max_risk_usd} limit.")
        st.info(f"1 Contract Risk: ${risk_per_contract:.2f}")
    else:
        st.success(f"**{suggested_qty} Contracts**")
        
        # Breakdown
        actual_risk = suggested_qty * risk_per_contract
        potential_reward = suggested_qty * (take_profit_pts * point_val)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Actual Risk", f"-${actual_risk:.2f}")
        c2.metric("Potential Profit", f"+${potential_reward:.2f}")
        c3.metric("Remaining Buffer", f"${max_risk_usd - actual_risk:.2f}")
        
        # NQ/MNQ Conversion Tip
        if contract_type == "NQ (Mini)" and suggested_qty == 0:
            mnq_equiv = math.floor(max_risk_usd / (stop_loss_pts * POINT_VALUE_MNQ))
            st.info(f"💡 Tip: Switch to **MNQ**. You could trade **{mnq_equiv} MNQ** contracts instead.")

# ==========================================
# MODE 2: Calculate P&L (Standard)
# ==========================================
else:
    st.subheader("💰 Standard P&L Calculator")
    
    col1, col2 = st.columns(2)
    with col1:
        contract_type = st.radio("Select Instrument:", ["NQ (Mini)", "MNQ (Micro)"])
    with col2:
        quantity = st.number_input("Quantity:", min_value=1, value=1, step=1)

    col3, col4 = st.columns(2)
    with col3:
        stop_loss_pts = st.number_input("Stop Loss (Points):", min_value=0.0, value=10.0, step=0.25)
    with col4:
        take_profit_pts = st.number_input("Take Profit (Points):", min_value=0.0, value=20.0, step=0.25)

    # Logic
    point_val = POINT_VALUE_NQ if contract_type == "NQ (Mini)" else POINT_VALUE_MNQ
    
    total_risk = quantity * (stop_loss_pts * point_val)
    total_reward = quantity * (take_profit_pts * point_val)

    # Display
    st.markdown("### 📊 Trade Outcome")
    m1, m2 = st.columns(2)
    m1.metric("Total Risk", f"-${total_risk:,.2f}")
    m2.metric("Total Profit", f"+${total_reward:,.2f}")
    
    # 50k Account Sanity Checks
    st.caption("--- Account Safety Checks ---")
    if total_risk > 600:
        st.error("⚠️ **High Risk:** This exceeds typical daily loss limits for 50k accounts.")
    elif total_reward > 1500:
        st.warning("⚠️ **Consistency Check:** Profit > $1500 (50% of $3k target). Ensure this aligns with your consistency rules.")
