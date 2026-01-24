import streamlit as st
import pandas as pd

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Breakout Hedge Commander v13", layout="wide", page_icon="🛡️")

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
    
    .pass-header { color: #00FF7F; font-size: 1.5em; font-weight: bold; margin-bottom: 10px; border-bottom: 1px solid #333; padding-bottom: 10px; }
    .fail-header { color: #FF4B4B; font-size: 1.5em; font-weight: bold; margin-bottom: 10px; border-bottom: 1px solid #333; padding-bottom: 10px; }
    
    /* Money Styles */
    .money-row { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 1.0em; }
    .money-pos { color: #00FF7F; font-weight: bold; }
    .money-neg { color: #FF4B4B; font-weight: bold; }
    .money-neutral { color: #aaa; font-weight: bold; }
    
    /* Total Row */
    .total-row { display: flex; justify-content: space-between; margin-top: 15px; padding-top: 15px; border-top: 1px solid #444; font-size: 1.3em; font-weight: bold; }
    
    /* Optimizer Box */
    .opt-box { background-color: #0d1117; border-left: 5px solid #00FF7F; padding: 15px; margin-top: 20px; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Breakout Hedge Commander v13")
st.caption("Fixed: HTML Rendering Issue & Layout")

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
    zero_cex_fees = st.checkbox("🔥 Use Zero-Fee CEX?", value=False, help="Sets CEX commission to $0.")
    
    st.markdown("---")
    include_swap = st.checkbox("Include Swap Fees?", value=True)
    if include_swap:
        swap_rate = st.number_input("Swap Rate (%)", 0.03, format="%.4f") / 100
        days_held = st.number_input("Avg Days Held", 2)
    else:
        swap_rate = 0.0
        days_held = 0.0
    
    st.markdown("---")
    if st.button("🔄 FULL RESET", key="reset_all"):
        st.session_state.phase1_status = "Pending"
        st.session_state.phase2_status = "Pending"
        st.rerun()

# --- CALCULATION ENGINE ---
def calculate_metrics(target_profit, ratio_val, is_funded=False, funded_ratio=0.0):
    risk_usd = acct_size * risk_per_trade_pct
    sl_dist = 0.01 
    
    prop_size = risk_usd / sl_dist
    
    if is_funded:
        effective_f_ratio = funded_ratio if funded_ratio > 0 else 1.0
        cex_size = prop_size * effective_f_ratio
        eff_ratio_divisor = 1/effective_f_ratio
    else:
        cex_size = prop_size / ratio_val
        eff_ratio_divisor = ratio_val

    # FRICTION
    prop_comm_cost = prop_size * comm_rate * 2 
    cex_comm_rate_applied = 0.0 if zero_cex_fees else comm_rate
    cex_comm_cost = cex_size * cex_comm_rate_applied * 2
    
    prop_swap = (prop_size * swap_rate * days_held) if include_swap else 0
    cex_swap = (cex_size * swap_rate * days_held) if include_swap else 0
    
    prop_friction = prop_comm_cost + prop_swap
    cex_friction = cex_comm_cost + cex_swap
    
    # 1. PASS SCENARIO
    prop_gross_needed = target_profit + prop_friction
    
    if is_funded:
        cex_loss_pass = (prop_gross_needed * funded_ratio) + cex_friction
    else:
        cex_loss_pass = (prop_gross_needed / ratio_val) + cex_friction

    # 2. FAIL SCENARIO (Max Drain)
    total_prop_drain = acct_size * max_dd_pct
    drain_multiplier = max_dd_pct / risk_per_trade_pct
    
    if is_funded:
        cex_win_gross = total_prop_drain * funded_ratio
    else:
        cex_win_gross = total_prop_drain / ratio_val
        
    cex_win_net = cex_win_gross - (cex_friction * drain_multiplier)

    return {
        "cex_loss_pass": cex_loss_pass,
        "cex_win_fail": cex_win_net,
        "prop_size": prop_size,
        "cex_size": cex_size,
        "prop_friction": prop_friction
    }

# Execute Base Calculations
p1 = calculate_metrics(acct_size * 0.05, ratio_p1)
p2 = calculate_metrics(acct_size * 0.10, ratio_p2)
total_sunk = fee + p1['cex_loss_pass'] + p2['cex_loss_pass']

# --- MAIN TABS ---
tab1, tab2, tab3 = st.tabs(["PHASE 1 (Eval)", "PHASE 2 (Verify)", "PHASE 3 (Funded)"])

# === PHASE 1 ===
with tab1:
    st.markdown("<div class='big-header'>Phase 1: The Setup</div>", unsafe_allow_html=True)
    
    if st.session_state.phase1_status == "Pending":
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Risk", f"${acct_size*risk_per_trade_pct:,.0f}")
        c2.metric("Daily Limit", f"${acct_size*daily_dd_pct:,.0f}")
        c3.metric("Prop Size", f"${p1['prop_size']:,.0f}")
        c4.metric("CEX Size", f"${p1['cex_size']:,.0f}")
        
        st.markdown("---")
        if zero_cex_fees:
            st.success("🔥 Zero-Fee Mode Active")
            
        col_pass, col_fail = st.columns(2)
        with col_pass:
            st.info(f"**Cost to Pass:** -${p1['cex_loss_pass']:,.2f}")
            if st.button("Phase 1 PASSED", key="btn_p1_pass"): 
                st.session_state.phase1_status = "Passed"
                st.rerun()
        with col_fail:
            st.error(f"**Refund if Fail:** +${p1['cex_win_fail']:,.2f}")
            if st.button("Phase 1 FAILED", key="btn_p1_fail"): 
                st.session_state.phase1_status = "Failed"
                st.rerun()

    elif st.session_state.phase1_status == "Passed":
        # PASSED CARD
        html_p1_pass = f"""
<div class="result-card" style="border-left: 5px solid #00FF7F;">
<div class="pass-header">✅ Phase 1 Passed</div>
<div class="money-row"><span>Evaluation Fee:</span><span class="money-neg">-${fee:,.2f}</span></div>
<div class="money-row"><span>CEX Hedge Cost:</span><span class="money-neg">-${p1['cex_loss_pass']:,.2f}</span></div>
<div class="total-row"><span>Current Sunk Cost:</span><span class="money-neg">-${fee + p1['cex_loss_pass']:,.2f}</span></div>
</div>"""
        st.markdown(html_p1_pass, unsafe_allow_html=True)
        
        if st.button("Undo Phase 1", key="undo_p1"): 
            st.session_state.phase1_status = "Pending"
            st.rerun()

    elif st.session_state.phase1_status == "Failed":
        # FAILED CARD
        net_res = p1['cex_win_fail'] - fee
        net_color = 'money-pos' if net_res > 0 else 'money-neg'
        html_p1_fail = f"""
<div class="result-card" style="border-left: 5px solid #FF4B4B;">
<div class="fail-header">❌ Phase 1 Failed (Drained)</div>
<div class="money-row"><span>CEX Gross Refund:</span><span class="money-pos">+${p1['cex_win_fail']:,.2f}</span></div>
<div class="money-row"><span>Evaluation Fee Paid:</span><span class="money-neg">-${fee:,.2f}</span></div>
<div class="total-row"><span>NET PROFIT (Refund - Fee):</span><span class="{net_color}">${net_res:,.2f}</span></div>
</div>"""
        st.markdown(html_p1_fail, unsafe_allow_html=True)
        
        if st.button("Restart Phase 1", key="rest_p1"): 
            st.session_state.phase1_status = "Pending"
            st.rerun()

# === PHASE 2 ===
with tab2:
    if st.session_state.phase1_status != "Passed":
        st.warning("🔒 Complete Phase 1 first.")
    elif st.session_state.phase2_status == "Pending":
        st.markdown("<div class='big-header'>Phase 2: Verification</div>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Risk", f"${acct_size*risk_per_trade_pct:,.0f}")
        c2.metric("Prop Size", f"${p2['prop_size']:,.0f}")
        c3.metric("CEX Size", f"${p2['cex_size']:,.0f}")
        
        st.markdown("---")
        col_pass, col_fail = st.columns(2)
        with col_pass:
            st.info(f"**Cost to Pass:** -${p2['cex_loss_pass']:,.2f}")
            if st.button("Phase 2 PASSED", key="btn_p2_pass"): 
                st.session_state.phase2_status = "Passed"
                st.rerun()
        with col_fail:
            st.error(f"**Refund if Fail:** +${p2['cex_win_fail']:,.2f}")
            if st.button("Phase 2 FAILED", key="btn_p2_fail"): 
                st.session_state.phase2_status = "Failed"
                st.rerun()
                
    elif st.session_state.phase2_status == "Passed":
        # FUNDED CARD
        html_p2_pass = f"""
<div class="result-card" style="border-left: 5px solid #00FF7F;">
<div class="pass-header">🏆 YOU ARE FUNDED!</div>
<div class="money-row"><span>Phase 1 Cost:</span><span class="money-neg">-${p1['cex_loss_pass']:,.2f}</span></div>
<div class="money-row"><span>Phase 2 Cost:</span><span class="money-neg">-${p2['cex_loss_pass']:,.2f}</span></div>
<div class="money-row"><span>Fee:</span><span class="money-neg">-${fee:,.2f}</span></div>
<div class="total-row"><span>TOTAL INVESTMENT:</span><span class="money-neg">-${total_sunk:,.2f}</span></div>
</div>"""
        st.markdown(html_p2_pass, unsafe_allow_html=True)
        
        if st.button("Undo Phase 2", key="undo_p2"): 
            st.session_state.phase2_status = "Pending"
            st.rerun()
            
    elif st.session_state.phase2_status == "Failed":
        net_res_p2 = p2['cex_win_fail'] - (fee + p1['cex_loss_pass'])
        net_color_p2 = 'money-pos' if net_res_p2 > 0 else 'money-neg'
        html_p2_fail = f"""
<div class="result-card" style="border-left: 5px solid #FF4B4B;">
<div class="fail-header">❌ Phase 2 Failed</div>
<div class="money-row"><span>CEX Refund:</span><span class="money-pos">+${p2['cex_win_fail']:,.2f}</span></div>
<div class="money-row"><span>Sunk Costs (Fee+P1):</span><span class="money-neg">-${fee + p1['cex_loss_pass']:,.2f}</span></div>
<div class="total-row"><span>NET RESULT:</span><span class="{net_color_p2}">${net_res_p2:,.2f}</span></div>
</div>"""
        st.markdown(html_p2_fail, unsafe_allow_html=True)
        
        if st.button("Restart Phase 2", key="rest_p2"): 
            st.session_state.phase2_status = "Pending"
            st.rerun()

# === PHASE 3 ===
with tab3:
    st.markdown("<div class='big-header'>Funded Phase: Harvest</div>", unsafe_allow_html=True)
    
    # INPUTS
    f_ratio = st.slider("Hedge Ratio (CEX Risk per $1 Prop)", 0.1, 1.0, 0.75, 0.01)
    
    # CALCS
    funded_metrics = calculate_metrics(acct_size*0.05, 0, is_funded=True, funded_ratio=f_ratio)
    prop_payout = (acct_size * 0.05) * 0.90
    hedge_cost = funded_metrics['cex_loss_pass']
    monthly_net = prop_payout - hedge_cost
    total_net = monthly_net - total_sunk
    monthly_net_color = 'money-pos' if monthly_net > 0 else 'money-neg'
    total_net_color = 'money-pos' if total_net > 0 else 'money-neg'
    
    # --- THE BALANCE SHEET (User Requested) ---
    html_p3 = f"""
<div class="result-card" style="border: 1px solid #FFD700;">
<div style="color: #FFD700; font-size: 1.5em; font-weight: bold; margin-bottom: 15px;">💰 Final Profit Calculation</div>
<div class="money-row"><span>Prop Firm Payout (90%):</span><span class="money-pos">+${prop_payout:,.2f}</span></div>
<div class="money-row"><span>CEX Hedge Burn (Cost):</span><span class="money-neg">-${hedge_cost:,.2f}</span></div>
<div style="border-top: 1px solid #333; margin: 10px 0;"></div>
<div class="money-row" style="font-size: 1.1em; font-weight: bold;"><span>Net Monthly Profit:</span><span class="{monthly_net_color}">${monthly_net:,.2f}</span></div>
<br>
<div class="money-row" style="color: #aaa;"><span>Previous Sunk Costs (Fee + P1 + P2):</span><span>-${total_sunk:,.2f}</span></div>
<div class="total-row"><span>TOTAL NET PROFIT:</span><span class="{total_net_color}">${total_net:,.2f}</span></div>
</div>"""
    st.markdown(html_p3, unsafe_allow_html=True)
    
    # OPTIMIZER ALERT
    prop_gross_approx = (acct_size * 0.05) + funded_metrics['prop_friction']
    breakeven_ratio = prop_payout / prop_gross_approx
    if not zero_cex_fees: breakeven_ratio *= 0.95

    if monthly_net < 0:
        html_alert = f"""
<div class="opt-box" style="border-left-color: #FF4B4B; background-color: #220a0a;">
<h4 style="margin:0; color: #FF4B4B;">⚠️ Unprofitable Settings</h4>
<p>Your ratio ({f_ratio}) is too high for your fees.</p>
<p><strong>Recommendation:</strong> Slide ratio below <strong>{breakeven_ratio:.2f}</strong> to turn Green.</p>
</div>"""
        st.markdown(html_alert, unsafe_allow_html=True)
