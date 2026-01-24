import streamlit as st
import pandas as pd

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Breakout Hedge Commander v15", layout="wide", page_icon="🛡️")

# --- SESSION STATE ---
if 'phase1_status' not in st.session_state: st.session_state.phase1_status = "Pending"
if 'phase2_status' not in st.session_state: st.session_state.phase2_status = "Pending"

# --- STYLING ---
st.markdown("""
<style>
    /* Main Layout */
    .big-header { font-size: 24px; font-weight: bold; color: #4CAF50; margin-bottom: 10px; }
    
    /* Result Cards */
    .result-card { background-color: #0e1117; border: 1px solid #333; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
    
    /* Money Styles */
    .money-pos { color: #00FF7F; font-weight: bold; }
    .money-neg { color: #FF4B4B; font-weight: bold; }
    
    /* Reverse Calc Box */
    .solver-box { border: 1px solid #00BFFF; background-color: #0a192f; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Breakout Hedge Commander v15")
st.caption("Feature Added: 'Guaranteed Fail Profit' Solver")

# --- SIDEBAR: INPUTS ---
with st.sidebar:
    st.header("1. Account Rules")
    acct_size = st.number_input("Account Size ($)", 50000, step=10000)
    fee = st.number_input("Signup Fee ($)", 450)
    
    st.header("2. Risk Management")
    max_dd_pct = st.number_input("Max Drawdown Limit (%)", 8.0) / 100
    daily_dd_pct = st.number_input("Daily Drawdown Limit (%)", 5.0) / 100
    risk_per_trade_pct = st.number_input("RISK PER TRADE (%)", 4.0) / 100
    
    st.header("3. Hedge Ratios")
    st.caption("Evaluation Phase")
    ratio_p1 = st.number_input("Phase 1 Ratio", 5.8, step=0.1)
    ratio_p2 = st.number_input("Phase 2 Ratio", 3.2, step=0.1)
    
    st.markdown("---")
    st.header("4. Market Friction")
    comm_rate = st.number_input("Standard Commission (%)", 0.04, format="%.4f") / 100
    zero_cex_fees = st.checkbox("🔥 Use Zero-Fee CEX?", value=False)
    
    st.markdown("---")
    include_swap = st.checkbox("Include Swap Fees?", value=True)
    if include_swap:
        swap_rate = st.number_input("Swap Rate (%)", 0.03, format="%.4f") / 100
        days_held = st.number_input("Avg Days Held", 2)
    else:
        swap_rate = 0.0
        days_held = 0.0
        
    if st.button("🔄 FULL RESET"):
        st.session_state.phase1_status = "Pending"
        st.session_state.phase2_status = "Pending"
        st.rerun()

# --- ENGINE ---
def calculate_metrics(target_profit, ratio_val, is_funded=False, funded_ratio=0.0):
    risk_usd = acct_size * risk_per_trade_pct
    sl_dist = 0.01 
    prop_size = risk_usd / sl_dist
    
    if is_funded:
        cex_size = prop_size * funded_ratio
    else:
        cex_size = prop_size / ratio_val

    # FRICTION
    prop_fric = (prop_size * comm_rate * 2) + ((prop_size * swap_rate * days_held) if include_swap else 0)
    
    cex_comm_applied = 0.0 if zero_cex_fees else comm_rate
    cex_fric = (cex_size * cex_comm_applied * 2) + ((cex_size * swap_rate * days_held) if include_swap else 0)
    
    # PASS
    prop_gross = target_profit + prop_fric
    if is_funded:
        cex_loss_pass = (prop_gross * funded_ratio) + cex_fric
    else:
        cex_loss_pass = (prop_gross / ratio_val) + cex_fric

    # FAIL
    total_prop_drain = acct_size * max_dd_pct
    drain_multiplier = max_dd_pct / risk_per_trade_pct
    
    if is_funded:
        cex_win_gross = total_prop_drain * funded_ratio
    else:
        cex_win_gross = total_prop_drain / ratio_val
        
    cex_win_net = cex_win_gross - (cex_fric * drain_multiplier)

    return {
        "cex_loss_pass": cex_loss_pass,
        "cex_win_fail": cex_win_net,
        "prop_friction": prop_fric
    }

# Base Calcs
p1 = calculate_metrics(acct_size * 0.05, ratio_p1)
p2 = calculate_metrics(acct_size * 0.10, ratio_p2)
total_sunk = fee + p1['cex_loss_pass'] + p2['cex_loss_pass']

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["PHASE 1", "PHASE 2", "PHASE 3 (Funded & Solver)"])

# P1 & P2 Simplified Display
with tab1:
    st.markdown("### Phase 1")
    c1, c2 = st.columns(2)
    c1.info(f"Cost to Pass: -${p1['cex_loss_pass']:,.2f}")
    c2.error(f"Refund if Fail: +${p1['cex_win_fail']:,.2f}")
    if st.button("Passed P1"): st.session_state.phase1_status="Passed"; st.rerun()

with tab2:
    st.markdown("### Phase 2")
    c1, c2 = st.columns(2)
    c1.info(f"Cost to Pass: -${p2['cex_loss_pass']:,.2f}")
    c2.error(f"Refund if Fail: +${p2['cex_win_fail']:,.2f}")
    if st.button("Passed P2"): st.session_state.phase2_status="Passed"; st.rerun()

# PHASE 3: THE SOLVER
with tab3:
    st.markdown("<div class='big-header'>Funded Phase: Profit Engineer</div>", unsafe_allow_html=True)
    
    # SOLVER UI
    st.markdown(f"""
    <div class="solver-box">
        <h4 style="color:#00BFFF; margin:0;">🎯 Guaranteed Profit Solver</h4>
        <p style="color:#ccc; font-size:0.9em;">Total Sunk Costs to Recover: <strong>${total_sunk:,.2f}</strong></p>
    </div>
    """, unsafe_allow_html=True)
    
    desired_fail_profit = st.number_input("I want to make this much PROFIT if I blow the account ($):", value=600.0, step=50.0)
    
    # REVERSE MATH
    # We need: CEX_Win_Fail - Total_Sunk = Desired_Profit
    # CEX_Win_Fail = Total_Sunk + Desired_Profit
    target_cex_win = total_sunk + desired_fail_profit
    
    # CEX_Win_Fail ~= (MaxDD * Ratio) - Friction
    # We ignore friction for the estimation to solve for Ratio, then refine
    # Ratio ~= Target_Win / MaxDD
    suggested_ratio = target_cex_win / (acct_size * max_dd_pct)
    
    # Cap ratio at 1.5 for safety
    if suggested_ratio > 1.5: suggested_ratio = 1.5
    
    # --- RUN CALC WITH SUGGESTED RATIO ---
    f_metrics = calculate_metrics(acct_size*0.05, 0, is_funded=True, funded_ratio=suggested_ratio)
    
    # PnL Checks
    actual_fail_profit = f_metrics['cex_win_fail'] - total_sunk
    
    prop_payout = (acct_size*0.05) * 0.90
    monthly_net = prop_payout - f_metrics['cex_loss_pass']
    
    # DISPLAY RESULTS
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.markdown(f"""
        <div class="result-card" style="border: 1px solid #00BFFF;">
            <div style="color:#00BFFF; font-weight:bold; font-size:1.2em;">Recommended Settings</div>
            <div style="font-size:1.5em; font-weight:bold; color:white;">Ratio: {suggested_ratio:.2f}</div>
            <div style="color:#888;">(Risk ${suggested_ratio:.2f} on CEX per $1 Prop)</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col_b:
        if monthly_net > 0:
            status_color = "money-pos"
            status_text = "✅ Profitable Month"
        else:
            status_color = "money-neg"
            status_text = "⚠️ Unprofitable Month"
            
        st.markdown(f"""
        <div class="result-card" style="border: 1px solid #333;">
            <div style="color:#aaa;">Trade-Off Analysis</div>
            <div class="money-row"><span>If you FAIL, you make:</span><span class="money-pos">+${actual_fail_profit:,.2f}</span></div>
            <div class="money-row"><span>If you PASS, you make:</span><span class="{status_color}">${monthly_net:,.2f}</span></div>
            <div style="margin-top:10px; font-weight:bold;">{status_text}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Warning if the desired failure profit forces a ratio so high that passing becomes unprofitable
    if monthly_net < 0:
        st.error(f"🚨 IMPOSSIBLE GOAL: To make ${desired_fail_profit:,.0f} on failure, you need a ratio of {suggested_ratio:.2f}. This is so high that fees/hedging cost will eat 100% of your payout profit. You must accept a lower failure profit.")
