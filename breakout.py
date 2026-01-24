import streamlit as st
import pandas as pd

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Breakout Hedge Commander v16", layout="wide", page_icon="🛡️")

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
    
    /* Total Row */
    .total-row { display: flex; justify-content: space-between; margin-top: 15px; padding-top: 15px; border-top: 1px solid #444; font-size: 1.3em; font-weight: bold; }
    
    /* Solver Box */
    .solver-box { border: 1px solid #00BFFF; background-color: #0a192f; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Breakout Hedge Commander v16")
st.caption("Complete Suite: Profit Solver + Detailed Balance Sheets")

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

# --- CALCULATION ENGINE ---
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
        "prop_size": prop_size,
        "cex_size": cex_size
    }

# Execute Base Calculations
p1 = calculate_metrics(acct_size * 0.05, ratio_p1)
p2 = calculate_metrics(acct_size * 0.10, ratio_p2)
total_sunk = fee + p1['cex_loss_pass'] + p2['cex_loss_pass']

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["PHASE 1 (Eval)", "PHASE 2 (Verify)", "PHASE 3 (Funded & Solver)"])

# === PHASE 1 ===
with tab1:
    st.markdown("<div class='big-header'>Phase 1: The Setup</div>", unsafe_allow_html=True)
    
    if st.session_state.phase1_status == "Pending":
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Risk", f"${acct_size*risk_per_trade_pct:,.0f}")
        c2.metric("Prop Size", f"${p1['prop_size']:,.0f}")
        c3.metric("CEX Size", f"${p1['cex_size']:,.0f}")
        c4.metric("Daily Limit", f"${acct_size*daily_dd_pct:,.0f}")
        
        st.markdown("---")
        if zero_cex_fees: st.success("🔥 Zero-Fee Mode Active")

        col_pass, col_fail = st.columns(2)
        with col_pass:
            st.info(f"**Cost to Pass:** -${p1['cex_loss_pass']:,.2f}")
            if st.button("Phase 1 PASSED", key="p1_pass"): st.session_state.phase1_status="Passed"; st.rerun()
        with col_fail:
            st.error(f"**Refund if Fail:** +${p1['cex_win_fail']:,.2f}")
            if st.button("Phase 1 FAILED", key="p1_fail"): st.session_state.phase1_status="Failed"; st.rerun()

    elif st.session_state.phase1_status == "Passed":
        html_p1_pass = f"""
        <div class="result-card" style="border-left: 5px solid #00FF7F;">
        <div class="pass-header">✅ Phase 1 Passed</div>
        <div class="money-row"><span>Fee:</span><span class="money-neg">-${fee:,.2f}</span></div>
        <div class="money-row"><span>Hedge Cost:</span><span class="money-neg">-${p1['cex_loss_pass']:,.2f}</span></div>
        <div class="total-row"><span>Sunk Cost:</span><span class="money-neg">-${fee + p1['cex_loss_pass']:,.2f}</span></div>
        </div>"""
        st.markdown(html_p1_pass, unsafe_allow_html=True)
        if st.button("Undo Phase 1", key="u1"): st.session_state.phase1_status="Pending"; st.rerun()

    elif st.session_state.phase1_status == "Failed":
        net_res = p1['cex_win_fail'] - fee
        html_p1_fail = f"""
        <div class="result-card" style="border-left: 5px solid #FF4B4B;">
        <div class="fail-header">❌ Phase 1 Failed (Drained)</div>
        <div class="money-row"><span>Refund:</span><span class="money-pos">+${p1['cex_win_fail']:,.2f}</span></div>
        <div class="money-row"><span>Fee:</span><span class="money-neg">-${fee:,.2f}</span></div>
        <div class="total-row"><span>NET:</span><span class="{'money-pos' if net_res>0 else 'money-neg'}">${net_res:,.2f}</span></div>
        </div>"""
        st.markdown(html_p1_fail, unsafe_allow_html=True)
        if st.button("Restart Phase 1", key="r1"): st.session_state.phase1_status="Pending"; st.rerun()

# === PHASE 2 ===
with tab2:
    if st.session_state.phase1_status != "Passed":
        st.warning("Locked: Complete Phase 1 first.")
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
            if st.button("Phase 2 PASSED", key="p2_pass"): st.session_state.phase2_status="Passed"; st.rerun()
        with col_fail:
            st.error(f"**Refund if Fail:** +${p2['cex_win_fail']:,.2f}")
            if st.button("Phase 2 FAILED", key="p2_fail"): st.session_state.phase2_status="Failed"; st.rerun()

    elif st.session_state.phase2_status == "Passed":
        html_p2_pass = f"""
        <div class="result-card" style="border-left: 5px solid #00FF7F;">
        <div class="pass-header">🏆 YOU ARE FUNDED!</div>
        <div class="money-row"><span>Phase 1 Cost:</span><span class="money-neg">-${p1['cex_loss_pass']:,.2f}</span></div>
        <div class="money-row"><span>Phase 2 Cost:</span><span class="money-neg">-${p2['cex_loss_pass']:,.2f}</span></div>
        <div class="total-row"><span>TOTAL INVESTMENT:</span><span class="money-neg">-${total_sunk:,.2f}</span></div>
        </div>"""
        st.markdown(html_p2_pass, unsafe_allow_html=True)
        if st.button("Undo Phase 2", key="u2"): st.session_state.phase2_status="Pending"; st.rerun()

    elif st.session_state.phase2_status == "Failed":
        html_p2_fail = f"""
        <div class="result-card" style="border-left: 5px solid #FF4B4B;">
        <div class="fail-header">❌ Phase 2 Failed</div>
        <div class="money-row"><span>Refund:</span><span class="money-pos">+${p2['cex_win_fail']:,.2f}</span></div>
        <div class="total-row"><span>Sunk Costs:</span><span class="money-neg">-${fee + p1['cex_loss_pass']:,.2f}</span></div>
        </div>"""
        st.markdown(html_p2_fail, unsafe_allow_html=True)
        if st.button("Restart Phase 2", key="r2"): st.session_state.phase2_status="Pending"; st.rerun()

# === PHASE 3 ===
with tab3:
    st.markdown("<div class='big-header'>Funded Phase: Profit Engineer</div>", unsafe_allow_html=True)
    
    # 1. TOOL SELECTION
    tool_mode = st.radio("Select Mode:", ["🎚️ Manual Slider", "🎯 Guaranteed Profit Solver"], horizontal=True)
    
    # 2. INPUTS
    if tool_mode == "🎚️ Manual Slider":
        f_ratio = st.slider("Hedge Ratio (CEX Risk per $1 Prop)", 0.1, 1.5, 0.75, 0.01)
    else:
        st.markdown(f"""
        <div class="solver-box">
            <h4 style="color:#00BFFF; margin:0;">🎯 Target: Guaranteed Fail Profit</h4>
            <p style="color:#ccc; font-size:0.9em;">Total Investment to Recover: <strong>${total_sunk:,.2f}</strong></p>
        </div>
        """, unsafe_allow_html=True)
        desired_fail_profit = st.number_input("Desired Profit if Account Blown ($):", value=600.0, step=50.0)
        
        # SOLVER LOGIC
        # CEX_Win = Sunk + Desired
        # CEX_Win ~= MaxDD * Ratio
        target_win = total_sunk + desired_fail_profit
        f_ratio = target_win / (acct_size * max_dd_pct)
        if f_ratio > 2.0: f_ratio = 2.0 # Cap for safety
        
        st.info(f"💡 Calculated Ratio: **{f_ratio:.2f}** (Risks ${f_ratio:.2f} on CEX per $1 Prop)")

    # 3. CALCULATE
    f_metrics = calculate_metrics(acct_size*0.05, 0, is_funded=True, funded_ratio=f_ratio)
    
    # 4. RESULTS
    prop_payout = (acct_size * 0.05) * 0.90
    monthly_net = prop_payout - f_metrics['cex_loss_pass']
    actual_fail_profit = f_metrics['cex_win_fail'] - total_sunk
    total_net_lifetime = monthly_net - total_sunk
    
    # 5. DISPLAY CARD
    monthly_color = 'money-pos' if monthly_net > 0 else 'money-neg'
    fail_color = 'money-pos' if actual_fail_profit > 0 else 'money-neg'
    
    html_p3 = f"""
    <div class="result-card" style="border: 1px solid #FFD700;">
    <div style="color: #FFD700; font-size: 1.5em; font-weight: bold; margin-bottom: 15px;">💰 Scenario Analysis (Ratio: {f_ratio:.2f})</div>
    
    <div style="color:#aaa; font-weight:bold; margin-top:10px;">SCENARIO A: YOU PASS (Payout)</div>
    <div class="money-row"><span>Prop Payout (90%):</span><span class="money-pos">+${prop_payout:,.2f}</span></div>
    <div class="money-row"><span>CEX Cost:</span><span class="money-neg">-${f_metrics['cex_loss_pass']:,.2f}</span></div>
    <div class="money-row" style="border-top:1px solid #333; padding-top:5px;">
        <span>Net Monthly Profit:</span><span class="{monthly_color}">${monthly_net:,.2f}</span>
    </div>

    <div style="color:#aaa; font-weight:bold; margin-top:20px;">SCENARIO B: YOU FAIL (Blow Account)</div>
    <div class="money-row"><span>CEX Refund:</span><span class="money-pos">+${f_metrics['cex_win_fail']:,.2f}</span></div>
    <div class="money-row"><span>Less Sunk Costs:</span><span class="money-neg">-${total_sunk:,.2f}</span></div>
    <div class="money-row" style="border-top:1px solid #333; padding-top:5px;">
        <span>Net Profit on Fail:</span><span class="{fail_color}">${actual_fail_profit:,.2f}</span>
    </div>
    
    <div class="total-row"><span>LIFETIME NET (If Passed):</span><span class="{monthly_color}">${total_net_lifetime:,.2f}</span></div>
    </div>"""
    st.markdown(html_p3, unsafe_allow_html=True)
