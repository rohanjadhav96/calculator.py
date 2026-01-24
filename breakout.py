import streamlit as st
import pandas as pd

# --- CONFIGURATION ---
st.set_page_config(page_title="Breakout Hedge Pro (Strict Math)", layout="wide", page_icon="🧮")

# Custom Styling
st.markdown("""
<style>
    .metric-card { background-color: #1E1E1E; padding: 15px; border-radius: 8px; border: 1px solid #333; }
    .profit-text { color: #00FF7F; font-weight: bold; }
    .loss-text { color: #FF4B4B; font-weight: bold; }
    .warning-text { color: #FFA500; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("🧮 Breakout Hedge Pro: The 'True Cost' Calculator")
st.markdown("This tool includes **Commissions, Slippage, and Swaps** to match the Python script logic exactly.")

# --- SIDEBAR: INPUTS ---
with st.sidebar:
    st.header("1. Account & Rules")
    acct_size = st.number_input("Account Size ($)", 50000, step=10000)
    fee = st.number_input("Evaluation Fee ($)", 450)
    leverage = st.number_input("Max Leverage Allowed", 5, help="Breakout BTC/ETH is usually 5:1")
    daily_dd_pct = st.number_input("Daily Drawdown Limit (%)", 5.0) / 100
    
    st.header("2. Market Conditions")
    # Matches screenshot logic: commission = 0.0004 (0.04%)
    comm_rate = st.number_input("Commission Rate (%)", 0.04, step=0.01, format="%.4f") / 100
    slippage_pct = st.number_input("Est. Slippage (%)", 0.05, step=0.01) / 100
    spread_pct = st.number_input("Spread (%)", 0.02, step=0.01) / 100
    
    st.header("3. Holding Costs")
    funding_rate_8h = st.number_input("Funding Rate (per 8h %)", 0.01, format="%.4f") / 100
    days_held = st.number_input("Days to Hit Target", 2, step=1)
    
    st.header("4. Ratios (Prop:CEX)")
    ratio_p1 = st.number_input("Phase 1 Ratio", 5.8, step=0.1)
    ratio_p2 = st.number_input("Phase 2 Ratio", 3.2, step=0.1)

# --- CALCULATOR FUNCTIONS ---

def calculate_true_cost(target_net_profit, ratio, max_loss_limit):
    """
    Reverse engineers the trade to find out how much we actually need to Gross
    to net the target after paying commissions and slippage.
    """
    # 1. We need to find the required Position Size first.
    # Logic: To be safe, we base Position Size on the MAX LOSS LIMIT (Daily Limit).
    # If price moves X% against us, we must not lose more than Max Loss.
    # Let's assume a Stop Loss distance of 4% (leaving 1% buffer for daily limit) for safety.
    stop_loss_dist = 0.04 
    
    # Notional Position Size = Max_Risk / Stop_Loss_Dist
    # However, user wants "Max Size Possible".
    # Max Size by Leverage = Account * Leverage
    max_size_lev = acct_size * leverage
    
    # Max Size by Daily Limit (Assuming 1% bad wick/slippage on a 5% limit) is safer
    # But to match "Max Size" request, we use Leverage limit, but warn about risk.
    pos_size_prop = max_size_lev 
    
    # 2. Calculate Costs on Prop Side
    prop_comm_cost = pos_size_prop * comm_rate
    prop_slippage_cost = pos_size_prop * slippage_pct
    prop_spread_cost = pos_size_prop * spread_pct
    prop_swap_cost = pos_size_prop * funding_rate_8h * 3 * days_held # 3 intervals per day
    
    total_prop_friction = prop_comm_cost + prop_slippage_cost + prop_spread_cost + prop_swap_cost
    
    # 3. To Net $2500, we need to Gross ($2500 + Friction)
    required_gross_win = target_net_profit + total_prop_friction
    
    # 4. Calculate CEX Side
    pos_size_cex = pos_size_prop / ratio
    cex_comm_cost = pos_size_cex * comm_rate # Assuming similar fees on CEX
    cex_swap_cost = pos_size_cex * funding_rate_8h * 3 * days_held
    
    # The CEX Loss is the Gross Win divided by Ratio
    cex_trading_loss = required_gross_win / ratio
    
    # Total Cost to Pass = CEX Loss + CEX Fees
    total_cost_cex = cex_trading_loss + cex_comm_cost + cex_swap_cost
    
    return {
        "prop_size": pos_size_prop,
        "cex_size": pos_size_cex,
        "prop_friction": total_prop_friction,
        "cex_loss_total": total_cost_cex,
        "gross_needed": required_gross_win
    }

# --- PERFORM CALCULATIONS ---

# Phase 1
p1_target = acct_size * 0.05
p1_data = calculate_true_cost(p1_target, ratio_p1, acct_size * daily_dd_pct)

# Phase 2
p2_target = acct_size * 0.10
p2_data = calculate_true_cost(p2_target, ratio_p2, acct_size * daily_dd_pct)

# Total
total_sunk = p1_data['cex_loss_total'] + p2_data['cex_loss_total'] + fee

# --- DISPLAY ---

st.header("📊 Detailed Execution Plan (True Cost)")

# Warning about Max Size
if p1_data['prop_size'] > (acct_size * daily_dd_pct) / 0.01:
    st.error(f"⚠️ **CRITICAL WARNING:** You requested 'Max Size' (${p1_data['prop_size']:,.0f}). This size is dangerously high. A 1% move against you will breach the Daily Drawdown. Recommended size: < ${(acct_size*daily_dd_pct)/0.02:,.0f}.")

# TABS
tab1, tab2, tab3 = st.tabs(["Phase 1 Checklist", "Phase 2 Checklist", "Financial Breakdown"])

with tab1:
    st.subheader("Phase 1: The Filter")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""
        ### 🟢 Prop Account Setup
        * **Position Size (Notional):** `${p1_data['prop_size']:,.0f}`
        * **Leverage Used:** {leverage}x
        * **Target Net Profit:** ${p1_target:,.0f}
        * **Actual Gross Target:** `${p1_data['gross_needed']:,.2f}`
        * *(You need extra profit to cover ${p1_data['prop_friction']:,.2f} in fees/swaps)*
        """)
    with c2:
        st.markdown(f"""
        ### 🔴 CEX Account Setup
        * **Position Size (Notional):** `${p1_data['cex_size']:,.0f}`
        * **Direction:** Opposite to Prop
        * **Expected Loss:** `${p1_data['cex_loss_total']:,.2f}`
        """)

    st.markdown("---")
    outcome = st.selectbox("Phase 1 Result?", ["Select...", "Pass", "Fail"], key="o1")
    if outcome == "Pass":
        st.success(f"Move to Phase 2. Cost incurred: ${p1_data['cex_loss_total']:,.2f}")
    elif outcome == "Fail":
        refund = (acct_size * 0.08) / ratio_p1 # Approx win
        st.error(f"Account Failed. Refund calculated: +${refund:,.2f}. Net: {refund - fee - p1_data['cex_loss_total']}")

with tab2:
    st.subheader("Phase 2: Verification")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""
        ### 🟢 Prop Account Setup
        * **Position Size:** `${p2_data['prop_size']:,.0f}`
        * **Target Net Profit:** ${p2_target:,.0f}
        * **Actual Gross Target:** `${p2_data['gross_needed']:,.2f}`
        """)
    with c2:
        st.markdown(f"""
        ### 🔴 CEX Account Setup
        * **Position Size:** `${p2_data['cex_size']:,.0f}`
        * **Expected Loss:** `${p2_data['cex_loss_total']:,.2f}`
        """)

with tab3:
    st.subheader("💰 The Real Numbers")
    
    df = pd.DataFrame({
        "Item": ["Evaluation Fee", "Phase 1 Cost (Hedge+Fees)", "Phase 2 Cost (Hedge+Fees)", "Total Investment"],
        "Amount": [fee, p1_data['cex_loss_total'], p2_data['cex_loss_total'], total_sunk]
    })
    st.table(df)
    
    st.markdown(f"### 💡 ROI Analysis")
    payout = (acct_size * 0.05) * 0.90
    st.write(f"First Payout (Net 5%): **${payout:,.2f}**")
    st.metric("Net Profit (Payout - Total Investment)", f"${payout - total_sunk:,.2f}")

