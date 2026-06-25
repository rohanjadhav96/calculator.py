import streamlit as st
import pandas as pd

# Configure page layout and visual theme
st.set_page_config(layout="wide", page_title="Hedge Sizing Dashboard")

# Custom CSS for better UI appearance
st.markdown("""
    <style>
    .metric-box {
        background-color: #1e1e1e; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 4px solid #0b57d0;
    }
    .warning-text { color: #ff4b4b; font-weight: bold; }
    .success-text { color: #00c853; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ Prop vs CEX Hedge Sizing Engine")
st.markdown("Dynamic mathematical sizing for perfect risk extraction.")

# ==========================================
# SIDEBAR CONFIGURATION
# ==========================================
with st.sidebar:
    st.header("⚙️ Account Settings")
    
    tier_str = st.selectbox("Funded Account Tier", ["10k", "50k", "100k"], index=0)
    tier_value = int(tier_str.replace("k", "000"))
    
    # 4% Legacy Rule Max Daily Loss
    max_daily_loss = tier_value * 0.04 
    max_dd_percent = st.number_input("Max Overall Drawdown (%)", min_value=1.0, value=8.0, step=1.0)
    account_blow_level = tier_value * (1.0 - (max_dd_percent / 100.0))
    
    prop_balance = st.number_input("Current Prop Balance ($)", min_value=0.0, value=10259.0, step=10.0)
    cex_balance = st.number_input("Current Bitunix Balance ($)", min_value=0.0, value=1500.0, step=10.0)
    
    st.markdown("---")
    st.header("🧠 Strategy Selector")
    
    strategy_options = [
        "Drain / Payout Focus (1:3 RR) [DYNAMIC]",
        "High Win-Rate Payout (Asymmetric 3:1)",
        "Aggressive Cash Drain (1:1)",
        "Standard Breakeven (1:2 RR)"
    ]
    selected_strategy = st.selectbox("Select Strategy Profile", strategy_options)
    
    target_net_profit = 0
    if "High Win-Rate" in selected_strategy:
        target_net_profit = st.slider("Target Net Profit (If Prop Wins)", 10, 500, 150, step=10)

# ==========================================
# DEAD ZONE CALCULATION
# ==========================================
is_underwater = prop_balance < tier_value
dead_zone_amt = max(0.0, tier_value - prop_balance)

if is_underwater:
    st.sidebar.markdown(f"🚨 **DEAD ZONE:** You are **${dead_zone_amt:,.2f}** underwater.")
else:
    buffer_amt = prop_balance - tier_value
    st.sidebar.markdown(f"✅ **BUFFER:** You have a **${buffer_amt:,.2f}** safety buffer.")

# ==========================================
# MAIN DASHBOARD INPUTS
# ==========================================
st.subheader("🎯 Trade Parameters")
col1, col2, col3, col4 = st.columns(4)

with col1:
    prop_risk_chunk = st.number_input("Prop Risk Per Trade ($)", min_value=10.0, value=300.0, step=10.0)
with col2:
    cmp_price = st.number_input("Entry Price (CMP)", min_value=0.0001, value=65000.0, format="%.4f")
with col3:
    prop_sl_price = st.number_input("Prop Stop Loss Price", min_value=0.0001, value=64000.0, format="%.4f")
with col4:
    cex_direction = st.selectbox("CEX Direction (Hedge)", ["Short", "Long"])

if prop_risk_chunk > max_daily_loss:
    st.error(f"⚠️ WARNING: Your risk (${prop_risk_chunk}) exceeds the 4% daily limit (${max_daily_loss})!")

# ==========================================
# CORE MATH ENGINE
# ==========================================
price_delta = abs(cmp_price - prop_sl_price)
if price_delta <= 0:
    st.warning("Please enter a valid Entry and Stop Loss price to calculate.")
    st.stop()

# Strategy 1: High Win-Rate Payout (Asymmetric 3:1)
if "High Win-Rate" in selected_strategy:
    prop_sl_dollar = prop_risk_chunk
    prop_tp_dollar = prop_risk_chunk / 3.0
    
    gross_payout = prop_tp_dollar - dead_zone_amt
    net_payout = max(0.0, gross_payout * 0.90)
    
    cex_sl_dollar = max(0.0, net_payout - target_net_profit)
    cex_tp_dollar = cex_sl_dollar * 3.0 

# Strategy 2: Drain / Payout Focus (1:3 RR) [DYNAMIC SCALER]
elif "Drain" in selected_strategy:
    prop_sl_dollar = prop_risk_chunk
    prop_tp_dollar = prop_risk_chunk * 3.0
    
    if prop_balance < tier_value:
        gross_payout = prop_tp_dollar - dead_zone_amt
        net_payout = max(0.0, gross_payout * 0.90)
        cex_sl_dollar = net_payout if net_payout > 0 else (prop_risk_chunk * 1.5) 
    else:
        # Throttle CEX SL when in profit to generate massive net returns on Payout
        cex_sl_dollar = prop_tp_dollar * 0.75 
        
    cex_tp_dollar = cex_sl_dollar / 3.0 

# Strategy 3: Aggressive Cash Drain (1:1)
elif "Aggressive" in selected_strategy:
    prop_sl_dollar = prop_risk_chunk
    prop_tp_dollar = prop_risk_chunk
    
    cex_sl_dollar = prop_risk_chunk * 0.90
    cex_tp_dollar = prop_risk_chunk * 0.90

# Strategy 4: Perfect Breakeven
else:
    prop_sl_dollar = prop_risk_chunk
    prop_tp_dollar = prop_risk_chunk * 2.0
    
    gross_payout = prop_tp_dollar - dead_zone_amt
    net_payout = max(0.0, gross_payout * 0.90)
    
    cex_sl_dollar = net_payout if net_payout > 0 else (prop_risk_chunk * 0.75)
    cex_tp_dollar = cex_sl_dollar / 2.0

# Calculate Quantities
prop_qty = prop_tp_dollar / price_delta if price_delta > 0 else 0
cex_qty = cex_sl_dollar / price_delta if price_delta > 0 else 0

# Calculate Hedge Ratio
hedge_ratio = cex_qty / prop_qty if prop_qty > 0 else 0

# ==========================================
# UNIVERSAL TARGET PRICE CALCULATOR
# ==========================================
prop_direction = "Long" if cex_direction == "Short" else "Short"

if prop_direction == "Long":
    prop_sl_target = cmp_price - price_delta
    prop_tp_target = cmp_price + (prop_tp_dollar / prop_qty) if prop_qty > 0 else cmp_price
else:
    prop_sl_target = cmp_price + price_delta
    prop_tp_target = cmp_price - (prop_tp_dollar / prop_qty) if prop_qty > 0 else cmp_price

if cex_direction == "Long":
    cex_sl_target = cmp_price - (cex_sl_dollar / cex_qty) if cex_qty > 0 else cmp_price
    cex_tp_target = cmp_price + (cex_tp_dollar / cex_qty) if cex_qty > 0 else cmp_price
else:
    cex_sl_target = cmp_price + (cex_sl_dollar / cex_qty) if cex_qty > 0 else cmp_price
    cex_tp_target = cmp_price - (cex_tp_dollar / cex_qty) if cex_qty > 0 else cmp_price

cex_notional = cex_qty * cmp_price
cex_leverage = cex_notional / cex_balance if cex_balance > 0 else 0

# ==========================================
# UI RENDERING: EXECUTION PLAN
# ==========================================
st.markdown("---")
st.markdown(f"### 📋 Execution Plan (Hedge Ratio: `{hedge_ratio:.2f}x`)")
st.caption(f"A {hedge_ratio:.2f}x ratio means your Bitunix position size is exactly {hedge_ratio*100:.1f}% the size of your Prop position.")

exec_data = [
    {
        "Platform": "Prop Account",
        "Direction": prop_direction,
        "Quantity (Units)": f"{prop_qty:.4f}",
        "Stop Loss Price": f"{prop_sl_target:.4f}",
        "Take Profit Price": f"{prop_tp_target:.4f}",
        "Risk Amount": f"-${prop_sl_dollar:.2f}",
        "Leverage": "N/A"
    },
    {
        "Platform": "Bitunix (CEX)",
        "Direction": cex_direction,
        "Quantity (Units)": f"{cex_qty:.4f}",
        "Stop Loss Price": f"{cex_sl_target:.4f}",
        "Take Profit Price": f"{cex_tp_target:.4f}",
        "Risk Amount": f"-${cex_sl_dollar:.2f}",
        "Leverage": f"{cex_leverage:.1f}x"
    }
]
st.table(pd.DataFrame(exec_data))

# ==========================================
# SIMULATION: FULL ACCOUNT DRAIN
# ==========================================
sim_balance = prop_balance
total_drain_profit = 0.0
trades_to_blow = 0

while sim_balance > account_blow_level:
    trades_to_blow += 1
    sim_dead_zone = max(0.0, tier_value - sim_balance)
    
    # Calculate CEX TP for this specific step in the simulation
    if "High Win-Rate" in selected_strategy:
        s_p_tp = prop_risk_chunk / 3.0
        s_g_pay = s_p_tp - sim_dead_zone
        s_n_pay = max(0.0, s_g_pay * 0.90)
        s_c_sl = max(0.0, s_n_pay - target_net_profit)
        step_cex_tp = s_c_sl * 3.0
    elif "Drain" in selected_strategy:
        s_p_tp = prop_risk_chunk * 3.0
        if sim_balance < tier_value:
            s_g_pay = s_p_tp - sim_dead_zone
            s_n_pay = max(0.0, s_g_pay * 0.90)
            s_c_sl = s_n_pay if s_n_pay > 0 else (prop_risk_chunk * 1.5)
        else:
            s_c_sl = s_p_tp * 0.75
        step_cex_tp = s_c_sl / 3.0
    elif "Aggressive" in selected_strategy:
        step_cex_tp = prop_risk_chunk * 0.90
    else:
        s_p_tp = prop_risk_chunk * 2.0
        s_g_pay = s_p_tp - sim_dead_zone
        s_n_pay = max(0.0, s_g_pay * 0.90)
        s_c_sl = s_n_pay if s_n_pay > 0 else (prop_risk_chunk * 0.75)
        step_cex_tp = s_c_sl / 2.0
        
    total_drain_profit += step_cex_tp
    sim_balance -= prop_risk_chunk

# ==========================================
# UI RENDERING: OUTCOMES MATRIX
# ==========================================
st.subheader("🔮 Immediate Trade Outcomes")

scen1_prop_pnl = -prop_sl_dollar
scen1_cex_pnl = cex_tp_dollar
scen1_net = scen1_prop_pnl + scen1_cex_pnl

scen2_gross_prop = prop_tp_dollar
scen2_payout = max(0.0, (scen2_gross_prop - dead_zone_amt) * 0.90)
scen2_cex_pnl = -cex_sl_dollar
scen2_net = scen2_payout + scen2_cex_pnl

outcome_data = [
    {
        "Scenario": "📉 The Drain (Prop SL / CEX TP)",
        "Prop Balance Change": f"-${prop_sl_dollar:.2f}",
        "CEX PnL (Wallet)": f"+${cex_tp_dollar:.2f}",
        "Total Net Cash": f"${scen1_net:.2f}"
    },
    {
        "Scenario": "📈 The Payout (Prop TP / CEX SL)",
        "Prop Balance Change": f"+${prop_tp_dollar:.2f}",
        "CEX PnL (Wallet)": f"-${cex_sl_dollar:.2f}",
        "Total Net Cash": f"${scen2_net:.2f} (After 90% Split)"
    }
]
st.table(pd.DataFrame(outcome_data))

st.markdown("---")
st.subheader("🩸 Full Account Drain Projection (100% Loss Rate)")
st.markdown(f"""
<div class="metric-box">
    If you lose every single trade from your current balance of <b>${prop_balance:,.2f}</b> until the account is completely blown (at the ${account_blow_level:,.2f} limit), the math dynamically extracts cash on every single loss.
    <br><br>
    💥 <b>Trades to Blow Account:</b> {trades_to_blow} consecutive losses<br>
    💰 <b>Total Bitunix Cash Extracted:</b> <span class="success-text">+${total_drain_profit:,.2f}</span>
</div>
""", unsafe_allow_html=True)

if cex_leverage > 100:
    st.error(f"🚨 BITUNIX LIQUIDATION WARNING: Required leverage is {cex_leverage:.1f}x. You must deposit more funds or reduce Prop Risk.")
elif cex_leverage > 50:
    st.warning(f"⚠️ HIGH LEVERAGE: Required leverage is {cex_leverage:.1f}x. Ensure your Bitunix isolated margin can handle the stop loss.")
