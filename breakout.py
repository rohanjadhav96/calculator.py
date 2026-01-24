import streamlit as st
import pandas as pd

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Breakout Hedge Commander v22", layout="wide", page_icon="🛡️")

# --- SESSION STATE ---
if 'phase1_status' not in st.session_state: st.session_state.phase1_status = "Pending"
if 'phase2_status' not in st.session_state: st.session_state.phase2_status = "Pending"

# --- STYLING ---
st.markdown("""
<style>
    .big-header { font-size: 24px; font-weight: bold; color: #FFD700; margin-bottom: 15px; }
    .result-card { background-color: #0e1117; border: 1px solid #333; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
    .money-pos { color: #00FF7F; font-weight: bold; }
    .money-neg { color: #FF4B4B; font-weight: bold; }
    .pass-header { color: #00FF7F; font-size: 1.4em; font-weight: bold; margin-bottom: 10px; border-bottom: 1px solid #333; padding-bottom: 5px; }
    .fail-header { color: #FF4B4B; font-size: 1.4em; font-weight: bold; margin-bottom: 10px; border-bottom: 1px solid #333; padding-bottom: 5px; }
    .money-row { display: flex; justify-content: space-between; margin-bottom: 6px; }
    .total-row { display: flex; justify-content: space-between; margin-top: 15px; padding-top: 10px; border-top: 1px solid #444; font-size: 1.2em; font-weight: bold; }
    .warning-box { background-color: #2e0b0b; padding: 10px; border-left: 3px solid #FF4B4B; font-size: 0.9em; color: #ffcccc; margin-bottom: 15px; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Breakout Hedge Commander v22")
st.caption("Trailing Drawdown Edition: Optimized for Single-Trade Execution")

# --- SIDEBAR ---
with st.sidebar:
    st.header("1. Account Rules")
    acct_size = st.number_input("Account Size ($)", 50000, step=10000)
    fee = st.number_input("Signup Fee ($)", 450)
    
    st.header("2. Risk Management")
    st.markdown("""
    <div style='font-size:0.9em; color:#FFD700; margin-bottom:10px;'>
    ⚠️ <b>Trailing Drawdown Alert:</b><br>
    Since drawdown trails profit, you MUST pass in <b>1 Trade</b>.
    Taking small wins is dangerous because the drawdown line moves up.
    </div>
    """, unsafe_allow_html=True)
    
    max_dd_pct = st.number_input("Max Drawdown Limit (%)", 8.0) / 100
    daily_dd_pct = st.number_input("Daily Drawdown Limit (%)", 5.0) / 100
    risk_per_trade_pct = st.number_input("RISK PER TRADE (%)", value=4.5, step=0.1, format="%.1f") / 100
    
    if risk_per_trade_pct < 0.04:
        st.warning("⚠️ Risk is too low for 1-Shot Pass. You need ~4.5% risk to hit 5% target in one trade.")
    
    st.header("3. Hedge Ratios")
    ratio_p1 = st.number_input("Phase 1 Ratio", 5.8, step=0.1)
    ratio_p2 = st.number_input("Phase 2 Ratio", 3.2, step=0.1)
    
    st.markdown("---")
    st.header("4. Market Friction")
    comm_rate = st.number_input("Commission (%)", 0.04, format="%.4f") / 100
    zero_cex_fees = st.checkbox("🔥 Use Zero-Fee CEX?", value=True)
    
    # Swap is removed/hidden because 1-Shot implies < 24h holding
    swap_rate = 0.0
    days_held = 0.0

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

    # FRICTION (No Swap, only Comm)
    prop_fric = (prop_size * comm_rate * 2)
    cex_comm_effective = 0.0 if zero_cex_fees else comm_rate
    cex_fric = (cex_size * cex_comm_effective * 2)
    
    # PASS LOGIC (One Shot)
    prop_gross = target_profit + prop_fric
    if is_funded:
        cex_loss_pass = (prop_gross * funded_ratio) + cex_fric
    else:
        cex_loss_pass = (prop_gross / ratio_val) + cex_fric

    # FAIL LOGIC (One Shot Fail)
    # If we risk 4.5% and lose, we stop immediately.
    # We do NOT drain the full 8% because Trailing Drawdown might catch us.
    # We assume "Fail" = Hitting Stop Loss on the big trade.
    
    # Loss on Prop = Risk Amount
    prop_loss = risk_usd
    
    if is_funded:
        cex_win_gross = prop_loss * funded_ratio
    else:
        cex_win_gross = prop_loss / ratio_val
        
    cex_win_net = cex_win_gross - cex_fric

    return {"pass_cost": cex_loss_pass, "fail_refund": cex_win_net, "prop_size": prop_size, "cex_size": cex_size}

# --- CALCULATIONS ---
p1 = calculate_metrics(acct_size * 0.05, ratio_p1)
p2 = calculate_metrics(acct_size * 0.10, ratio_p2)
total_sunk = fee + p1['pass_cost'] + p2['pass_cost']

# --- TABS ---
t1, t2, t3 = st.tabs(["Phase 1", "Phase 2", "Funded Phase"])

# === PHASE 1 ===
with t1:
    st.markdown("<div class='big-header'>Phase 1: One-Shot Pass</div>", unsafe_allow_html=True)
    
    if st.session_state.phase1_status == "Pending":
        c1, c2, c3 = st.columns(3)
        c1.metric("Prop Size", f"${p1['prop_size']:,.0f}")
        c2.metric("CEX Size", f"${p1['cex_size']:,.0f}")
        c3.metric("Daily Limit", f"${acct_size*daily_dd_pct:,.0f}")
        
        # SAFETY WARNING
        net_profit_fail = p1['fail_refund'] - fee
        if net_profit_fail < 0:
            st.markdown(f"""
            <div class='warning-box'>
            ⚠️ <b>DANGER: Ratio Too High</b><br>
            If you hit SL, you lose <b>${abs(net_profit_fail):.2f}</b>.<br>
            Because of trailing drawdown, we only calculate refund based on <b>One Trade Risk</b> ({risk_per_trade_pct*100}%), not the full 8%.
            </div>
            """, unsafe_allow_html=True)

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
            <div class="fail-header">❌ Phase 1 Failed</div>
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
        st.markdown("<div class='big-header'>Phase 2: One-Shot Pass</div>", unsafe_allow_html=True)
        
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
    st.markdown("<div class='big-header'>Funded Phase: Sniper Mode</div>", unsafe_allow_html=True)
    st.markdown("""
    <div style='background-color:#1c1c1c; padding:10px; border-radius:5px; margin-bottom:15px; border-left:3px solid #FFD700;'>
    <b>Strategy:</b> Target a specific withdrawal amount in <b>ONE</b> trade. 
    If you lose, the account is burned (Trailing Drawdown), but you profit on CEX.
    </div>
    """, unsafe_allow_html=True)

    target_profit_amt = st.number_input("I want to withdraw this amount ($):", value=2000.0, step=100.0)
    
    if target_profit_amt < 50:
        st.warning("⚠️ Minimum withdrawal is $50.")
    
    f_ratio = st.slider("Hedge Ratio (CEX Risk per $1 Prop)", 0.1, 2.0, 0.75, 0.01)

    # CALC
    f_metrics = calculate_metrics(target_profit_amt, 0, is_funded=True, funded_ratio=f_ratio)
    
    payout_gross = target_profit_amt * 0.90
    monthly_net = payout_gross - f_metrics['pass_cost']
    fail_net = f_metrics['fail_refund'] - total_sunk
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""
        <div class="result-card" style="border: 1px solid #00FF7F;">
            <div class="pass-header">SCENARIO A: SNIPE & WITHDRAW</div>
            <div class="money-row"><span>Goal:</span><span style="color:white;">${target_profit_amt:,.2f}</span></div>
            <div class="money-row"><span>Payout (90%):</span><span class="money-pos">+${payout_gross:,.2f}</span></div>
            <div class="money-row"><span>Hedge Cost:</span><span class="money-neg">-${f_metrics['pass_cost']:,.2f}</span></div>
            <div class="total-row"><span>NET PROFIT:</span><span class="{'money-pos' if monthly_net>0 else 'money-neg'}">${monthly_net:,.2f}</span></div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="result-card" style="border: 1px solid #FF4B4B;">
            <div class="fail-header">SCENARIO B: MISS & BURN</div>
            <div class="money-row"><span>Refund (1 Trade Risk):</span><span class="money-pos">+${f_metrics['fail_refund']:,.2f}</span></div>
            <div class="money-row"><span>Sunk Costs:</span><span class="money-neg">-${total_sunk:,.2f}</span></div>
            <div class="total-row"><span>EXIT PROFIT:</span><span class="{'money-pos' if fail_net>0 else 'money-neg'}">${fail_net:,.2f}</span></div>
        </div>
        """, unsafe_allow_html=True)
        
    if monthly_net < 0:
        st.error("⚠️ Unprofitable: Hedge Cost > Payout. Lower your ratio.")
