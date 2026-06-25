import streamlit as st
import pandas as pd

st.set_page_config(layout="wide", page_title="Hedge Sizing Dashboard")

st.markdown("""
    <style>
    .metric-box {
        background-color: #1e1e1e; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 4px solid #0b57d0;
    }
    .warning-text { color: #ff4b4b; font-weight: bold; }
    .success-text { color: #00c853; font-weight: bold; }
    .info-box {
        background-color: #1e293b; padding: 15px; border-radius: 10px; border-left: 4px solid #38bdf8; margin-top: 10px; margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ Prop vs CEX Hedge Sizing Engine")
st.markdown("Dynamic mathematical sizing for perfect risk extraction.")

with st.sidebar:
    st.header("⚙️ Account Settings")
    
    tier_str = st.selectbox("Funded Account Tier", ["10k", "50k", "100k"], index=0)
    tier_value = int(tier_str.replace("k", "000"))
    
    # 4% Legacy Rule Max Daily Loss
    max_daily_loss = tier_value * 0.04 
    # FIXED: Default Breakout legacy overall drawdown is 6%
    max_dd_percent = st.number_input("Max Overall Drawdown (%)", min_value=1.0, value=6.0, step=1.0)
    account_blow_level = tier_value * (1.0 - (max_dd_percent / 100.0))
    
    prop_balance = st.number_input("Current Prop Balance ($)", min_value=0.0, value=9719.0, step=10.0)
    cex_balance = st.number_input("Current Bitunix Balance ($)", min_value=0.0, value=1500.0, step=10.0)
    
    prev_cex_pnl = st.number_input("Previous CEX PnL (Running Total $)", value=-60.0, step=10.0, 
                                   help="Enter your running total profit/loss on Bitunix for this specific prop account. Use negatives for losses.")
    
    st.markdown("---")
    st.header("🧠 Strategy Selector")
    
    strategy_options = [
        "Drain / Payout Focus (Custom RR) [DYNAMIC]",
        "High Win-Rate Payout (Asymmetric 3:1)",
        "Aggressive Cash Drain (1:1)",
        "Standard Breakeven (1:2 RR)"
    ]
    selected_strategy = st.selectbox("Select Strategy Profile", strategy_options)
    
    target_net_profit = 0
    if "High Win-Rate" in selected_strategy:
        target_net_profit = st.slider("Target Net Profit (If Prop Wins)", 10, 500, 100, step=10)

is_underwater = prop_balance <= tier_value
dead_zone_amt = max(0.0, tier_value - prop_balance)

if is_underwater:
    st.sidebar.markdown(f"🚨 **DEAD ZONE:** You are **${dead_zone_amt:,.2f}** underwater.")
else:
    buffer_amt = prop_balance - tier_value
    st.sidebar.markdown(f"✅ **BUFFER:** You have a **${buffer_amt:,.2f}** safety buffer.")

st.subheader("🎯 Trade Parameters")
col1, col2, col3, col4 = st.columns(4)

with col1:
    prop_risk_chunk = st.number_input("Prop Risk Per Trade ($)", min_value=10.0, value=350.0, step=10.0)
with col2:
    cmp_price = st.number_input("Entry Price (CMP)", min_value=0.0001, value=65000.0, format="%.4f")
with col3:
    prop_sl_price = st.number_input("Prop Stop Loss Price", min_value=0.0001, value=64000.0, format="%.4f")
with col4:
    cex_direction = st.selectbox("CEX Direction (Hedge)", ["Short", "Long"])

if prop_risk_chunk > max_daily_loss:
    st.error(f"⚠️ WARNING: Your risk (${prop_risk_chunk}) exceeds the 4% daily limit (${max_daily_loss})!")

prop_rr = 3.0 # Default fallback
if "Drain" in selected_strategy:
    st.markdown("---")
    st.markdown("### 🎛️ Dynamic Target Planner")
    
    # 1. Show minimum target to escape dead zone
    st.markdown(f"""
    <div class="info-box">
        💡 <b>Minimum to escape Dead Zone:</b> Your Prop Take Profit must be at least <b>${dead_zone_amt:,.2f}</b> to trigger ANY payout. Everything above this is split 90/10.
    </div>
    """, unsafe_allow_html=True)
    
    # 2. Show RR needed to recover the historical hole
    if prev_cex_pnl < 0:
        hole_to_cover = abs(prev_cex_pnl)
        if prop_balance <= tier_value:
            # Underwater: we extract cash on loss. CEX_TP = CEX_SL / 3. 
            # To get CEX_TP >= hole, CEX_SL >= 3 * hole.
            # CEX_SL = net_payout = (Prop_TP - DZ) * 0.9.
            req_cex_sl = hole_to_cover * 3.0
            req_prop_tp = (req_cex_sl / 0.90) + dead_zone_amt
            req_rr = req_prop_tp / prop_risk_chunk
            st.success(f"🎯 **Hole Recovery:** To extract enough cash to wipe out your -${hole_to_cover:,.2f} hole in ONE trade if Prop LOSES, you need a Prop Target of **{req_rr:.1f}x RR**.")
        else:
            # In Profit: we extract cash on win or loss.
            # Win Net Profit = Prop_TP * 0.15
            req_tp_win = hole_to_cover / 0.15
            req_rr_win = req_tp_win / prop_risk_chunk
            # Loss Net Profit = (Prop_TP * 0.75) / 3 = Prop_TP * 0.25
            req_tp_loss = hole_to_cover / 0.25
            req_rr_loss = req_tp_loss / prop_risk_chunk
            st.success(f"🎯 **Hole Recovery:** To wipe out your -${hole_to_cover:,.2f} hole if Prop WINS, you need **{req_rr_win:.1f}x RR**. If Prop LOSES, you need **{req_rr_loss:.1f}x RR**.")
    
    # 3. Interactive Slider for Target
    prop_rr = st.slider("Select Prop Take Profit (RR Multiplier)", min_value=1.0, max_value=15.0, value=3.0, step=0.1, help="Slide to see how holding for a larger payout impacts your net profit in the Outcome Matrix below.")

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

# Strategy 2: Drain / Payout Focus (Custom RR Dynamic Scaler)
elif "Drain" in selected_strategy:
    prop_sl_dollar = prop_risk_chunk
    prop_tp_dollar = prop_risk_chunk * prop_rr
    
    gross_payout = prop_tp_dollar - dead_zone_amt
    net_payout = max(0.0, gross_payout * 0.90)
    
    if prop_balance <= tier_value:
        # Match CEX SL perfectly to the net payout for a $0 Breakeven
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

sim_balance = prop_balance
total_drain_profit = 0.0
trades_to_blow = 0

while sim_balance > account_blow_level:
    trades_to_blow += 1
    sim_dead_zone = max(0.0, tier_value - sim_balance)
    
    if "High Win-Rate" in selected_strategy:
        s_p_tp = prop_risk_chunk / 3.0
        s_g_pay = s_p_tp - sim_dead_zone
        s_n_pay = max(0.0, s_g_pay * 0.90)
        s_c_sl = max(0.0, s_n_pay - target_net_profit)
        step_cex_tp = s_c_sl * 3.0
    elif "Drain" in selected_strategy:
        s_p_tp = prop_risk_chunk * prop_rr # Uses the custom slider value
        if sim_balance <= tier_value:
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

st.subheader("🔮 Immediate Trade Outcomes")

def fmt_money(val):
    return f"{'-$' if val < 0 else '+$'}{abs(val):,.2f}"

scen1_prop_pnl = -prop_sl_dollar
scen1_cex_pnl = cex_tp_dollar
scen1_net = scen1_prop_pnl + scen1_cex_pnl + prev_cex_pnl

scen2_gross_prop = prop_tp_dollar
scen2_payout = max(0.0, (scen2_gross_prop - dead_zone_amt) * 0.90)
scen2_cex_pnl = -cex_sl_dollar
scen2_net = scen2_payout + scen2_cex_pnl + prev_cex_pnl

outcome_data = [
    {
        "Scenario": "📉 The Drain (Prop SL / CEX TP)",
        "Prop Balance Change": f"-${prop_sl_dollar:.2f}",
        "CEX PnL (Wallet)": f"+${cex_tp_dollar:.2f}",
        "Total Net Cash (Incl Prev PnL)": fmt_money(scen1_net)
    },
    {
        "Scenario": "📈 The Payout (Prop TP / CEX SL)",
        "Prop Balance Change": f"+${prop_tp_dollar:.2f}",
        "CEX PnL (Wallet)": f"-${cex_sl_dollar:.2f}",
        "Total Net Cash (Incl Prev PnL)": fmt_money(scen2_net)
    }
]
st.table(pd.DataFrame(outcome_data))

st.markdown("---")
st.subheader("🩸 Full Account Drain Projection (100% Loss Rate)")

final_drain_net = total_drain_profit + prev_cex_pnl
pnl_color = "success-text" if final_drain_net > 0 else "warning-text"

st.markdown(f"""
<div class="metric-box">
    If you lose every single trade from your current balance of <b>${prop_balance:,.2f}</b> until the account is completely blown (at the 6% limit of ${account_blow_level:,.2f}), the math dynamically extracts cash on every single loss.
    <br><br>
    💥 <b>Trades to Blow Account:</b> {trades_to_blow} consecutive losses<br>
    💰 <b>Total Bitunix Cash Extracted (From Current Balance):</b> <span class="success-text">+${total_drain_profit:,.2f}</span><br>
    📊 <b>FINAL NET CASH (Including Previous ${prev_cex_pnl:.2f} PnL):</b> <span class="{pnl_color}">{fmt_money(final_drain_net)}</span>
</div>
""", unsafe_allow_html=True)

if cex_leverage > 100:
    st.error(f"🚨 BITUNIX LIQUIDATION WARNING: Required leverage is {cex_leverage:.1f}x. You must deposit more funds or reduce Prop Risk.")
elif cex_leverage > 50:
    st.warning(f"⚠️ HIGH LEVERAGE: Required leverage is {cex_leverage:.1f}x. Ensure your Bitunix isolated margin can handle the stop loss.")
