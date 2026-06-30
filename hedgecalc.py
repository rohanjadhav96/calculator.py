import streamlit as st
import pandas as pd

st.set_page_config(layout="wide", page_title="Hedge Sizing Dashboard")

# --- SESSION STATE INITIALIZATION (For Interactive Tracking) ---
if "st_account_phase" not in st.session_state:
    st.session_state.st_account_phase = "Evaluation Stage (Milking Evals)"
if "st_prop_balance" not in st.session_state:
    st.session_state.st_prop_balance = 25000.0
if "st_prev_cex_pnl" not in st.session_state:
    st.session_state.st_prev_cex_pnl = 0.0
if "st_trade_logs" not in st.session_state:
    st.session_state.st_trade_logs = []
if "st_last_tier" not in st.session_state:
    st.session_state.st_last_tier = 25000

st.markdown("""
    <style>
    .metric-box { background-color: #1e1e1e; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 4px solid #0b57d0; }
    .warning-text { color: #ff4b4b; font-weight: bold; }
    .success-text { color: #00c853; font-weight: bold; }
    .info-box { background-color: #1e293b; padding: 15px; border-radius: 10px; border-left: 4px solid #38bdf8; margin-top: 10px; margin-bottom: 10px; }
    .eval-box { background-color: #2d1b2e; padding: 15px; border-radius: 10px; border-left: 4px solid #d946ef; margin-bottom: 10px; }
    .log-box { background-color: #0f172a; padding: 10px; border-radius: 5px; font-family: monospace; font-size: 14px; margin-bottom: 5px; border-left: 3px solid #64748b;}
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ Prop vs CEX Hedge Sizing Engine")

# --- MASTER PHASE & TYPE TOGGLES ---
col_phase, col_type = st.columns(2)
with col_phase:
    account_phase = st.radio("Select Account Phase", ["Funded Stage (Payout Focus)", "Evaluation Stage (Milking Evals)"], horizontal=True, key="st_account_phase")
with col_type:
    account_type = st.radio("Select Account Type", ["Classic Rules", "Pro Rules"], horizontal=True)

# Define static pricing and rules matrix
pricing_matrix = {
    "Classic Rules": {"10k": 102.0, "25k": 253.0, "50k": 470.0, "100k": 850.0},
    "Pro Rules": {"10k": 78.0, "25k": 180.0, "50k": 366.0, "100k": 700.0}
}

# Apply default overall drawdown values based on Account Type
default_dd = 6.0 if account_type == "Classic Rules" else 5.0
default_target_pct = 0.10 if account_type == "Classic Rules" else 0.12

with st.sidebar:
    st.header("⚙️ Account Settings")
    tier_str = st.selectbox("Funded Account Tier", ["10k", "25k", "50k", "100k"], index=1)
    tier_value = int(tier_str.replace("k", "000"))
    
    # Auto-reset balances if user changes Tier
    if tier_value != st.session_state.st_last_tier:
        st.session_state.st_prop_balance = float(tier_value)
        st.session_state.st_prev_cex_pnl = 0.0
        st.session_state.st_trade_logs = []
        st.session_state.st_last_tier = tier_value
        st.rerun()

    max_daily_loss = tier_value * 0.03 
    max_dd_percent = st.number_input("Max Overall Drawdown (%)", min_value=1.0, value=default_dd, step=1.0)
    account_blow_level = tier_value * (1.0 - (max_dd_percent / 100.0))
    
    prop_balance = st.number_input("Current Prop Balance ($)", min_value=0.0, step=10.0, key="st_prop_balance")
    cex_balance = st.number_input("Current Bitunix Balance ($)", min_value=0.0, value=4000.0, step=10.0)
    
    if account_phase == "Evaluation Stage (Milking Evals)":
        st.markdown("---")
        st.header("🎟️ Challenge Details")
        standard_price = pricing_matrix[account_type].get(tier_str, 100.0)
        challenge_fee = st.number_input("Challenge Fee Paid ($)", min_value=0.0, value=standard_price, step=5.0)
        target_to_pass = tier_value * default_target_pct
        st.info(f"Target to Pass ({int(default_target_pct*100)}%): **${target_to_pass:,.2f}**")
        
        # PnL input acts as a tracker in Eval mode too now (tracks extracted cash)
        prev_cex_pnl = st.number_input("Extracted Cash / Sunk Costs ($)", step=10.0, key="st_prev_cex_pnl")
    else:
        prev_cex_pnl = st.number_input("Previous CEX PnL (Running Total $)", step=10.0, key="st_prev_cex_pnl")
    
    st.header("⚖️ Position Limits")
    cex_max_qty = st.number_input("Max Bitunix Size (Units)", min_value=0.0, value=450.0, step=10.0)
    prop_leverage = st.number_input("Prop Account Max Leverage", min_value=1.0, value=50.0, step=1.0)
    
    st.header("🧠 Strategy Selector")
    strategy_options = [
        "Manual Hedge Ratio Selection [CUSTOM]",
        "Drain / Payout Focus (Custom RR) [DYNAMIC]",
        "High Win-Rate Payout (Asymmetric 3:1)",
        "Aggressive Cash Drain (1:1)",
        "Standard Breakeven (1:2 RR)"
    ]
    selected_strategy = st.selectbox("Select Strategy Profile", strategy_options)
    
    custom_hedge_ratio = 1.0
    if selected_strategy == "Manual Hedge Ratio Selection [CUSTOM]":
        custom_hedge_ratio = st.slider("Select Custom Hedge Ratio (CEX Qty / Prop Qty)", min_value=0.10, max_value=3.00, value=0.41, step=0.01)
    
    target_net_profit = 0
    if "High Win-Rate" in selected_strategy and account_phase == "Funded Stage (Payout Focus)":
        target_net_profit = st.slider("Target Net Profit (If Prop Wins)", 10, 500, 100, step=10)

is_underwater = prop_balance <= tier_value
dead_zone_amt = max(0.0, tier_value - prop_balance)

st.subheader("🎯 Trade Parameters")
col1, col2, col3, col4 = st.columns(4)

with col1: 
    default_risk = tier_value * 0.025 if account_phase == "Evaluation Stage (Milking Evals)" else tier_value * 0.035
    # Automatically bound the suggested risk if the account is near blow level
    suggested_risk = min(default_risk, prop_balance - account_blow_level)
    if suggested_risk < 10.0: suggested_risk = 10.0
    prop_risk_chunk = st.number_input("Prop Risk Per Trade ($)", min_value=1.0, value=float(suggested_risk), step=10.0)
with col2: cmp_price = st.number_input("Entry Price (CMP)", min_value=0.0001, value=62.3500, format="%.4f")
with col3: prop_sl_price = st.number_input("Prop Stop Loss Price", min_value=0.0001, value=60.0000, format="%.4f")
with col4: cex_direction = st.selectbox("CEX Direction (Hedge)", ["Short", "Long"])

if prop_risk_chunk > max_daily_loss:
    st.error(f"⚠️ WARNING: Your risk (${prop_risk_chunk}) exceeds the daily limit (${max_daily_loss})!")
if (prop_balance - prop_risk_chunk) < account_blow_level:
    st.error(f"🚨 FATAL WARNING: This risk (${prop_risk_chunk}) will blow the account! You only have ${(prop_balance - account_blow_level):.2f} drawdown left.")

prop_rr = 3.0 
if "Drain" in selected_strategy:
    if "prop_rr_slider" not in st.session_state: st.session_state.prop_rr_slider = 3.0
    def reset_rr(): st.session_state.prop_rr_slider = 3.0
    slide_col, btn_col = st.columns([3, 1])
    with slide_col: prop_rr = st.slider("Select Prop Take Profit (RR Multiplier)", min_value=1.0, max_value=15.0, key="prop_rr_slider", step=0.1)
    with btn_col: st.button("🔄 Reset to 3.0x", on_click=reset_rr, use_container_width=True)

price_delta = abs(cmp_price - prop_sl_price)
prop_qty_ideal = prop_risk_chunk / price_delta if price_delta > 0 else 0
prop_direction = "Long" if cex_direction == "Short" else "Short"

# --- CORE MATH LOGIC ---
if selected_strategy == "Manual Hedge Ratio Selection [CUSTOM]":
    cex_qty_ideal = prop_qty_ideal * custom_hedge_ratio
    if account_phase == "Evaluation Stage (Milking Evals)":
        prop_tp_dollar = target_to_pass - (prop_balance - tier_value) if (target_to_pass - (prop_balance - tier_value)) > 0 else prop_risk_chunk * 4.0
    else:
        prop_tp_dollar = prop_risk_chunk * 2.0  
    cex_sl_dollar = cex_qty_ideal * (prop_tp_dollar / prop_qty_ideal) if prop_qty_ideal > 0 else 0
    cex_tp_dollar = cex_qty_ideal * price_delta

elif "High Win-Rate" in selected_strategy:
    prop_tp_dollar = prop_risk_chunk / 3.0
    gross_payout = prop_tp_dollar - dead_zone_amt
    net_payout = max(0.0, gross_payout * 0.90) if account_phase == "Funded Stage (Payout Focus)" else 0.0
    cex_sl_dollar = max(0.0, net_payout - target_net_profit)
    cex_tp_dollar = cex_sl_dollar * 3.0 
    cex_qty_ideal = cex_sl_dollar / (prop_tp_dollar / prop_qty_ideal) if prop_qty_ideal > 0 else 0

elif "Drain" in selected_strategy:
    prop_tp_dollar = prop_risk_chunk * prop_rr
    gross_payout = prop_tp_dollar - dead_zone_amt
    net_payout = max(0.0, gross_payout * 0.90) if account_phase == "Funded Stage (Payout Focus)" else 0.0
    if account_phase == "Funded Stage (Payout Focus)":
        cex_sl_dollar = net_payout if net_payout > 0 else (prop_risk_chunk * 1.5) if prop_balance <= tier_value else prop_tp_dollar * 0.75 
    else:
        cex_sl_dollar = prop_tp_dollar * 0.40 
    cex_tp_dollar = cex_sl_dollar / 3.0 
    cex_qty_ideal = cex_sl_dollar / (prop_tp_dollar / prop_qty_ideal) if prop_qty_ideal > 0 else 0

elif "Aggressive" in selected_strategy:
    prop_tp_dollar = prop_risk_chunk
    cex_sl_dollar = prop_risk_chunk * 0.90
    cex_tp_dollar = prop_risk_chunk * 0.90
    cex_qty_ideal = cex_sl_dollar / price_delta if price_delta > 0 else 0

else:
    prop_tp_dollar = prop_risk_chunk * 2.0
    gross_payout = prop_tp_dollar - dead_zone_amt
    net_payout = max(0.0, gross_payout * 0.90) if account_phase == "Funded Stage (Payout Focus)" else 0.0
    cex_sl_dollar = net_payout if net_payout > 0 else (prop_risk_chunk * 0.75)
    cex_tp_dollar = cex_sl_dollar / 2.0
    cex_qty_ideal = cex_sl_dollar / (prop_tp_dollar / prop_qty_ideal) if prop_qty_ideal > 0 else 0

max_safe_cex_sl = cex_balance * 0.85
wallet_capped = False
if selected_strategy != "Manual Hedge Ratio Selection [CUSTOM]":
    if cex_sl_dollar > max_safe_cex_sl and max_safe_cex_sl > 0:
        scale_factor = max_safe_cex_sl / cex_sl_dollar
        cex_sl_dollar = max_safe_cex_sl
        cex_tp_dollar = cex_tp_dollar * scale_factor
        cex_qty_ideal = cex_qty_ideal * scale_factor
        wallet_capped = True

if prop_direction == "Long":
    prop_sl_target = cmp_price - price_delta
    prop_tp_target = cmp_price + (prop_tp_dollar / prop_qty_ideal) if prop_qty_ideal > 0 else cmp_price
    cex_sl_target = prop_tp_target
    cex_tp_target = prop_sl_target
else:
    prop_sl_target = cmp_price + price_delta
    prop_tp_target = cmp_price - (prop_tp_dollar / prop_qty_ideal) if prop_qty_ideal > 0 else cmp_price
    cex_sl_target = prop_tp_target
    cex_tp_target = prop_sl_target

cex_sl_distance = abs(cex_sl_target - cmp_price)
prop_max_qty = (prop_balance * prop_leverage) / cmp_price if cmp_price > 0 else 0
prop_qty = prop_max_qty if prop_qty_ideal > prop_max_qty else prop_qty_ideal
req_delta_cex = (cex_balance * 0.85) / (cex_max_qty * (cex_sl_distance / price_delta if price_delta > 0 else prop_rr)) if (cex_max_qty * (cex_sl_distance / price_delta if price_delta > 0 else prop_rr)) > 0 else 0
cex_qty = cex_max_qty if cex_qty_ideal > cex_max_qty and cex_max_qty > 0 else cex_qty_ideal

hedge_ratio = cex_qty / prop_qty if prop_qty > 0 else 0
actual_prop_sl_dollar = prop_qty * price_delta
actual_prop_tp_dollar = prop_qty * abs(prop_tp_target - cmp_price)
actual_cex_sl_dollar = cex_qty * cex_sl_distance
actual_cex_tp_dollar = cex_qty * abs(cex_tp_target - cmp_price)

exec_data = [
    {"Platform": "Prop Account", "Direction": prop_direction, "Qty (Units)": f"{prop_qty:.4f}", "SL": f"{prop_sl_target:.4f}", "TP": f"{prop_tp_target:.4f}", "Risk": f"-${actual_prop_sl_dollar:.2f}"},
    {"Platform": "Bitunix (CEX)", "Direction": cex_direction, "Qty (Units)": f"{cex_qty:.4f}", "SL": f"{cex_sl_target:.4f}", "TP": f"{cex_tp_target:.4f}", "Risk": f"-${actual_cex_sl_dollar:.2f}"}
]
st.table(pd.DataFrame(exec_data))

# --- NEW: LIVE TRADE SEQUENCE MANAGER ---
st.markdown("---")
st.subheader("🕹️ Live Trade Sequence Manager")
st.markdown("Click a button below after your trade concludes to instantly update your balances, track your PnL, and queue up tomorrow's trade limits.")

def handle_loss(risk, cex_win):
    st.session_state.st_prop_balance -= risk
    st.session_state.st_prev_cex_pnl += cex_win
    st.session_state.st_trade_logs.append(f"📉 DRAIN SUCCESS: Breakout lost ${risk:,.2f}. Bitunix extracted +${cex_win:,.2f} to wallet.")

def handle_win(gross_prop, cex_loss, is_eval, tier_val, dead_zone):
    if is_eval:
        st.session_state.st_account_phase = "Funded Stage (Payout Focus)"
        st.session_state.st_prop_balance = float(tier_val)
        st.session_state.st_prev_cex_pnl -= cex_loss
        st.session_state.st_trade_logs.append(f"🎉 CHALLENGE PASSED! Bitunix absorbed -${cex_loss:,.2f} hedge cost. Dashboard upgraded to Funded Stage & Balance reset to ${tier_val:,.2f}. Resume draining!")
    else:
        payout = max(0.0, (gross_prop - dead_zone) * 0.90)
        st.session_state.st_prop_balance = float(tier_val)
        st.session_state.st_prev_cex_pnl += (payout - cex_loss)
        net = payout - cex_loss
        st.session_state.st_trade_logs.append(f"💸 PAYOUT SECURED! Firm paid +${payout:,.2f}, Bitunix lost -${cex_loss:,.2f}. Net Profit: ${net:,.2f}. Account reset to ${tier_val:,.2f}.")

def reset_sequence():
    st.session_state.st_prop_balance = float(tier_value)
    st.session_state.st_prev_cex_pnl = 0.0
    st.session_state.st_trade_logs = []

act_col1, act_col2, act_col3 = st.columns([2, 2, 1])
with act_col1:
    st.button("📉 Breakout Lost (Hit SL)", on_click=handle_loss, args=(actual_prop_sl_dollar, actual_cex_tp_dollar), use_container_width=True, type="primary")
with act_col2:
    st.button("📈 Breakout Won (Hit TP)", on_click=handle_win, args=(actual_prop_tp_dollar, actual_cex_sl_dollar, account_phase == "Evaluation Stage (Milking Evals)", tier_value, dead_zone_amt), use_container_width=True)
with act_col3:
    st.button("🔄 Clear Sequence", on_click=reset_sequence, use_container_width=True)

# Trade Logger UI
if st.session_state.st_trade_logs:
    st.markdown("#### Sequence History")
    for log in st.session_state.st_trade_logs:
        st.markdown(f"<div class='log-box'>{log}</div>", unsafe_allow_html=True)
    
    current_net = st.session_state.st_prev_cex_pnl
    if account_phase == "Evaluation Stage (Milking Evals)":
        current_net -= challenge_fee
        
    pnl_color = "success-text" if current_net >= 0 else "warning-text"
    st.markdown(f"**Current Wallet Impact (Incl. Challenge Fees):** <span class='{pnl_color}'>{'-$' if current_net < 0 else '+$'}{abs(current_net):,.2f}</span>", unsafe_allow_html=True)

st.markdown("---")

# Projection Loop Engine Logic
sim_balance = prop_balance
total_drain_profit = 0.0
trades_to_blow = 0

while sim_balance > account_blow_level:
    trades_to_blow += 1
    sim_dead_zone = max(0.0, tier_value - sim_balance)
    current_sim_risk = min(prop_risk_chunk, sim_balance - account_blow_level)
    
    if selected_strategy == "Manual Hedge Ratio Selection [CUSTOM]":
        step_cex_tp = (current_sim_risk / price_delta) * custom_hedge_ratio * price_delta
    elif "High Win-Rate" in selected_strategy:
        s_p_tp = current_sim_risk / 3.0
        s_n_pay = max(0.0, (s_p_tp - sim_dead_zone) * 0.90) if account_phase == "Funded Stage (Payout Focus)" else 0.0
        s_c_sl = max(0.0, s_n_pay - target_net_profit)
        step_cex_tp = s_c_sl * 3.0
    elif "Drain" in selected_strategy:
        s_p_tp = current_sim_risk * prop_rr 
        s_n_pay = max(0.0, (s_p_tp - sim_dead_zone) * 0.90) if account_phase == "Funded Stage (Payout Focus)" else 0.0
        s_c_sl = s_n_pay if s_n_pay > 0 else (current_sim_risk * 1.5) if sim_balance <= tier_value else s_p_tp * 0.75 
        step_cex_tp = s_c_sl / 3.0
    elif "Aggressive" in selected_strategy:
        step_cex_tp = current_sim_risk * 0.90
    else:
        s_p_tp = current_sim_risk * 2.0
        s_n_pay = max(0.0, (s_p_tp - sim_dead_zone) * 0.90) if account_phase == "Funded Stage (Payout Focus)" else 0.0
        s_c_sl = s_n_pay if s_n_pay > 0 else (current_sim_risk * 0.75)
        step_cex_tp = s_c_sl / 2.0
        
    total_drain_profit += step_cex_tp
    sim_balance -= current_sim_risk

st.subheader("🔮 Immediate Trade Outcomes")

def fmt_money(val): return f"{'-$' if val < 0 else '+$'}{abs(val):,.2f}"

if account_phase == "Funded Stage (Payout Focus)":
    scen1_prop_pnl = -actual_prop_sl_dollar
    scen1_cex_pnl = actual_cex_tp_dollar
    scen1_net = scen1_cex_pnl + prev_cex_pnl
    
    scen2_gross_prop = actual_prop_tp_dollar
    scen2_payout = max(0.0, (scen2_gross_prop - dead_zone_amt) * 0.90)
    scen2_cex_pnl = -actual_cex_sl_dollar
    scen2_net = scen2_payout + scen2_cex_pnl + prev_cex_pnl
    
    outcome_data = [
        {"Scenario": "📉 The Drain (Prop SL / CEX TP)", "Prop Balance Change": f"-${actual_prop_sl_dollar:.2f}", "CEX PnL (Wallet)": f"+${actual_cex_tp_dollar:.2f}", "Total Net Cash": fmt_money(scen1_net)},
        {"Scenario": "📈 The Payout (Prop TP / CEX SL)", "Prop Balance Change": f"+${actual_prop_tp_dollar:.2f}", "CEX PnL (Wallet)": f"-${actual_cex_sl_dollar:.2f}", "Total Net Cash": fmt_money(scen2_net)}
    ]
else:
    st.markdown(f"""<div class="eval-box"><span style="color:#d946ef; font-weight:bold;">🎟️ EVALUATION MODE ACTIVE ({account_type.upper()})</span><br>Payouts are $0. The goal is to either extract cash on a failure, or calculate the exact sunk cost of acquiring the funded account.</div>""", unsafe_allow_html=True)
    
    scen1_cex_pnl = actual_cex_tp_dollar
    scen1_net = scen1_cex_pnl - challenge_fee
    
    scen2_cex_pnl = -actual_cex_sl_dollar
    scen2_net = scen2_cex_pnl - challenge_fee
    
    outcome_data = [
        {"Scenario": "💀 Eval Failed (Prop SL Hits)", "Prop Result": "Drawdown", "CEX Extraction": f"+${actual_cex_tp_dollar:.2f}", "Net Profit (After Fee)": fmt_money(scen1_net)},
        {"Scenario": "🎉 Eval Passed (Prop TP Hits)", "Prop Result": "Funded Unlocked!", "CEX Cost": f"-${actual_cex_sl_dollar:.2f}", "Total Acquisition Cost": f"-${abs(scen2_net):,.2f}"}
    ]

st.table(pd.DataFrame(outcome_data))

st.markdown("---")
st.subheader("🩸 Full Account Drain Projection (100% Loss Rate)")

if account_phase == "Funded Stage (Payout Focus)":
    final_drain_net = total_drain_profit + prev_cex_pnl
    pnl_color = "success-text" if final_drain_net > 0 else "warning-text"
    st.markdown(f"""
    <div class="metric-box">
        💥 <b>Trades to Blow Account:</b> {trades_to_blow} consecutive losses<br>
        💰 <b>Total Bitunix Cash Extracted:</b> <span class="success-text">+${total_drain_profit:,.2f}</span><br>
        📊 <b>FINAL NET CASH (Incl Prev PnL):</b> <span class="{pnl_color}">{fmt_money(final_drain_net)}</span>
    </div>
    """, unsafe_allow_html=True)
else:
    final_drain_net = total_drain_profit - challenge_fee
    pnl_color = "success-text" if final_drain_net > 0 else "warning-text"
    st.markdown(f"""
    <div class="metric-box" style="border-left: 4px solid #d946ef;">
        If you successfully milk the evaluation and fail the account:<br><br>
        💥 <b>Trades to Fail Challenge:</b> {trades_to_blow} losses<br>
        💰 <b>Total Gross Extracted to Bitunix:</b> <span class="success-text">+${total_drain_profit:,.2f}</span><br>
        💸 <b>Challenge Fee Deducted:</b> -${challenge_fee:,.2f}<br>
        📊 <b>FINAL NET TAKE-HOME PROFIT:</b> <span class="{pnl_color}">{fmt_money(final_drain_net)}</span>
    </div>
    """, unsafe_allow_html=True)
