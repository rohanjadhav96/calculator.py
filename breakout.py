import streamlit as st
import pandas as pd
import math

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Breakout Hedge Commander", layout="wide", page_icon="🛡️")

# --- SESSION STATE ---
if 'phase1_status' not in st.session_state: st.session_state.phase1_status = "Pending"
if 'phase2_status' not in st.session_state: st.session_state.phase2_status = "Pending"
# Default Presets (Kitakita)
if 'risk_p1' not in st.session_state: st.session_state.risk_p1 = 3.6
if 'lev_p1' not in st.session_state: st.session_state.lev_p1 = 3.6
if 'risk_p2' not in st.session_state: st.session_state.risk_p2 = 4.8
if 'lev_p2' not in st.session_state: st.session_state.lev_p2 = 4.8

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
    .info-box { background-color: #1c1c1c; padding: 10px; border-left: 3px solid #888; font-size: 0.9em; color: #ccc; margin-bottom: 10px; }
    .success-box { background-color: #0a1f0a; padding: 10px; border-left: 3px solid #00FF7F; font-size: 0.9em; color: #ccffcc; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Breakout Hedge Commander v35")
st.caption("Final Audit: Advanced Risk/Leverage & Exact Pricing")

# --- SIDEBAR ---
with st.sidebar:
    st.header("1. Strategy Presets")
    st.markdown("""
    <div class='info-box'>
    <b>Presets (Kitakita):</b><br>
    • <b>Phase 1:</b> 3.6% Risk | 3.6x Lev<br>
    • <b>Phase 2:</b> 4.8% Risk | 4.8x Lev
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("⚡ RESET DEFAULTS"):
        st.session_state.risk_p1 = 3.6; st.session_state.lev_p1 = 3.6
        st.session_state.risk_p2 = 4.8; st.session_state.lev_p2 = 4.8
        st.rerun()

    st.markdown("---")
    st.header("2. Account Configuration")
    
    num_accounts = st.number_input("Active Accounts (Multiplier)", min_value=1, max_value=50, value=1)
    acct_choice = st.selectbox("Select Account Size", [25000, 50000, 100000], index=1)
    split_choice = st.radio("Profit Split", ["90% (Pro)", "80% (Standard)"], horizontal=True)
    apply_discount = st.checkbox("Apply 2% Discount Code?", value=False)
    
    # FEE LOGIC (Corrected Structure)
    # 25k: Base 250 | +25 for 90%
    # 50k: Base 450 | +45 for 90%
    # 100k: Base 750 | +75 for 90%
    if acct_choice == 25000: base_fee = 250; add_on = 25
    elif acct_choice == 50000: base_fee = 450; add_on = 45
    elif acct_choice == 100000: base_fee = 750; add_on = 75
        
    raw_fee = base_fee + add_on if "90%" in split_choice else base_fee
    final_fee = raw_fee * 0.98 if apply_discount else raw_fee
    
    st.metric("Fee (Per Account)", f"${final_fee:.2f}")
    if num_accounts > 1:
        st.caption(f"Total Investment: ${final_fee * num_accounts:,.2f}")
    
    acct_size = acct_choice
    fee = final_fee
    profit_split_pct = 0.90 if "90%" in split_choice else 0.80
    
    st.header("3. Advanced Risk Settings")
    st.markdown("<div class='success-box'><b>Note:</b> You can now set Risk (Loss Amount) and Leverage (Position Size) separately.</div>", unsafe_allow_html=True)
    
    max_dd_pct = st.number_input("Max Drawdown Limit (%)", 8.0) / 100
    
    st.markdown("**Phase 1 Settings**")
    c1, c2 = st.columns(2)
    risk_p1_in = c1.number_input("P1 Risk (%)", 0.1, 10.0, st.session_state.risk_p1, 0.1) / 100
    lev_p1_in = c2.number_input("P1 Leverage (x)", 1.0, 20.0, st.session_state.lev_p1, 0.1)

    st.markdown("**Phase 2 / Funded Settings**")
    c3, c4 = st.columns(2)
    risk_p2_in = c3.number_input("P2 Risk (%)", 0.1, 10.0, st.session_state.risk_p2, 0.1) / 100
    lev_p2_in = c4.number_input("P2 Leverage (x)", 1.0, 20.0, st.session_state.lev_p2, 0.1)
    
    # Calculate Implied Stop Loss
    sl_p1 = risk_p1_in / lev_p1_in
    sl_p2 = risk_p2_in / lev_p2_in
    st.caption(f"ℹ️ Implied SL Distance: P1 **{sl_p1*100:.2f}%** | P2 **{sl_p2*100:.2f}%**")
    
    st.header("4. Hedge Ratios")
    ratio_p1 = st.number_input("Phase 1 Ratio", min_value=0.01, max_value=100.0, value=5.8, step=0.1, format="%.2f")
    ratio_p2 = st.number_input("Phase 2 Ratio", min_value=0.01, max_value=100.0, value=3.2, step=0.1, format="%.2f")
    
    st.markdown("---")
    st.header("5. Commissions")
    prop_comm_rate = st.number_input("Prop Commission (%)", 0.04, format="%.4f") / 100
    zero_cex_fees = st.checkbox("🔥 Use Zero-Fee CEX?", value=True)
    cex_comm_rate = 0.0 if zero_cex_fees else (st.number_input("CEX Commission (%)", 0.04, format="%.4f") / 100)
    
    include_swap = st.checkbox("Include Swap Fees?", value=False)
    swap_rate = 0.0
    days_held = 0.0
    if include_swap:
        swap_rate = st.number_input("Swap Rate (%)", 0.03, format="%.4f") / 100
        days_held = st.number_input("Avg Days Held", value=1)

# --- ENGINE ---
def calculate_metrics(target_profit, ratio_val, risk_pct, leverage, is_funded=False, funded_ratio=0.0):
    # 1. RISK Amount (Loss if SL hit)
    risk_usd = acct_size * risk_pct
    
    # 2. POSITION SIZE (Based on Leverage)
    prop_size = acct_size * leverage
    
    if is_funded:
        cex_size = prop_size * funded_ratio
    else:
        cex_size = prop_size / ratio_val

    # 3. FRICTION (Based on SIZE, not Risk)
    prop_fric_pass = (prop_size * prop_comm_rate * 2) + ((prop_size * swap_rate * days_held) if include_swap else 0)
    cex_fric_pass = (cex_size * cex_comm_rate * 2) + ((cex_size * swap_rate * days_held) if include_swap else 0)
    
    # Fail: Scale friction by volume needed to drain account
    total_drain = acct_size * max_dd_pct
    volume_multiplier = max_dd_pct / risk_pct
    
    total_fail_volume_prop = prop_size * volume_multiplier
    if is_funded:
        total_fail_volume_cex = total_fail_volume_prop * funded_ratio
    else:
        total_fail_volume_cex = total_fail_volume_prop / ratio_val
        
    prop_fric_fail = (total_fail_volume_prop * prop_comm_rate * 2) + ((total_fail_volume_prop * swap_rate * days_held) if include_swap else 0)
    cex_fric_fail = (total_fail_volume_cex * cex_comm_rate * 2) + ((total_fail_volume_cex * swap_rate * days_held) if include_swap else 0)
    
    # PASS LOGIC
    prop_gross = target_profit + prop_fric_pass
    if is_funded:
        cex_loss_pass = (prop_gross * funded_ratio) + cex_fric_pass
    else:
        cex_loss_pass = (prop_gross / ratio_val) + cex_fric_pass

    # FAIL LOGIC
    if is_funded:
        cex_win_gross = total_drain * funded_ratio
    else:
        cex_win_gross = total_drain / ratio_val
        
    cex_win_net = cex_win_gross - cex_fric_fail

    return {
        "pass_cost": cex_loss_pass, 
        "fail_refund": cex_win_net, 
        "prop_size": prop_size, 
        "cex_size": cex_size
    }

# --- CALCULATIONS ---
p1 = calculate_metrics(acct_size * 0.05, ratio_p1, risk_p1_in, lev_p1_in)
p2 = calculate_metrics(acct_size * 0.10, ratio_p2, risk_p2_in, lev_p2_in)

total_sunk = fee + p1['pass_cost'] + p2['pass_cost']

# --- TABS ---
t1, t2, t3 = st.tabs(["Phase 1", "Phase 2", "Funded Phase"])

# === PHASE 1 ===
with t1:
    st.markdown("<div class='big-header'>Phase 1: One-Shot Pass</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='info-box'>Risking <b>{risk_p1_in*100:.1f}%</b> (${acct_size*risk_p1_in:,.0f}) using <b>{lev_p1_in}x Leverage</b>.</div>", unsafe_allow_html=True)
    
    if st.session_state.phase1_status == "Pending":
        c1, c2, c3 = st.columns(3)
        c1.metric("Prop Size", f"${p1['prop_size']:,.0f}")
        c2.metric("CEX Size", f"${p1['cex_size']:,.0f}")
        c3.metric("Est. SL Distance", f"{sl_p1*100:.2f}%")
        
        pass_cost_disp = p1['pass_cost'] * num_accounts
        fail_refund_disp = p1['fail_refund'] * num_accounts
        
        col_pass, col_fail = st.columns(2)
        with col_pass:
            st.info(f"Total Cost to Pass ({num_accounts}x): -${pass_cost_disp:,.2f}")
            if st.button("Phase 1 PASSED", key="p1_pass"): st.session_state.phase1_status="Passed"; st.rerun()
        with col_fail:
            st.error(f"Total Refund if Fail ({num_accounts}x): +${fail_refund_disp:,.2f}")
            if st.button("Phase 1 FAILED", key="p1_fail"): st.session_state.phase1_status="Failed"; st.rerun()

    elif st.session_state.phase1_status == "Passed":
        total_fee_disp = fee * num_accounts
        total_hedge_disp = p1['pass_cost'] * num_accounts
        total_sunk_disp = (fee + p1['pass_cost']) * num_accounts
        
        html_p1 = f"""
        <div class="result-card" style="border-left: 5px solid #00FF7F;">
            <div class="pass-header">✅ Phase 1 Passed ({num_accounts} Accts)</div>
            <div class="money-row"><span>Fees Paid:</span><span class="money-neg">-${total_fee_disp:,.2f}</span></div>
            <div class="money-row"><span>Hedge Cost:</span><span class="money-neg">-${total_hedge_disp:,.2f}</span></div>
            <div class="total-row"><span>Total Sunk:</span><span class="money-neg">-${total_sunk_disp:,.2f}</span></div>
        </div>"""
        st.markdown(html_p1, unsafe_allow_html=True)
        if st.button("Undo Phase 1"): st.session_state.phase1_status="Pending"; st.rerun()

    elif st.session_state.phase1_status == "Failed":
        total_refund_disp = p1['fail_refund'] * num_accounts
        total_fee_disp = fee * num_accounts
        net_profit_disp = total_refund_disp - total_fee_disp
        
        html_fail = f"""
        <div class="result-card" style="border-left: 5px solid #FF4B4B;">
            <div class="fail-header">❌ Phase 1 Failed ({num_accounts} Accts)</div>
            <div class="money-row"><span>Total Refund:</span><span class="money-pos">+${total_refund_disp:,.2f}</span></div>
            <div class="money-row"><span>Fees Paid:</span><span class="money-neg">-${total_fee_disp:,.2f}</span></div>
            <div class="total-row"><span>NET PROFIT:</span><span class="{'money-pos' if net_profit_disp>0 else 'money-neg'}">${net_profit_disp:,.2f}</span></div>
        </div>"""
        st.markdown(html_fail, unsafe_allow_html=True)
        if st.button("Restart Phase 1"): st.session_state.phase1_status="Pending"; st.rerun()

# === PHASE 2 ===
with t2:
    if st.session_state.phase1_status != "Passed":
        st.warning("🔒 Complete Phase 1 first.")
    else:
        st.markdown("<div class='big-header'>Phase 2: One-Shot Pass</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='info-box'>Risking <b>{risk_p2_in*100:.1f}%</b> (${acct_size*risk_p2_in:,.0f}) using <b>{lev_p2_in}x Leverage</b>.</div>", unsafe_allow_html=True)
        
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
            p1_cost_total = p1['pass_cost'] * num_accounts
            p2_cost_total = p2['pass_cost'] * num_accounts
            total_inv_total = total_sunk * num_accounts
            
            html_p2 = f"""
            <div class="result-card" style="border-left: 5px solid #00FF7F;">
                <div class="pass-header">🏆 YOU ARE FUNDED ({num_accounts} Accts)</div>
                <div class="money-row"><span>Total Phase 1 Cost:</span><span class="money-neg">-${p1_cost_total:,.2f}</span></div>
                <div class="money-row"><span>Total Phase 2 Cost:</span><span class="money-neg">-${p2_cost_total:,.2f}</span></div>
                <div class="total-row"><span>TOTAL INVESTMENT:</span><span class="money-neg">-${total_inv_total:,.2f}</span></div>
            </div>"""
            st.markdown(html_p2, unsafe_allow_html=True)
            if st.button("Undo Phase 2"): st.session_state.phase2_status="Pending"; st.rerun()

        elif st.session_state.phase2_status == "Failed":
            total_refund_disp = p2['fail_refund'] * num_accounts
            total_sunk_prev = (fee + p1['pass_cost']) * num_accounts
            net_res_disp = total_refund_disp - total_sunk_prev
            
            html_f2 = f"""
            <div class="result-card" style="border-left: 5px solid #FF4B4B;">
                <div class="fail-header">❌ Phase 2 Failed</div>
                <div class="money-row"><span>Total Refund:</span><span class="money-pos">+${total_refund_disp:,.2f}</span></div>
                <div class="money-row"><span>Total Sunk:</span><span class="money-neg">-${total_sunk_prev:,.2f}</span></div>
                <div class="total-row"><span>NET RESULT:</span><span class="{'money-pos' if net_res_disp>0 else 'money-neg'}">${net_res_disp:,.2f}</span></div>
            </div>"""
            st.markdown(html_f2, unsafe_allow_html=True)
            if st.button("Restart Phase 2"): st.session_state.phase2_status="Pending"; st.rerun()

# === FUNDED ===
with t3:
    st.markdown("<div class='big-header'>Funded Phase: Sniper Mode</div>", unsafe_allow_html=True)
    st.markdown(f"**Live Accounts:** {num_accounts} | **Split:** {split_choice}")

    target_profit_amt = st.number_input("Target Withdrawal Amount (Per Account):", value=4000.0, step=100.0)
    
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

    # CALC PER ACCOUNT (Using P2 Risk/Lev for Funded High Speed)
    f_metrics = calculate_metrics(target_profit_amt, 0, risk_p2_in, lev_p2_in, is_funded=True, funded_ratio=f_ratio)
    
    # Per Account
    payout_one = target_profit_amt * profit_split_pct
    net_win_one = payout_one - f_metrics['pass_cost']
    net_fail_one = f_metrics['fail_refund'] - total_sunk
    
    # Totals (Live Multiplier)
    goal_total_disp = target_profit_amt * num_accounts
    payout_total_disp = payout_one * num_accounts
    hedge_cost_total_disp = f_metrics['pass_cost'] * num_accounts
    net_win_total_disp = net_win_one * num_accounts
    
    refund_total_disp = f_metrics['fail_refund'] * num_accounts
    sunk_total_disp = total_sunk * num_accounts
    net_fail_total_disp = net_fail_one * num_accounts

    # DISPLAY CARDS
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""
        <div class="result-card" style="border: 1px solid #00FF7F;">
            <div class="pass-header">SCENARIO A: SNIPE & WITHDRAW</div>
            <div class="money-row"><span>Goal ({num_accounts}x):</span><span style="color:white;">${goal_total_disp:,.2f}</span></div>
            <div class="money-row"><span>Payout:</span><span class="money-pos">+${payout_total_disp:,.2f}</span></div>
            <div class="money-row"><span>Hedge Cost:</span><span class="money-neg">-${hedge_cost_total_disp:,.2f}</span></div>
            <div class="total-row"><span>NET PROFIT:</span><span class="{'money-pos' if net_win_total_disp>0 else 'money-neg'}">${net_win_total_disp:,.2f}</span></div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="result-card" style="border: 1px solid #FF4B4B;">
            <div class="fail-header">SCENARIO B: MISS & BURN</div>
            <div class="money-row"><span>Refund (8% Drain):</span><span class="money-pos">+${refund_total_disp:,.2f}</span></div>
            <div class="money-row"><span>Sunk Costs:</span><span class="money-neg">-${sunk_total_disp:,.2f}</span></div>
            <div class="total-row"><span>EXIT PROFIT:</span><span class="{'money-pos' if net_fail_total_disp>0 else 'money-neg'}">${net_fail_total_disp:,.2f}</span></div>
        </div>
        """, unsafe_allow_html=True)
