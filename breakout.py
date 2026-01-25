import streamlit as st
import pandas as pd
import math

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Breakout Hedge Commander", layout="wide", page_icon="🛡️")

# --- SESSION STATE INITIALIZATION ---
if 'phase1_status' not in st.session_state: st.session_state.phase1_status = "Pending"
if 'phase2_status' not in st.session_state: st.session_state.phase2_status = "Pending"

# Initialize Presets
if 'risk_p1' not in st.session_state: st.session_state.risk_p1 = 3.6
if 'lev_p1' not in st.session_state: st.session_state.lev_p1 = 3.6
if 'risk_p2' not in st.session_state: st.session_state.risk_p2 = 4.8
if 'lev_p2' not in st.session_state: st.session_state.lev_p2 = 4.8
if 'ratio_p1_set' not in st.session_state: st.session_state.ratio_p1_set = 5.8
if 'ratio_p2_set' not in st.session_state: st.session_state.ratio_p2_set = 3.2

# --- STYLING ---
st.markdown("""
<style>
    .big-header { font-size: 24px; font-weight: bold; color: #FFD700; margin-bottom: 15px; }
    .result-card { background-color: #0e1117; border: 1px solid #333; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
    .money-pos { color: #00FF7F; font-weight: bold; }
    .money-neg { color: #FF4B4B; font-weight: bold; }
    .money-neu { color: #888; font-weight: bold; }
    .pass-header { color: #00FF7F; font-size: 1.4em; font-weight: bold; margin-bottom: 10px; border-bottom: 1px solid #333; padding-bottom: 5px; }
    .fail-header { color: #FF4B4B; font-size: 1.4em; font-weight: bold; margin-bottom: 10px; border-bottom: 1px solid #333; padding-bottom: 5px; }
    .money-row { display: flex; justify-content: space-between; margin-bottom: 6px; }
    .total-row { display: flex; justify-content: space-between; margin-top: 15px; padding-top: 10px; border-top: 1px solid #444; font-size: 1.2em; font-weight: bold; }
    .info-box { background-color: #1c1c1c; padding: 10px; border-left: 3px solid #888; font-size: 0.9em; color: #ccc; margin-bottom: 10px; }
    .success-box { background-color: #0a1f0a; padding: 10px; border-left: 3px solid #00FF7F; font-size: 0.9em; color: #ccffcc; margin-bottom: 10px; }
    .farm-box { background-color: #1a1a0a; padding: 10px; border-left: 3px solid #FFD700; font-size: 0.9em; color: #fffacd; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Breakout Hedge Commander v39")
st.caption("Visual Fix: Explicit Fee Tracking in Phase 2")

# --- SIDEBAR ---
with st.sidebar:
    st.header("1. Choose Your Mode")
    
    # PRESET BUTTONS
    c_farm, c_pro = st.columns(2)
    
    if c_farm.button("💸 CASH FARMER"):
        st.session_state.risk_p1 = 4.5
        st.session_state.lev_p1 = 5.0
        st.session_state.ratio_p1_set = 4.2
        st.session_state.risk_p2 = 4.8
        st.session_state.lev_p2 = 4.8
        st.session_state.ratio_p2_set = 3.2
        st.rerun()
        
    if c_pro.button("🏆 PRO TRADER"):
        st.session_state.risk_p1 = 3.6
        st.session_state.lev_p1 = 3.6
        st.session_state.ratio_p1_set = 5.8
        st.session_state.risk_p2 = 4.8
        st.session_state.lev_p2 = 4.8
        st.session_state.ratio_p2_set = 3.2
        st.rerun()

    if st.session_state.risk_p1 < 5.0 and st.session_state.ratio_p1_set < 5.0:
        st.markdown("""<div class='farm-box'><b>Mode: Split Cash Farm</b><br>Target: Burn 4.5% Today.</div>""", unsafe_allow_html=True)
    else:
        st.markdown("""<div class='success-box'><b>Mode: Pro Trader</b><br>Target: Safe Pass.</div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.header("2. Account Configuration")
    
    num_accounts = st.number_input("Active Accounts (Multiplier)", min_value=1, max_value=50, value=1)
    acct_choice = st.selectbox("Select Account Size", [25000, 50000, 100000], index=1)
    split_choice = st.radio("Profit Split", ["90% (Pro)", "80% (Standard)"], horizontal=True)
    apply_discount = st.checkbox("Apply 2% Discount Code?", value=False)
    
    if acct_choice == 25000: base_fee = 250; add_on = 25
    elif acct_choice == 50000: base_fee = 450; add_on = 45
    elif acct_choice == 100000: base_fee = 750; add_on = 75
        
    raw_fee = base_fee + add_on if "90%" in split_choice else base_fee
    final_fee = raw_fee * 0.98 if apply_discount else raw_fee
    
    st.metric("Fee (Per Account)", f"${final_fee:.2f}")
    
    acct_size = acct_choice
    fee = final_fee
    profit_split_pct = 0.90 if "90%" in split_choice else 0.80
    
    st.header("3. Risk & Leverage")
    max_dd_pct = st.number_input("Max Drawdown Limit (%)", 8.0) / 100
    
    st.markdown("**Phase 1 Settings (Daily)**")
    c1, c2 = st.columns(2)
    risk_p1_in = c1.number_input("P1 Daily Risk (%)", 0.1, 10.0, st.session_state.risk_p1, 0.1) / 100
    lev_p1_in = c2.number_input("P1 Leverage (x)", 1.0, 20.0, st.session_state.lev_p1, 0.1)

    st.markdown("**Phase 2 / Funded Settings**")
    c3, c4 = st.columns(2)
    risk_p2_in = c3.number_input("P2 Risk (%)", 0.1, 10.0, st.session_state.risk_p2, 0.1) / 100
    lev_p2_in = c4.number_input("P2 Leverage (x)", 1.0, 20.0, st.session_state.lev_p2, 0.1)
    
    st.header("4. Hedge Ratios")
    ratio_p1 = st.number_input("Phase 1 Ratio", min_value=0.01, max_value=100.0, value=st.session_state.ratio_p1_set, step=0.1, format="%.2f")
    ratio_p2 = st.number_input("Phase 2 Ratio", min_value=0.01, max_value=100.0, value=st.session_state.ratio_p2_set, step=0.1, format="%.2f")
    
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
    risk_usd = acct_size * risk_pct
    prop_size = acct_size * leverage
    
    if is_funded:
        cex_size = prop_size * funded_ratio
    else:
        cex_size = prop_size / ratio_val

    # Friction Pass
    prop_fric_pass = (prop_size * prop_comm_rate * 2) + ((prop_size * swap_rate * days_held) if include_swap else 0)
    cex_fric_pass = (cex_size * cex_comm_rate * 2) + ((cex_size * swap_rate * days_held) if include_swap else 0)
    
    # Friction Fail (Trade Only)
    prop_fric_trade = (prop_size * prop_comm_rate * 2) + ((prop_size * swap_rate * days_held) if include_swap else 0)
    cex_fric_trade = (cex_size * cex_comm_rate * 2) + ((cex_size * swap_rate * days_held) if include_swap else 0)
    
    # Friction Fail (Full Drain)
    total_drain = acct_size * max_dd_pct
    vol_mult = max_dd_pct / risk_pct
    prop_fric_drain = prop_fric_trade * vol_mult
    cex_fric_drain = cex_fric_trade * vol_mult
    
    # Fail Trade Net
    if is_funded:
        cex_win_gross_trade = risk_usd * funded_ratio
    else:
        cex_win_gross_trade = risk_usd / ratio_val
    cex_win_net_trade = cex_win_gross_trade - cex_fric_trade
    
    # Fail Drain Net
    if is_funded:
        cex_win_gross_drain = total_drain * funded_ratio
    else:
        cex_win_gross_drain = total_drain / ratio_val
    cex_win_net_drain = cex_win_gross_drain - cex_fric_drain

    # Pass Cost
    prop_gross = target_profit + prop_fric_pass
    if is_funded:
        cex_loss_pass = (prop_gross * funded_ratio) + cex_fric_pass
    else:
        cex_loss_pass = (prop_gross / ratio_val) + cex_fric_pass

    return {
        "pass_cost": cex_loss_pass, 
        "fail_refund_trade": cex_win_net_trade,
        "fail_refund_full": cex_win_net_drain,
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
    st.markdown("<div class='big-header'>Phase 1: Daily Execution</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='info-box'>Risking <b>{risk_p1_in*100:.1f}%</b> (${acct_size*risk_p1_in:,.0f}) today.</div>", unsafe_allow_html=True)
    
    if st.session_state.phase1_status == "Pending":
        c1, c2, c3 = st.columns(3)
        c1.metric("Prop Size", f"${p1['prop_size']:,.0f}")
        c2.metric("CEX Size", f"${p1['cex_size']:,.0f}")
        c3.metric("Daily Refund", f"${p1['fail_refund_trade']:,.2f}")
        
        pass_cost_disp = p1['pass_cost'] * num_accounts
        daily_refund_disp = p1['fail_refund_trade'] * num_accounts
        full_refund_disp = p1['fail_refund_full'] * num_accounts
        
        # Split Drain
        remaining_refund_disp = full_refund_disp - daily_refund_disp
        if remaining_refund_disp < 0: remaining_refund_disp = 0
        
        col_pass, col_fail = st.columns(2)
        with col_pass:
            st.info(f"Cost if Pass: -${pass_cost_disp:,.2f}")
            if st.button("Phase 1 PASSED", key="p1_pass"): st.session_state.phase1_status="Passed"; st.rerun()
        
        with col_fail:
            fees_paid = fee * num_accounts
            net_today = daily_refund_disp - fees_paid
            
            card_html = f"""
            <div class="result-card" style="border-left: 5px solid #FF4B4B;">
                <div class="fail-header">SCENARIO B: STRATEGIC FAIL</div>
                <div class="money-row"><span><b>Day 1 Refund ({risk_p1_in*100:.1f}%):</b></span><span class="money-pos">+${daily_refund_disp:,.2f}</span></div>
                <div class="money-row"><span>Fees Paid (Upfront):</span><span class="money-neg">-${fees_paid:,.2f}</span></div>
                <div class="money-row" style="border-top:1px solid #333; padding-top:5px;"><span><b>Day 1 Net Cash:</b></span><span class="{'money-pos' if net_today>0 else 'money-neg'}">${net_today:,.2f}</span></div>
                <br>
                <div class="money-row"><span>Day 2 Reserve:</span><span class="money-neu">+${remaining_refund_disp:,.2f}</span></div>
            </div>"""
            st.markdown(card_html, unsafe_allow_html=True)
            
            if st.button("Phase 1 FAILED (Log Today)", key="p1_fail"): st.session_state.phase1_status="Failed"; st.rerun()

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
        st.info("Account logged as Failed. Reset to start new day.")
        if st.button("Restart Phase 1"): st.session_state.phase1_status="Pending"; st.rerun()

# === PHASE 2 ===
with t2:
    if st.session_state.phase1_status != "Passed":
        st.warning("🔒 Complete Phase 1 first.")
    else:
        st.markdown("<div class='big-header'>Phase 2: One-Shot Pass</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='info-box'>Risking <b>{risk_p2_in*100:.1f}%</b> using <b>{lev_p2_in}x Leverage</b>.</div>", unsafe_allow_html=True)
        
        pass_cost_disp = p2['pass_cost'] * num_accounts
        fail_refund_disp = p2['fail_refund_full'] * num_accounts
        
        if st.session_state.phase2_status == "Pending":
            col_pass, col_fail = st.columns(2)
            with col_pass:
                st.info(f"Total Cost to Pass ({num_accounts}x): -${pass_cost_disp:,.2f}")
                if st.button("Phase 2 PASSED", key="p2_pass"): st.session_state.phase2_status="Passed"; st.rerun()
            with col_fail:
                st.error(f"Refund if Fail (Full 8%): +${fail_refund_disp:,.2f}")
                if st.button("Phase 2 FAILED", key="p2_fail"): st.session_state.phase2_status="Failed"; st.rerun()

        elif st.session_state.phase2_status == "Passed":
            # FIXED DISPLAY LOGIC
            fee_total = fee * num_accounts
            p1_cost_total = p1['pass_cost'] * num_accounts
            p2_cost_total = p2['pass_cost'] * num_accounts
            total_inv_total = fee_total + p1_cost_total + p2_cost_total
            
            html_p2 = f"""
            <div class="result-card" style="border-left: 5px solid #00FF7F;">
                <div class="pass-header">🏆 YOU ARE FUNDED ({num_accounts} Accts)</div>
                <div class="money-row"><span>Fees Paid:</span><span class="money-neg">-${fee_total:,.2f}</span></div>
                <div class="money-row"><span>Phase 1 Hedge:</span><span class="money-neg">-${p1_cost_total:,.2f}</span></div>
                <div class="money-row"><span>Phase 2 Hedge:</span><span class="money-neg">-${p2_cost_total:,.2f}</span></div>
                <div class="total-row"><span>TOTAL INVESTMENT:</span><span class="money-neg">-${total_inv_total:,.2f}</span></div>
            </div>"""
            st.markdown(html_p2, unsafe_allow_html=True)
            if st.button("Undo Phase 2"): st.session_state.phase2_status="Pending"; st.rerun()

        elif st.session_state.phase2_status == "Failed":
            fee_total = fee * num_accounts
            p1_cost_total = p1['pass_cost'] * num_accounts
            total_sunk_prev = fee_total + p1_cost_total
            net_res_disp = fail_refund_disp - total_sunk_prev
            
            html_f2 = f"""
            <div class="result-card" style="border-left: 5px solid #FF4B4B;">
                <div class="fail-header">❌ Phase 2 Failed</div>
                <div class="money-row"><span>Total Refund (8% Drain):</span><span class="money-pos">+${fail_refund_disp:,.2f}</span></div>
                <div class="money-row"><span>Fees Paid:</span><span class="money-neg">-${fee_total:,.2f}</span></div>
                <div class="money-row"><span>Phase 1 Hedge:</span><span class="money-neg">-${p1_cost_total:,.2f}</span></div>
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

    # CALC PER ACCOUNT
    f_metrics = calculate_metrics(target_profit_amt, 0, risk_p2_in, lev_p2_in, is_funded=True, funded_ratio=f_ratio)
    
    payout_one = target_profit_amt * profit_split_pct
    net_win_one = payout_one - f_metrics['pass_cost']
    
    # Fail calc (Funded)
    total_drain = acct_size * max_dd_pct
    vol_mult = max_dd_pct / risk_p2_in
    prop_fric_fail = (f_metrics['prop_size'] * vol_mult * prop_comm_rate * 2)
    cex_fric_fail = (f_metrics['cex_size'] * vol_mult * cex_comm_rate * 2)
    
    cex_win_gross_drain = total_drain * f_ratio
    cex_win_net_drain = cex_win_gross_drain - cex_fric_fail
    
    net_fail_one = cex_win_net_drain - total_sunk
    
    # Totals
    goal_total_disp = target_profit_amt * num_accounts
    payout_total_disp = payout_one * num_accounts
    hedge_cost_total_disp = f_metrics['pass_cost'] * num_accounts
    net_win_total_disp = net_win_one * num_accounts
    
    refund_total_disp = cex_win_net_drain * num_accounts
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
            <div class="fail-header">SCENARIO B: MISS & BURN (Full Drain)</div>
            <div class="money-row"><span>Refund (8% Drain):</span><span class="money-pos">+${refund_total_disp:,.2f}</span></div>
            <div class="money-row"><span>Sunk Costs:</span><span class="money-neg">-${sunk_total_disp:,.2f}</span></div>
            <div class="total-row"><span>EXIT PROFIT:</span><span class="{'money-pos' if net_fail_total_disp>0 else 'money-neg'}">${net_fail_total_disp:,.2f}</span></div>
        </div>
        """, unsafe_allow_html=True)
