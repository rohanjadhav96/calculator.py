import streamlit as st
import pandas as pd

# Page Config
st.set_page_config(page_title="Breakout Hedge Architect", layout="wide", page_icon="⚖️")

# Custom CSS for dark mode aesthetics
st.markdown("""
<style>
    .stMetric {
        background-color: #1E1E1E;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #333;
    }
    .big-font {
        font-size: 20px !important;
        font-weight: bold;
    }
    .success-text { color: #00FF7F; }
    .danger-text { color: #FF4B4B; }
</style>
""", unsafe_allow_html=True)

st.title("⚖️ Prop Firm Arbitrage Calculator")
st.markdown("### Strategy: Breakout 2-Step (Classic)")

# --- SIDEBAR INPUTS ---
st.sidebar.header("⚙️ Account Parameters")

with st.sidebar.expander("1. Prop Firm Rules", expanded=True):
    account_size = st.number_input("Account Size ($)", value=50000, step=10000)
    fee = st.number_input("Evaluation Fee ($)", value=450)
    
    st.markdown("---")
    st.markdown("**Targets & Limits**")
    p1_target_pct = st.slider("Phase 1 Target (%)", 1.0, 20.0, 5.0, 0.5) / 100
    p2_target_pct = st.slider("Phase 2 Target (%)", 1.0, 20.0, 10.0, 0.5) / 100
    max_dd_pct = st.slider("Max Drawdown (%)", 1.0, 15.0, 8.0, 0.5) / 100
    payout_share = st.slider("Payout Share (%)", 50, 100, 90, 5) / 100

with st.sidebar.expander("2. Hedge Ratios (Prop : CEX)", expanded=True):
    st.info("Higher Ratio = Less CEX capital needed, but harder to 'Refund' if you fail.")
    ratio_p1 = st.number_input("Phase 1 Ratio", value=5.8, step=0.1, help="e.g. 5.8 means 5.8 lots on Prop for every 1 lot on CEX.")
    ratio_p2 = st.number_input("Phase 2 Ratio", value=3.2, step=0.1)
    
    st.markdown("---")
    st.markdown("**Funded Phase Strategy**")
    st.caption("In funded stage, we usually reverse the ratio (Risk more on CEX) or balance it to guarantee payout.")
    ratio_funded = st.number_input("Funded Ratio (Prop : CEX)", value=0.75, step=0.05, help="0.75 means you risk LESS on Prop than CEX to secure the payout.")

# --- CALCULATIONS ---

# Dollar Values
p1_target = account_size * p1_target_pct
p2_target = account_size * p2_target_pct
max_loss_amt = account_size * max_dd_pct

# Phase 1 Math
p1_cost_to_pass = p1_target / ratio_p1  # Loss on CEX
p1_fail_gross_win = max_loss_amt / ratio_p1 # Win on CEX
p1_fail_net = p1_fail_gross_win - fee # Net profit/loss if prop acc blows

# Phase 2 Math
p2_cost_to_pass = p2_target / ratio_p2
p2_fail_gross_win = max_loss_amt / ratio_p2
# If we fail P2, we gained the P2 CEX win, but we lost the Fee AND the cost to pass P1.
p2_fail_net = p2_fail_gross_win - p1_cost_to_pass - fee 

# Total Investment to get Funded
total_sunk_cost = p1_cost_to_pass + p2_cost_to_pass + fee

# Funded Phase Math (Scenario: Making 5% on Prop Account to get first payout)
funded_target_profit = account_size * 0.05 # e.g. $2500
funded_cex_loss = funded_target_profit / ratio_funded # Amount lost on CEX to gain that profit on Prop
prop_payout = funded_target_profit * payout_share
net_profit_funded = prop_payout - funded_cex_loss

# --- DASHBOARD LAYOUT ---

# Row 1: The "Fail Safe" Check
st.subheader("1. The Safety Net Test")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Max Drawdown Limit", f"${max_loss_amt:,.0f}")

with col2:
    status_p1 = "✅ PROFITABLE FAIL" if p1_fail_net > 0 else "⚠️ LOSS IF FAIL"
    st.metric("Phase 1: If You Fail", f"${p1_fail_net:,.2f}", delta=status_p1, delta_color="off" if p1_fail_net < 0 else "normal")
    st.caption(f"CEX Win (${p1_fail_gross_win:,.0f}) - Fee (${fee})")

with col3:
    status_p2 = "✅ PROFITABLE FAIL" if p2_fail_net > 0 else "⚠️ LOSS IF FAIL"
    st.metric("Phase 2: If You Fail", f"${p2_fail_net:,.2f}", delta=status_p2, delta_color="off" if p2_fail_net < 0 else "normal")
    st.caption(f"CEX Win - P1 Cost - Fee")

st.markdown("---")

# Row 2: Investment Required
st.subheader("2. Cost to Get Funded")
c1, c2 = st.columns([1, 2])

with c1:
    st.write(f"**Phase 1 CEX Loss:** ${p1_cost_to_pass:,.2f}")
    st.write(f"**Phase 2 CEX Loss:** ${p2_cost_to_pass:,.2f}")
    st.write(f"**Evaluation Fee:** ${fee:,.2f}")
    st.markdown("#### Total Risk: ")
    st.markdown(f"<h2 style='color: #FF4B4B'>${total_sunk_cost:,.2f}</h2>", unsafe_allow_html=True)
    st.caption("This is the cash required in your CEX account to hedge successfully.")

with c2:
    # Visualization of Costs
    cost_data = pd.DataFrame({
        'Stage': ['Fee', 'Phase 1 Hedge', 'Phase 2 Hedge'],
        'Cost': [fee, p1_cost_to_pass, p2_cost_to_pass]
    })
    st.bar_chart(cost_data, x='Stage', y='Cost', color="#FF4B4B")

st.markdown("---")

# Row 3: The Reward (Funded)
st.subheader("3. Funded Phase Simulation")
st.markdown("If you achieve a **5% profit** on the funded account ($2,500) using a **0.75:1 ratio**:")

f1, f2, f3 = st.columns(3)
with f1:
    st.metric("Prop Payout (90%)", f"${prop_payout:,.2f}")
with f2:
    st.metric("CEX Hedge Loss", f"-${funded_cex_loss:,.2f}")
with f3:
    final_profit = net_profit_funded
    st.metric("Net Profit (First Month)", f"${final_profit:,.2f}")

# ROI Calculation
roi = (final_profit / total_sunk_cost) * 100
st.info(f"💡 **ROI Analysis:** If you pass and get one payout, you make **{roi:.1f}%** return on your total sunk costs (${total_sunk_cost:,.0f}).")

# --- WARNING SECTION ---
with st.expander("🚨 CRITICAL WARNING: Daily Drawdown"):
    st.error(f"""
    **Do NOT ignore the 5% Daily Drawdown Rule.**
    
    Your max total drawdown is {max_dd_pct*100}%, but your DAILY limit is likely 5%.
    
    If you use the hedging math based on the full {max_dd_pct*100}% stop loss, but the market moves against you by 5% in a SINGLE day, 
    you will lose the Prop account instantly, but your CEX trade won't have hit the full target profit yet.
    
    **Result:** You lose the Prop Account AND you don't make enough on CEX to cover the fee.
    
    **Solution:** Calculate your position sizes based on **4.5%** Max Loss, not {max_dd_pct*100}%, to be safe.
    """)
