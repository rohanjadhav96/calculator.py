import streamlit as st
import pandas as pd
import math

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Breakout Hedge Commander", layout="wide", page_icon="🛡️")

# --- SESSION STATE ---
if 'phase1_status' not in st.session_state: st.session_state.phase1_status = "Pending"
if 'phase2_status' not in st.session_state: st.session_state.phase2_status = "Pending"
if 'risk_preset' not in st.session_state: st.session_state.risk_preset = 4.8
if 'days_preset' not in st.session_state: st.session_state.days_preset = 0

# --- STYLING ---
st.markdown("""
<style>
    .big-header { font-size: 24px; font-weight: bold; color: #FFD700; margin-bottom: 15px; }
    .sub-header { font-size: 18px; font-weight: bold; color: #00BFFF; margin-top: 20px; margin-bottom: 10px; }
    .result-card { background-color: #0e1117; border: 1px solid #333; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
    .money-pos { color: #00FF7F; font-weight: bold; }
    .money-neg { color: #FF4B4B; font-weight: bold; }
    .pass-header { color: #00FF7F; font-size: 1.4em; font-weight: bold; margin-bottom: 10px; border-bottom: 1px solid #333; padding-bottom: 5px; }
    .fail-header { color: #FF4B4B; font-size: 1.4em; font-weight: bold; margin-bottom: 10px; border-bottom: 1px solid #333; padding-bottom: 5px; }
    .money-row { display: flex; justify-content: space-between; margin-bottom: 6px; }
    .total-row { display: flex; justify-content: space-between; margin-top: 15px; padding-top: 10px; border-top: 1px solid #444; font-size: 1.2em; font-weight: bold; }
    .solver-box { border: 1px solid #00BFFF; background-color: #0a1320; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
    .info-box { background-color: #1c1c1c; padding: 10px; border-left: 3px solid #888; font-size: 0.9em; color: #ccc; margin-bottom: 10px; }
    .warning-box { background-color: #2e0b0b; padding: 10px; border-left: 3px solid #FF4B4B; font-size: 0.9em; color: #ffcccc; margin-bottom: 15px; }
    .success-box { background-color: #0a1f0a; padding: 10px; border-left: 3px solid #00FF7F; font-size: 0.9em; color: #ccffcc; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Breakout Hedge Commander")
st.caption("Strategic Arbitrage Calculator & Execution Planner")

# --- SIDEBAR ---
with st.sidebar:
    st.header("1. Strategy Presets")
    st.markdown("""
    <div class='info-box'>
    <b>Strategy: One-Shot (Sniper)</b><br>
    Risk ~4.8% to pass in 1 trade.<br>
    Fail drains FULL 8% for max refund.
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("⚡ RESET DEFAULTS"):
        st.session_state.risk_preset = 4.8
        st.session_state.days_preset = 0 
        st.rerun()

    st.markdown("---")
    st.header("2. Account Configuration")
    
    # LIVE ACCOUNT TRACKER
    num_accounts = st.number_input("Active Accounts (Multiplier)", min_value=1, max_value=50, value=1)
    
    # ACCOUNT SELECTION
    acct_choice = st.selectbox("Select Account Size", [25000, 50000, 100000], index=1)
    split_choice = st.radio("Profit Split", ["90% (Pro)", "80% (Standard)"], horizontal=True)
    apply_discount = st.checkbox("Apply 2% Discount Code?", value=False)
    
    # FEE LOGIC
    # 25k: Base 250 | +25 for 90%
    # 50k: Base 450 | +45 for 90%
    # 100k: Base 750 | +75 for 90%
    
    if acct_choice == 25000:
        base_fee = 250
        add_on = 25
    elif acct_choice == 50000:
        base_fee = 450
        add_on = 45
    elif acct_choice == 100000:
        base_fee = 750
        add_on = 75
        
    raw_fee = base_fee + add_on if "90%" in split_choice else base_fee
    final_fee = raw_fee * 0.98 if apply_discount else raw_fee
    
    # Display Inputs
    st.metric("Required Fee (Per Account)", f"${final_fee:.2f}")
    if num_accounts > 1:
        st.caption(f"Total Investment: ${final_fee * num_accounts:,.2f}")
    
    # Store for calculations
    acct_size = acct_choice
    fee = final_fee
    profit_split_pct = 0.90 if "90%" in split_choice else 0.80
    
    st.header("3. Risk Management")
    st.markdown("<div class='success-box'><b>Note:</b> Since Trailing Drawdown is static while open, we target the full profit in <b>1 Trade</b>.</div>", unsafe_allow_html=True)
    
    max_dd_pct = st.number_input("Max Drawdown Limit (%)", 8.0) / 100
    daily_dd_pct = st.number_input("Daily Drawdown Limit (%)", 5.0) / 100
    risk_per_trade_pct = st.number_input("RISK PER TRADE (%)", value=st.session_state.risk_preset, step=0.1, format="%.1f") / 100
    
    st.header("4. Hedge Ratios")
    # UPDATED: Unlocked Ratios (Min 0.01, Max 100.0)
    ratio_p1 = st.number_input("Phase 1 Ratio", min_value=0.01, max_value=100.0, value=5.8, step=0.1, format="%.2f")
    ratio_p2 = st.number_input("Phase 2 Ratio", min_value=0.01, max_value=100.0, value=3.2, step=0.1, format="%.2f")
    
    st.markdown("---")
    st.header("5. Commissions")
    prop_comm_rate = st.number_input("Prop Commission (%)", 0.04, format="%.4f") / 100
    zero_cex_fees = st.checkbox("🔥 Use Zero-Fee CEX?", value=True)
    
    if zero_cex_fees:
        cex_comm_rate = 0.0
    else:
        cex_comm_rate = st.number_input("CEX Commission (%)", 0.04, format="%.4f") / 100
    
    include_swap = st.checkbox("Include Swap Fees?", value=False)
    swap_rate = 0.0
    days_held = 0.0
    if include_swap:
        swap_rate = st.number_input("Swap Rate (%)", 0.03, format="%.4f") / 100
        days_held = st.number_input("Avg Days Held", value=1)

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
    prop_fric = (prop_size * prop_comm_rate * 2) + ((prop_size * swap_rate * days_held) if include_swap else 0)
    cex_fric = (cex_size * cex_comm_rate * 2) + ((cex_size * swap_rate * days_held) if include_swap else 0)
    
    # PASS LOGIC
    prop_gross = target_profit + prop_fric
    if is_funded:
        cex_loss_pass = (prop_gross * funded_ratio) + cex_fric
    else:
        cex_loss_pass = (prop_gross / ratio_val) + cex_fric

    # FAIL LOGIC (Full 8% Drain)
    total_drain = acct_size * max_dd_pct
    volume_multiplier = max_dd_pct / risk_per_trade_pct
    
    if is_funded:
        cex_win_gross = total_drain * funded_ratio
    else:
        cex_win_gross = total_drain / ratio_val
        
    cex_win_net = cex_win_gross - (cex_fric * volume_multiplier)

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
        c3.metric("One-Shot Risk", f"${acct_size*risk_per_trade_pct:,.0f}")
        
        # Display Totals
        pass_cost_disp = p1['pass_cost'] * num_accounts
        fail_refund_disp = p1['fail_refund'] * num_accounts
        
        col_pass, col_fail = st.columns(2)
        with col_pass:
            st.info(f"Total Cost to Pass ({num_accounts}x): -${pass_cost_disp:,.2f}")
            if st.button("Phase 1 PASSED", key="p1_pass"): st.session_state.phase1_status="Passed"; st.rerun()
        with col_fail:
            st.error(f"Total Refund if Fail ({num_accounts}x): +${fail_refund_disp:,.2f}")
            if st.button("Phase 1 FAILED", key="p1_fail"): st.session_state.phase1_status="Failed"; st.rerun()

        st.caption(f"ℹ️ Refund based on Full {max_dd_pct*100}% Drain.")

    elif st.session_state.phase1_status == "Passed":
        html_p1 = f"""
        <div class="result-card" style="border-left: 5px solid #00FF7F;">
            <div class="pass-header">✅ Phase 1 Passed ({num_accounts} Accts)</div>
            <div class="money-row"><span>Fees Paid:</span><span class="money-neg">-${fee*num_accounts:,.2f}</span></div>
            <div class="money-row"><span>Hedge Cost:</span><span class="money-neg">-${p1['pass_cost']*num_accounts:,.2f}</span></div>
            <div class="total-row"><span>Total Sunk:</span><span class="money-neg">-${(fee+p1['pass_cost'])*num_accounts:,.2f}</span></div>
        </div>"""
        st.markdown(html_p1, unsafe_allow_html=True)
        if st.button("Undo Phase 1"): st.session_state.phase1_status="Pending"; st.rerun()

    elif st.session_state.phase1_status == "Failed":
        net = (p1['fail_refund'] - fee) * num_accounts
        html_fail = f"""
        <div class="result-card" style="border-left: 5px solid #FF4B4B;">
            <div class="fail-header">❌ Phase 1 Failed ({num_accounts} Accts)</div>
            <div class="money-row"><span>Total Refund:</span><span class="money-pos">+${p1['fail_refund']*num_accounts:,.2f}</span></div>
            <div class="money-row"><span>Fees Paid:</span><span class="money-neg">-${fee*num_accounts:,.2f}</span></div>
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
        
        pass_cost_disp = p2['pass_cost'] * num_accounts
        fail_refund_disp = p2['fail_refund'] * num_accounts
        
        if st.session_state.phase2_status == "Pending":
            col_pass, col_fail = st.columns(2)
            with col_pass:
                st.info(f"Total Cost to Pass ({num_accounts}x): -${pass_cost_disp:,.2f}")
                if st.button("Phase 2 PASSED", key="p2_pass"): st.session_state.phase2_status="Passed"; st.rerun()
            with col_fail:
                st.error(f"Total Refund if Fail ({num_accounts}x): +${fail_refund_disp:,.2f}")
                if st.button("Phase 2 FAILED", key="p2_fail"): st.session_state.phase2_status="Failed"; st.rerun()

        elif st.session_state.phase2_status == "Passed":
            total_inv = total_sunk * num_accounts
            html_p2 = f"""
            <div class="result-card" style="border-left: 5px solid #00FF7F;">
                <div class="pass-header">🏆 YOU ARE FUNDED ({num_accounts} Accts)</div>
                <div class="money-row"><span>Total Phase 1 Cost:</span><span class="money-neg">-${p1['pass_cost']*num_accounts:,.2f}</span></div>
                <div class="money-row"><span>Total Phase 2 Cost:</span><span class="money-neg">-${p2['pass_cost']*num_accounts:,.2f}</span></div>
                <div class="total-row"><span>TOTAL INVESTMENT:</span><span class="money-neg">-${total_inv:,.2f}</span></div>
            </div>"""
            st.markdown(html_p2, unsafe_allow_html=True)
            if st.button("Undo Phase 2"): st.session_state.phase2_status="Pending"; st.rerun()

        elif st.session_state.phase2_status == "Failed":
            prev_sunk = (fee + p1['pass_cost']) * num_accounts
            net = fail_refund_disp - prev_sunk
            html_f2 = f"""
            <div class="result-card" style="border-left: 5px solid #FF4B4B;">
                <div class="fail-header">❌ Phase 2 Failed</div>
                <div class="money-row"><span>Total Refund:</span><span class="money-pos">+${fail_refund_disp:,.2f}</span></div>
                <div class="money-row"><span>Total Sunk:</span><span class="money-neg">-${prev_sunk:,.2f}</span></div>
                <div class="total-row"><span>NET RESULT:</span><span class="{'money-pos' if net>0 else 'money-neg'}">${net:,.2f}</span></div>
            </div>"""
            st.markdown(html_f2, unsafe_allow_html=True)
            if st.button("Restart Phase 2"): st.session_state.phase2_status="Pending"; st.rerun()

# === FUNDED ===
with t3:
    st.markdown("<div class='big-header'>Funded Phase: Sniper Mode</div>", unsafe_allow_html=True)
    st.markdown(f"**Live Accounts:** {num_accounts} | **Split:** {split_choice}")

    target_profit_amt = st.number_input("Target Withdrawal Amount (Per Account):", value=4000.0, step=100.0)
    
    # 1. RATIO SELECTOR
    col_tools, col_ratio = st.columns([1, 2])
    with col_tools:
        st.markdown("**Tools:**")
        if st.button("🧪 Auto-Breakeven Ratio"):
            full_drain = acct_size * max_dd_pct
            safe_ratio = total_sunk / full_drain
            if safe_ratio > 2.0: safe_ratio = 2.0
            st.session_state.funded_ratio = safe_ratio
            st.success(f"Set to {safe_ratio:.2f}")
            st.rerun()
            
    with col_ratio:
        if 'funded_ratio' not in st.session_state: st.session_state.funded_ratio = 0.75
        f_ratio = st.slider("Hedge Ratio (CEX Risk per $1 Prop)", 0.1, 2.0, st.session_state.funded_ratio, 0.01)
        st.session_state.funded_ratio = f_ratio

    # CALC PER ACCOUNT
    f_metrics = calculate_metrics(target_profit_amt, 0, is_funded=True, funded_ratio=f_ratio)
    
    # Per Account
    payout_one = target_profit_amt * profit_split_pct
    net_win_one = payout_one - f_metrics['pass_cost']
    net_fail_one = f_metrics['fail_refund'] - total_sunk
    
    # Totals (Live Multiplier)
    monthly_net_total = net_win_one * num_accounts
    fail_net_total = net_fail_one * num_accounts

    # DISPLAY CARDS
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""
        <div class="result-card" style="border: 1px solid #00FF7F;">
            <div class="pass-header">SCENARIO A: SNIPE & WITHDRAW</div>
            <div class="money-row"><span>Goal ({num_accounts}x):</span><span style="color:white;">${target_profit_amt*num_accounts:,.2f}</span></div>
            <div class="money-row"><span>Payout:</span><span class="money-pos">+${payout_one*num_accounts:,.2f}</span></div>
            <div class="money-row"><span>Hedge Cost:</span><span class="money-neg">-${f_metrics['pass_cost']*num_accounts:,.2f}</span></div>
            <div class="total-row"><span>NET PROFIT:</span><span class="{'money-pos' if monthly_net_total>0 else 'money-neg'}">${monthly_net_total:,.2f}</span></div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="result-card" style="border: 1px solid #FF4B4B;">
            <div class="fail-header">SCENARIO B: MISS & BURN</div>
            <div class="money-row"><span>Refund (8% Drain):</span><span class="money-pos">+${f_metrics['fail_refund']*num_accounts:,.2f}</span></div>
            <div class="money-row"><span>Sunk Costs:</span><span class="money-neg">-${total_sunk*num_accounts:,.2f}</span></div>
            <div class="total-row"><span>EXIT PROFIT:</span><span class="{'money-pos' if fail_net_total>0 else 'money-neg'}">${fail_net_total:,.2f}</span></div>
        </div>
        """, unsafe_allow_html=True)
