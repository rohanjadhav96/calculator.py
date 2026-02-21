import streamlit as st
import pandas as pd

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Breakout Hedge Commander v40", layout="wide", page_icon="🛡️")

# --- SESSION STATE INITIALIZATION ---
if 'phase1_status' not in st.session_state: st.session_state.phase1_status = "Pending"
if 'phase2_status' not in st.session_state: st.session_state.phase2_status = "Pending"

# Default to Standard Multipliers
if 'risk_p1' not in st.session_state: st.session_state.risk_p1 = 3.6
if 'lev_p1' not in st.session_state: st.session_state.lev_p1 = 3.6
if 'risk_p2' not in st.session_state: st.session_state.risk_p2 = 4.8
if 'lev_p2' not in st.session_state: st.session_state.lev_p2 = 4.8
if 'ratio_p1_set' not in st.session_state: st.session_state.ratio_p1_set = 0.25
if 'ratio_p2_set' not in st.session_state: st.session_state.ratio_p2_set = 0.35
if 'chal_type' not in st.session_state: st.session_state.chal_type = "Standard 2-Step"

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
    .danger-box { background-color: #2a0a0a; padding: 10px; border-left: 3px solid #FF4B4B; font-size: 0.9em; color: #ffcccc; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Breakout Hedge Commander v40")
st.caption("Update: 1-Step Pro Sniper Mode & Multiplier Ratios")

# --- SIDEBAR ---
with st.sidebar:
    st.header("1. Choose Your Mode")
    
    # PRESET BUTTONS
    c_farm, c_pro, c_1step = st.columns(3)
    
    if c_farm.button("💸 FARM"):
        st.session_state.chal_type = "Standard 2-Step"
        st.session_state.risk_p1 = 4.5
        st.session_state.lev_p1 = 5.0
        st.session_state.ratio_p1_set = 0.24
        st.session_state.risk_p2 = 4.8
        st.session_state.lev_p2 = 4.8
        st.session_state.ratio_p2_set = 0.32
        st.rerun()
        
    if c_pro.button("🏆 PRO"):
        st.session_state.chal_type = "Standard 2-Step"
        st.session_state.risk_p1 = 3.6
        st.session_state.lev_p1 = 3.6
        st.session_state.ratio_p1_set = 0.17
        st.session_state.risk_p2 = 4.8
        st.session_state.lev_p2 = 4.8
        st.session_state.ratio_p2_set = 0.32
        st.rerun()

    if c_1step.button("🎯 1-STEP"):
        st.session_state.chal_type = "1-Step Pro"
        st.session_state.risk_p1 = 2.5
        st.session_state.lev_p1 = 2.5
        st.session_state.ratio_p1_set = 0.50
        st.rerun()

    chal_type = st.radio("Challenge Type", ["Standard 2-Step", "1-Step Pro"], index=["Standard 2-Step", "1-Step Pro"].index(st.session_state.chal_type))
    st.session_state.chal_type = chal_type

    if chal_type == "1-Step Pro":
        st.markdown("""<div class='farm-box'><b>Mode: 1-Step Pro (50k)</b><br>Target: 12% | Max DD: 5%<br><i>Optimized for failing to extract cash.</i></div>""", unsafe_allow_html=True)
    else:
        st.markdown("""<div class='success-box'><b>Mode: Standard 2-Step</b><br>Target: 5% / 10% | Max DD: 8%</div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.header("2. Account Configuration")
    
    num_accounts = st.number_input("Active Accounts (Multiplier)", min_value=1, max_value=50, value=1)
    acct_choice = st.selectbox("Select Account Size", [25000, 50000, 100000], index=1)
    
    if chal_type == "1-Step Pro":
        split_choice = "90% (Pro)"
        apply_discount = True
        if acct_choice == 50000: final_fee = 395.0
        elif acct_choice == 25000: final_fee = 220.0 # Approximation, adjust as needed
        else: final_fee = 700.0
        st.info(f"Fixed 1-Step Fee: ${final_fee:.2f}")
    else:
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
    if chal_type == "1-Step Pro":
        max_dd_pct = 0.05
        target_p1_pct = 0.12
    else:
        max_dd_pct = st.number_input("Max Drawdown Limit (%)", 8.0) / 100
        target_p1_pct = 0.05
        target_p2_pct = 0.10
    
    st.markdown("**Phase 1 Settings (Daily)**")
    c1, c2 = st.columns(2)
    risk_p1_in = c1.number_input("P1 Daily Risk (%)", 0.1, 10.0, st.session_state.risk_p1, 0.1) / 100
    lev_p1_in = c2.number_input("P1 Leverage (x)", 1.0, 20.0, st.session_state.lev_p1, 0.1)

    if chal_type != "1-Step Pro":
        st.markdown("**Phase 2 Settings**")
        c3, c4 = st.columns(2)
        risk_p2_in = c3.number_input("P2 Risk (%)", 0.1, 10.0, st.session_state.risk_p2, 0.1) / 100
        lev_p2_in = c4.number_input("P2 Leverage (x)", 1.0, 20.0, st.session_state.lev_p2, 0.1)
    
    st.header("4. Hedge Ratios (Multiplier)")
    ratio_p1 = st.number_input("P1 Ratio (e.g., 0.50)", min_value=0.01, max_value=5.0, value=st.session_state.ratio_p1_set, step=0.01, format="%.2f")
    if chal_type != "1-Step Pro":
        ratio_p2 = st.number_input("P2 Ratio", min_value=0.01, max_value=5.0, value=st.session_state.ratio_p2_set, step=0.01, format="%.2f")
    else:
        ratio_p2 = 0.0
    
    st.markdown("---")
    st.header("5. Commissions")
    prop_comm_rate = st.number_input("Prop Commission (%)", 0.04, format="%.4f") / 100
    zero_cex_fees = st.checkbox("🔥 Use Zero-Fee CEX?", value=True)
    cex_comm_rate = 0.0 if zero_cex_fees else (st.number_input("CEX Commission (%)", 0.04, format="%.4f") / 100)

# --- ENGINE ---
def calculate_metrics(target_profit, ratio_val, risk_pct, leverage):
    risk_usd = acct_size * risk_pct
    prop_size = acct_size * leverage
    
    # NEW MULTIPLIER LOGIC
    cex_size = prop_size * ratio_val

    # Friction Pass
    prop_fric_pass = (prop_size * prop_comm_rate * 2)
    cex_fric_pass = (cex_size * cex_comm_rate * 2)
    
    # Friction Fail (Trade Only)
    prop_fric_trade = (prop_size * prop_comm_rate * 2)
    cex_fric_trade = (cex_size * cex_comm_rate * 2)
    
    # Friction Fail (Full Drain)
    total_drain = acct_size * max_dd_pct
    vol_mult = max_dd_pct / risk_pct
    prop_fric_drain = prop_fric_trade * vol_mult
    cex_fric_drain = cex_fric_trade * vol_mult
    
    # Fail Trade Net
    cex_win_gross_trade = risk_usd * ratio_val
    cex_win_net_trade = cex_win_gross_trade - cex_fric_trade
    
    # Fail Drain Net
    cex_win_gross_drain = total_drain * ratio_val
    cex_win_net_drain = cex_win_gross_drain - cex_fric_drain

    # Pass Cost
    prop_gross = target_profit + prop_fric_pass
    cex_loss_pass = (prop_gross * ratio_val) + cex_fric_pass

    return {
        "pass_cost": cex_loss_pass, 
        "fail_refund_trade": cex_win_net_trade,
        "fail_refund_full": cex_win_net_drain,
        "prop_size": prop_size, 
        "cex_size": cex_size
    }

# --- CALCULATIONS ---
p1 = calculate_metrics(acct_size * target_p1_pct, ratio_p1, risk_p1_in, lev_p1_in)

if chal_type != "1-Step Pro":
    p2 = calculate_metrics(acct_size * target_p2_pct, ratio_p2, risk_p2_in, lev_p2_in)
    total_sunk = fee + p1['pass_cost'] + p2['pass_cost']
else:
    total_sunk = fee + p1['pass_cost']

# --- TABS ---
if chal_type == "1-Step Pro":
    tabs = st.tabs(["Phase 1 (Eval)", "Funded Phase"])
    t1 = tabs[0]
    t3 = tabs[1]
else:
    tabs = st.tabs(["Phase 1", "Phase 2", "Funded Phase"])
    t1 = tabs[0]
    t2 = tabs[1]
    t3 = tabs[2]

# === PHASE 1 ===
with t1:
    target_str = f"Target: {target_p1_pct*100:.0f}% (${acct_size*target_p1_pct:,.0f})"
    st.markdown(f"<div class='big-header'>Phase 1 Execution ({target_str})</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='info-box'>Risking <b>{risk_p1_in*100:.1f}%</b> (${acct_size*risk_p1_in:,.0f}) per trade. Max DD: {max_dd_pct*100:.0f}%</div>", unsafe_allow_html=True)
    
    if st.session_state.phase1_status == "Pending":
        c1, c2, c3 = st.columns(3)
        c1.metric("Prop Size", f"${p1['prop_size']:,.0f}")
        c2.metric("CEX Size", f"${p1['cex_size']:,.0f}")
        c3.metric("Trade Refund", f"${p1['fail_refund_trade']:,.2f}")
        
        pass_cost_disp = p1['pass_cost'] * num_accounts
        daily_refund_disp = p1['fail_refund_trade'] * num_accounts
        full_refund_disp = p1['fail_refund_full'] * num_accounts
        
        # Split Drain
        remaining_refund_disp = full_refund_disp - daily_refund_disp
        if remaining_refund_disp < 0: remaining_refund_disp = 0
        
        col_pass, col_fail = st.columns(2)
        with col_pass:
            st.info(f"Hedge Loss if Pass: -${pass_cost_disp:,.2f}")
            if st.button("Phase 1 PASSED", key="p1_pass"): st.session_state.phase1_status="Passed"; st.rerun()
        
        with col_fail:
            fees_paid = fee * num_accounts
            net_today = daily_refund_disp - fees_paid
            net_full_drain = full_refund_disp - fees_paid
            
            card_html = f"""
            <div class="result-card" style="border-left: 5px solid #FF4B4B;">
                <div class="fail-header">SCENARIO B: STRATEGIC FAIL</div>
                <div class="money-row"><span><b>Trade Refund ({risk_p1_in*100:.1f}%):</b></span><span class="money-pos">+${daily_refund_disp:,.2f}</span></div>
                <div class="money-row"><span>Fees Paid (Upfront):</span><span class="money-neg">-${fees_paid:,.2f}</span></div>
                <div class="money-row" style="border-top:1px solid #333; padding-top:5px;"><span><b>Net Cash Today:</b></span><span class="{'money-pos' if net_today>0 else 'money-neg'}">${net_today:,.2f}</span></div>
                <br>
                <div class="money-row" style="font-size:1.1em; color:#FFD700;"><span><b>Total Net (Full Drain):</b></span><span><b>${net_full_drain:,.2f}</b></span></div>
            </div>"""
            st.markdown(card_html, unsafe_allow_html=True)
            
            if st.button("Phase 1 FAILED (Log)", key="p1_fail"): st.session_state.phase1_status="Failed"; st.rerun()

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
if chal_type != "1-Step Pro":
    with t2:
        if st.session_state.phase1_status != "Passed":
            st.warning("🔒 Complete Phase 1 first.")
        else:
            st.markdown("<div class='big-header'>Phase 2: Execution</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='info-box'>Risking <b>{risk_p2_in*100:.1f}%</b>.</div>", unsafe_allow_html=True)
            
            pass_cost_disp = p2['pass_cost'] * num_accounts
            fail_refund_disp = p2['fail_refund_full'] * num_accounts
            
            if st.session_state.phase2_status == "Pending":
                col_pass, col_fail = st.columns(2)
                with col_pass:
                    st.info(f"Hedge Loss if Pass ({num_accounts}x): -${pass_cost_disp:,.2f}")
                    if st.button("Phase 2 PASSED", key="p2_pass"): st.session_state.phase2_status="Passed"; st.rerun()
                with col_fail:
                    st.error(f"Refund if Fail (Full DD): +${fail_refund_disp:,.2f}")
                    if st.button("Phase 2 FAILED", key="p2_fail"): st.session_state.phase2_status="Failed"; st.rerun()

            elif st.session_state.phase2_status == "Passed":
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
                    <div class="money-row"><span>Total Refund:</span><span class="money-pos">+${fail_refund_disp:,.2f}</span></div>
                    <div class="money-row"><span>Fees Paid:</span><span class="money-neg">-${fee_total:,.2f}</span></div>
                    <div class="money-row"><span>Phase 1 Hedge:</span><span class="money-neg">-${p1_cost_total:,.2f}</span></div>
                    <div class="total-row"><span>NET RESULT:</span><span class="{'money-pos' if net_res_disp>0 else 'money-neg'}">${net_res_disp:,.2f}</span></div>
                </div>"""
                st.markdown(html_f2, unsafe_allow_html=True)
                if st.button("Restart Phase 2"): st.session_state.phase2_status="Pending"; st.rerun()

# === FUNDED ===
with t3:
    st.markdown("<div class='big-header'>Funded Phase</div>", unsafe_allow_html=True)
    
    if chal_type == "1-Step Pro":
        st.markdown(f"""
        <div class='danger-box'>
        <b>⚠️ 1-STEP MATH WARNING ⚠️</b><br>
        Because you paid heavily to pass the 12% target, your Sunk Cost (${total_sunk:,.0f}) is higher than your Max Drawdown (${acct_size * max_dd_pct:,.0f}).<br>
        <b>It is mathematically impossible to profit from a funded win if you hedge it.</b><br>
        Use the Auto-Breakeven tool to see why.
        </div>
        """, unsafe_allow_html=True)

    target_profit_amt = st.number_input("Target Withdrawal Amount (Per Account):", value=4000.0, step=100.0)
    
    col_tools, col_ratio = st.columns([1, 2])
    with col_tools:
        st.markdown("**Tools:**")
        if st.button("🧪 Auto-Breakeven Ratio"):
            full_drain = acct_size * max_dd_pct
            safe_ratio = total_sunk / full_drain
            if safe_ratio > 3.0: safe_ratio = 3.0 # Cap it visually
            st.session_state.funded_ratio = safe_ratio
            st.rerun()
            
    with col_ratio:
        if 'funded_ratio' not in st.session_state: st.session_state.funded_ratio = 0.75
        f_ratio = st.slider("Hedge Ratio (Multiplier)", 0.1, 3.0, st.session_state.funded_ratio, 0.01)
        st.session_state.funded_ratio = f_ratio

    # CALC PER ACCOUNT
    # For funded risk, we borrow the P1/P2 risk just to calculate sizing
    f_risk = st.session_state.risk_p1 / 100 if chal_type == "1-Step Pro" else risk_p2_in
    f_lev = st.session_state.lev_p1 if chal_type == "1-Step Pro" else lev_p2_in
    
    f_metrics = calculate_metrics(target_profit_amt, f_ratio, f_risk, f_lev)
    
    payout_one = target_profit_amt * profit_split_pct
    net_win_one = payout_one - f_metrics['pass_cost']
    
    # Fail calc (Funded)
    total_drain = acct_size * max_dd_pct
    vol_mult = max_dd_pct / f_risk
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
            <div class="pass-header">SCENARIO A: WIN & WITHDRAW</div>
            <div class="money-row"><span>Goal ({num_accounts}x):</span><span style="color:white;">${goal_total_disp:,.2f}</span></div>
            <div class="money-row"><span>Payout:</span><span class="money-pos">+${payout_total_disp:,.2f}</span></div>
            <div class="money-row"><span>Hedge Cost:</span><span class="money-neg">-${hedge_cost_total_disp:,.2f}</span></div>
            <div class="total-row"><span>NET TRADE PROFIT:</span><span class="{'money-pos' if net_win_total_disp>0 else 'money-neg'}">${net_win_total_disp:,.2f}</span></div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="result-card" style="border: 1px solid #FF4B4B;">
            <div class="fail-header">SCENARIO B: FAIL & DRAIN</div>
            <div class="money-row"><span>Refund ({max_dd_pct*100:.0f}% Drain):</span><span class="money-pos">+${refund_total_disp:,.2f}</span></div>
            <div class="money-row"><span>Sunk Costs:</span><span class="money-neg">-${sunk_total_disp:,.2f}</span></div>
            <div class="total-row"><span>LIFETIME EXIT NET:</span><span class="{'money-pos' if net_fail_total_disp>0 else 'money-neg'}">${net_fail_total_disp:,.2f}</span></div>
        </div>
        """, unsafe_allow_html=True)
