import streamlit as st
import pandas as pd

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Breakout Hedge Commander v18 (Ultimate)", layout="wide", page_icon="🛡️")

# --- SESSION STATE ---
if 'phase1_status' not in st.session_state: st.session_state.phase1_status = "Pending"
if 'phase2_status' not in st.session_state: st.session_state.phase2_status = "Pending"
# Default Presets
if 'risk_preset' not in st.session_state: st.session_state.risk_preset = 4.0
if 'days_preset' not in st.session_state: st.session_state.days_preset = 2

# --- STYLING ---
st.markdown("""
<style>
    .big-header { font-size: 24px; font-weight: bold; color: #FFD700; margin-bottom: 15px; }
    
    /* Result Cards */
    .result-card { background-color: #0e1117; border: 1px solid #333; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
    
    /* Money Colors */
    .money-pos { color: #00FF7F; font-weight: bold; }
    .money-neg { color: #FF4B4B; font-weight: bold; }
    
    /* Headers inside cards */
    .pass-header { color: #00FF7F; font-size: 1.4em; font-weight: bold; margin-bottom: 10px; border-bottom: 1px solid #333; padding-bottom: 5px; }
    .fail-header { color: #FF4B4B; font-size: 1.4em; font-weight: bold; margin-bottom: 10px; border-bottom: 1px solid #333; padding-bottom: 5px; }
    
    /* Rows */
    .money-row { display: flex; justify-content: space-between; margin-bottom: 6px; }
    .total-row { display: flex; justify-content: space-between; margin-top: 15px; padding-top: 10px; border-top: 1px solid #444; font-size: 1.2em; font-weight: bold; }
    
    /* Solver Box */
    .solver-box { border: 1px solid #00BFFF; background-color: #0a1320; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
    
    /* Badge */
    .badge { background-color: #FFD700; color: black; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8em; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Breakout Hedge Commander v18")
st.caption("The Complete Suite: Solver + Balance Sheets + Speedrun Mode")

# --- SIDEBAR ---
with st.sidebar:
    st.header("1. Quick Presets")
    c1, c2 = st.columns(2)
    if c1.button("🛡️ SAFE"):
        st.session_state.risk_preset = 2.0
        st.session_state.days_preset = 3
        st.rerun()
    if c2.button("⚡ SPEED"):
        st.session_state.risk_preset = 4.8
        st.session_state.days_preset = 0
        st.rerun()

    st.header("2. Account Rules")
    acct_size = st.number_input("Account Size ($)", 50000, step=10000)
    fee = st.number_input("Signup Fee ($)", 450)
    
    st.header("3. Risk Management")
    max_dd_pct = st.number_input("Max Drawdown Limit (%)", 8.0) / 100
    daily_dd_pct = st.number_input("Daily Drawdown Limit (%)", 5.0) / 100
    risk_per_trade_pct = st.number_input("RISK PER TRADE (%)", value=st.session_state.risk_preset, step=0.1, format="%.1f") / 100
    
    st.header("4. Hedge Ratios")
    ratio_p1 = st.number_input("Phase 1 Ratio", 5.8, step=0.1)
    ratio_p2 = st.number_input("Phase 2 Ratio", 3.2, step=0.1)
    
    st.markdown("---")
    st.header("5. Market Friction")
    comm_rate = st.number_input("Commission (%)", 0.04, format="%.4f") / 100
    zero_cex_fees = st.checkbox("🔥 Use Zero-Fee CEX?", value=True)
    
    include_swap = st.checkbox("Include Swap Fees?", value=(st.session_state.days_preset > 0))
    swap_rate = 0.0
    days_held = 0.0
    if include_swap:
        swap_rate = st.number_input("Swap Rate (%)", 0.03, format="%.4f") / 100
        days_held = st.number_input("Avg Days Held", value=st.session_state.days_preset)

    st.markdown("---")
    if st.button("🔄 FULL RESET"):
        st.session_state.clear()
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
    cex_comm_effective = 0.0 if zero_cex_fees else comm_rate
    cex_fric = (cex_size * cex_comm_effective * 2) + ((cex_size * swap_rate * days_held) if include_swap else 0)
    
    # PASS LOGIC
    prop_gross = target_profit + prop_fric
    if is_funded:
        cex_loss_pass = (prop_gross * funded_ratio) + cex_fric
    else:
        cex_loss_pass = (prop_gross / ratio_val) + cex_fric

    # FAIL LOGIC (Full Drain)
    total_prop_drain = acct_size * max_dd_pct
    drain_multiplier = max_dd_pct / risk_per_trade_pct 
    
    if is_funded:
        cex_win_gross = total_prop_drain * funded_ratio
    else:
        cex_win_gross = total_prop_drain / ratio_val
        
    cex_win_net = cex_win_gross - (cex_fric * drain_multiplier)

    return {"pass_cost": cex_loss_pass, "fail_refund": cex_win_net, "prop_size": prop_size, "cex_size": cex_size}

# --- CALCULATIONS ---
p1 = calculate_metrics(acct_size * 0.05, ratio_p1)
p2 = calculate_metrics(acct_size * 0.10, ratio_p2)
total_sunk = fee + p1['pass_cost'] + p2['pass_cost']

# --- TABS ---
t1, t2, t3 = st.tabs(["Phase 1", "Phase 2", "Funded"])

# === PHASE 1 ===
with t1:
    st.markdown("<div class='big-header'>Phase 1 Setup</div>", unsafe_allow_html=True)
    if risk_per_trade_pct > 0.045: st.caption("🔥 SPEEDRUN MODE DETECTED")
    
    if st.session_state.phase1_status == "Pending":
        c1, c2, c3 = st.columns(3)
        c1.metric("Prop Size", f"${p1['prop_size']:,.0f}")
        c2.metric("CEX Size", f"${p1['cex_size']:,.0f}")
        c3.metric("Daily Limit", f"${acct_size*daily_dd_pct:,.0f}")
        
        col_pass, col_fail = st.columns(2)
        with col_pass:
            st.info(f"Cost to Pass: -${p1['pass_cost']:,.2f}")
            if st.button("Phase 1 PASSED", key="p1_pass"): st.session_state.phase1_status="Passed"; st.rerun()
        with col_fail:
            st.error(f"Refund if Fail: +${p1['fail_refund']:,.2f}")
            if st.button("Phase 1 FAILED", key="p1_fail"): st.session_state.phase1_status="Failed"; st.rerun()

    elif st.session_state.phase1_status == "Passed":
        html_p1 = f"""
        <div class="result-card" style="border-left: 5px solid #00FF7F;">
            <div class="pass-header">✅ Phase 1 Passed</div>
            <div class="money-row"><span>Evaluation Fee:</span><span class="money-neg">-${fee:,.2f}</span></div>
            <div class="money-row"><span>Hedge Cost:</span><span class="money-neg">-${p1['pass_cost']:,.2f}</span></div>
            <div class="total-row"><span>Sunk Cost:</span><span class="money-neg">-${fee + p1['pass_cost']:,.2f}</span></div>
        </div>"""
        st.markdown(html_p1, unsafe_allow_html=True)
        if st.button("Undo Phase 1"): st.session_state.phase1_status="Pending"; st.rerun()

    elif st.session_state.phase1_status == "Failed":
        net = p1['fail_refund'] - fee
        html_fail = f"""
        <div class="result-card" style="border-left: 5px solid #FF4B4B;">
            <div class="fail-header">❌ Phase 1 Failed (Refund)</div>
            <div class="money-row"><span>Refund:</span><span class="money-pos">+${p1['fail_refund']:,.2f}</span></div>
            <div class="money-row"><span>Fee Paid:</span><span class="money-neg">-${fee:,.2f}</span></div>
            <div class="total-row"><span>NET PROFIT:</span><span class="{'money-pos' if net>0 else 'money-neg'}">${net:,.2f}</span></div>
        </div>"""
        st.markdown(html_fail, unsafe_allow_html=True)
        if st.button("Restart Phase 1"): st.session_state.phase1_status="Pending"; st.rerun()

# === PHASE 2 ===
with t2:
    if st.session_state.phase1_status != "Passed":
        st.warning("🔒 Complete Phase 1 first.")
    else:
        st.markdown("<div class='big-header'>Phase 2 Setup</div>", unsafe_allow_html=True)
        if st.session_state.phase2_status == "Pending":
            col_pass, col_fail = st.columns(2)
            with col_pass:
                st.info(f"Cost to Pass: -${p2['pass_cost']:,.2f}")
                if st.button("Phase 2 PASSED", key="p2_pass"): st.session_state.phase2_status="Passed"; st.rerun()
            with col_fail:
                st.error(f"Refund if Fail: +${p2['fail_refund']:,.2f}")
                if st.button("Phase 2 FAILED", key="p2_fail"): st.session_state.phase2_status="Failed"; st.rerun()

        elif st.session_state.phase2_status == "Passed":
            html_p2 = f"""
            <div class="result-card" style="border-left: 5px solid #00FF7F;">
                <div class="pass-header">🏆 YOU ARE FUNDED!</div>
                <div class="money-row"><span>Phase 1 Cost:</span><span class="money-neg">-${p1['pass_cost']:,.2f}</span></div>
                <div class="money-row"><span>Phase 2 Cost:</span><span class="money-neg">-${p2['pass_cost']:,.2f}</span></div>
                <div class="total-row"><span>TOTAL INVESTMENT:</span><span class="money-neg">-${total_sunk:,.2f}</span></div>
            </div>"""
            st.markdown(html_p2, unsafe_allow_html=True)
            if st.button("Undo Phase 2"): st.session_state.phase2_status="Pending"; st.rerun()

        elif st.session_state.phase2_status == "Failed":
            net = p2['fail_refund'] - (fee + p1['pass_cost'])
            html_f2 = f"""
            <div class="result-card" style="border-left: 5px solid #FF4B4B;">
                <div class="fail-header">❌ Phase 2 Failed</div>
                <div class="money-row"><span>Refund:</span><span class="money-pos">+${p2['fail_refund']:,.2f}</span></div>
                <div class="money-row"><span>Sunk Costs:</span><span class="money-neg">-${fee + p1['pass_cost']:,.2f}</span></div>
                <div class="total-row"><span>NET RESULT:</span><span class="{'money-pos' if net>0 else 'money-neg'}">${net:,.2f}</span></div>
            </div>"""
            st.markdown(html_f2, unsafe_allow_html=True)
            if st.button("Restart Phase 2"): st.session_state.phase2_status="Pending"; st.rerun()

# === FUNDED ===
with t3:
    st.markdown("<div class='big-header'>Funded Phase: Profit Engineer</div>", unsafe_allow_html=True)
    
    # SELECTION
    tool = st.radio("Mode:", ["🎚️ Manual Ratio", "🎯 Guaranteed Profit Solver"], horizontal=True)
    
    if tool == "🎚️ Manual Ratio":
        f_ratio = st.slider("Hedge Ratio", 0.1, 2.0, 0.75, 0.01)
    else:
        st.markdown(f"""
        <div class="solver-box">
            <h4 style="color:#00BFFF; margin:0;">🎯 Target: Guaranteed Fail Profit</h4>
            <p style="color:#ccc; font-size:0.9em;">Total Investment to Recover: <strong>${total_sunk:,.2f}</strong></p>
        </div>
        """, unsafe_allow_html=True)
        target_profit = st.number_input("Desired Profit if Account Blows ($)", 600.0, step=50.0)
        
        # Solver
        req_win = total_sunk + target_profit
        f_ratio = req_win / (acct_size * max_dd_pct)
        if f_ratio > 2.0: f_ratio = 2.0
        st.info(f"💡 Required Ratio: **{f_ratio:.2f}**")

    # CALC
    f_metrics = calculate_metrics(acct_size*0.05, 0, is_funded=True, funded_ratio=f_ratio)
    
    payout = (acct_size * 0.05) * 0.90
    monthly_net = payout - f_metrics['pass_cost']
    fail_net = f_metrics['fail_refund'] - total_sunk
    
    # DISPLAY
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""
        <div class="result-card" style="border: 1px solid #00FF7F;">
            <div style="color:#00FF7F; font-weight:bold; margin-bottom:10px;">SCENARIO A: PASS (Payout)</div>
            <div class="money-row"><span>Payout:</span><span class="money-pos">+${payout:,.2f}</span></div>
            <div class="money-row"><span>Hedge Cost:</span><span class="money-neg">-${f_metrics['pass_cost']:,.2f}</span></div>
            <div class="total-row"><span>MONTHLY NET:</span><span class="{'money-pos' if monthly_net>0 else 'money-neg'}">${monthly_net:,.2f}</span></div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="result-card" style="border: 1px solid #FF4B4B;">
            <div style="color:#FF4B4B; font-weight:bold; margin-bottom:10px;">SCENARIO B: FAIL (Blow Acct)</div>
            <div class="money-row"><span>Refund:</span><span class="money-pos">+${f_metrics['fail_refund']:,.2f}</span></div>
            <div class="money-row"><span>Sunk Costs:</span><span class="money-neg">-${total_sunk:,.2f}</span></div>
            <div class="total-row"><span>EXIT PROFIT:</span><span class="{'money-pos' if fail_net>0 else 'money-neg'}">${fail_net:,.2f}</span></div>
        </div>
        """, unsafe_allow_html=True)
        
    if monthly_net < 0:
        st.warning("⚠️ Warning: This ratio is too high. You are paying more in insurance than you earn in payout.")
