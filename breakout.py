import streamlit as st
import pandas as pd
import math


# --- APP CONFIGURATION ---
st.set_page_config(page_title="Breakout Hedge Commander v53", layout="wide", page_icon="🛡️")

# --- SESSION STATE INITIALIZATION ---
if 'phase1_status' not in st.session_state: st.session_state.phase1_status = "Pending"
if 'phase2_status' not in st.session_state: st.session_state.phase2_status = "Pending"

# Default to Classic 0.41 Strategy
if 'risk_p1' not in st.session_state: st.session_state.risk_p1 = 2.5
if 'lev_p1' not in st.session_state: st.session_state.lev_p1 = 2.5
if 'risk_p2' not in st.session_state: st.session_state.risk_p2 = 2.5
if 'lev_p2' not in st.session_state: st.session_state.lev_p2 = 2.5
if 'ratio_p1_set' not in st.session_state: st.session_state.ratio_p1_set = 0.41
if 'ratio_p2_set' not in st.session_state: st.session_state.ratio_p2_set = 0.35
if 'chal_type' not in st.session_state: st.session_state.chal_type = "1-Step Classic"

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
    .info-box { background-color: #1c1c1c; padding: 15px; border-left: 4px solid #4169e1; font-size: 0.95em; color: #ccc; margin-bottom: 20px; border-radius: 4px; }
    .success-box { background-color: #0a1f0a; padding: 10px; border-left: 3px solid #00FF7F; font-size: 0.9em; color: #ccffcc; margin-bottom: 10px; }
    .farm-box { background-color: #1a1a0a; padding: 10px; border-left: 3px solid #FFD700; font-size: 0.9em; color: #fffacd; margin-bottom: 10px; }
    .safety-box { background-color: #0d1b2a; border: 1px solid #4169e1; padding: 15px; border-radius: 8px; margin-top: 10px; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Breakout Hedge Commander v53")
st.caption("Update: Live Target Allocation Matrix Added")

# --- SIDEBAR ---
with st.sidebar:
    st.header("1. Choose Master Strategy")
    
    # QUICK LAUNCH BUTTONS
    c_pro, c_clas = st.columns(2)
    if c_pro.button("🎯 PRO (0.294)"):
        st.session_state.chal_type = "1-Step Pro"
        st.session_state.risk_p1 = 2.5
        st.session_state.ratio_p1_set = 0.294
        st.rerun()
    if c_clas.button("🏆 CLASSIC (0.41)"):
        st.session_state.chal_type = "1-Step Classic"
        st.session_state.risk_p1 = 2.5
        st.session_state.ratio_p1_set = 0.41
        st.rerun()

    chal_type = st.selectbox("Challenge Type", ["1-Step Turbo", "1-Step Pro", "1-Step Classic", "2-Step Classic"], index=["1-Step Turbo", "1-Step Pro", "1-Step Classic", "2-Step Classic"].index(st.session_state.chal_type))
    st.session_state.chal_type = chal_type

    st.markdown("---")
    st.header("2. Account Configuration")
    
    num_accounts = st.number_input("Active Accounts (Multiplier)", min_value=1, max_value=50, value=1)
    acct_choice = st.selectbox("Select Account Size", [10000, 25000, 50000, 100000, 200000], index=0)
    
    # EXACT BREAKOUT BASE PRICING MATRIX
    pricing_matrix = {
        "1-Step Turbo": {10000: 40.0, 25000: 95.0, 50000: 180.0, 100000: 330.0, 200000: 660.0},
        "1-Step Pro": {10000: 60.0, 25000: 150.0, 50000: 280.0, 100000: 545.0, 200000: 1090.0},
        "1-Step Classic": {10000: 85.0, 25000: 215.0, 50000: 400.0, 100000: 750.0, 200000: 1500.0},
        "2-Step Classic": {10000: 85.0, 25000: 215.0, 50000: 400.0, 100000: 750.0, 200000: 1500.0}
    }
    
    est_base = pricing_matrix[chal_type].get(acct_choice, 100.0)
    base_fee = st.number_input("Base Eval Fee ($)", value=est_base)
    
    split_choice = st.radio("Profit Split", ["90% Split (+20% Fee)", "80% Split (Standard)"], horizontal=True)
    
    add_on = base_fee * 0.20 if "90%" in split_choice else 0.0
    raw_fee = base_fee + add_on
    final_fee = raw_fee * 0.98  # Fixed MATCH 2% Code
    
    st.metric(f"Final Cost (with 'MATCH')", f"${final_fee:.2f}", f"+${add_on:.2f} for 90%" if add_on > 0 else None, delta_color="off")
    
    acct_size = acct_choice
    fee = final_fee
    profit_split_pct = 0.90 if "90%" in split_choice else 0.80

    st.header("3. Prop Firm Settings")
    
    if chal_type == "1-Step Turbo":
        max_dd_pct = 0.03
        target_p1_pct = 0.09
        daily_limit = 0.03
    elif chal_type == "1-Step Pro":
        max_dd_pct = 0.05
        target_p1_pct = 0.12
        daily_limit = 0.03
    elif chal_type == "1-Step Classic":
        max_dd_pct = 0.06
        target_p1_pct = 0.10
        daily_limit = 0.03
    else:
        max_dd_pct = 0.06
        target_p1_pct = 0.10
        target_p2_pct = 0.05
        daily_limit = 0.04
    
    st.markdown(f"**Phase 1 Settings (Max Daily: {daily_limit*100:.0f}%)**")
    c1, c2 = st.columns(2)
    risk_p1_in = c1.number_input("P1 Risk (%)", 0.1, 10.0, st.session_state.risk_p1, 0.1) / 100
    lev_p1_in = c2.number_input("P1 Leverage (x)", 1.0, 100.0, st.session_state.lev_p1, 0.1)

    if chal_type == "2-Step Classic":
        st.markdown("**Phase 2 Settings**")
        c3, c4 = st.columns(2)
        risk_p2_in = c3.number_input("P2 Risk (%)", 0.1, 10.0, st.session_state.risk_p2, 0.1) / 100
        lev_p2_in = c4.number_input("P2 Leverage (x)", 1.0, 100.0, st.session_state.lev_p2, 0.1)
    else:
        risk_p2_in = risk_p1_in
        lev_p2_in = lev_p1_in
    
    st.header("4. CEX & Hedge Settings")
    cex_lev_in = st.number_input("CEX Futures Leverage (x)", min_value=1.0, max_value=200.0, value=20.0, step=1.0)
    
    ratio_p1 = st.number_input("P1 Ratio (Multiplier)", min_value=0.01, max_value=5.0, value=st.session_state.ratio_p1_set, step=0.001, format="%.3f")
    if chal_type == "2-Step Classic":
        ratio_p2 = st.number_input("P2 Ratio", min_value=0.01, max_value=5.0, value=st.session_state.ratio_p2_set, step=0.01, format="%.2f")
    else:
        ratio_p2 = 0.0

    st.sidebar.markdown(f"""<div class='farm-box'><b>Mode: {chal_type} ({acct_size//1000}k)</b><br>Target: {target_p1_pct*100:.0f}% | Max DD: {max_dd_pct*100:.0f}%</div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.header("5. Commissions")
    prop_comm_rate = st.number_input("Prop Commission (%)", 0.04, format="%.4f") / 100
    zero_cex_fees = st.checkbox("🔥 Use Zero-Fee CEX?", value=True)
    cex_comm_rate = 0.0 if zero_cex_fees else (st.number_input("CEX Commission (%)", 0.04, format="%.4f") / 100)

# --- ENGINE ---
def calculate_metrics(target_profit, ratio_val, risk_pct, leverage):
    risk_usd = acct_size * risk_pct
    prop_size = acct_size * leverage
    cex_size = prop_size * ratio_val

    prop_fric_trade = (prop_size * prop_comm_rate * 2)
    cex_fric_trade = (cex_size * cex_comm_rate * 2)
    
    total_drain = acct_size * max_dd_pct
    vol_mult = max_dd_pct / risk_pct
    prop_fric_drain = prop_fric_trade * vol_mult
    cex_fric_drain = cex_fric_trade * vol_mult
    
    cex_win_net_trade = (risk_usd * ratio_val) - cex_fric_trade
    cex_win_net_drain = (total_drain * ratio_val) - cex_fric_drain

    prop_gross = target_profit + (prop_size * prop_comm_rate * 2)
    cex_loss_pass = (prop_gross * ratio_val) + (cex_size * cex_comm_rate * 2)

    return {
        "pass_cost": cex_loss_pass, 
        "fail_refund_trade": cex_win_net_trade,
        "fail_refund_full": cex_win_net_drain,
        "prop_size": prop_size, 
        "cex_size": cex_size,
        "risk_usd": risk_usd,
        "total_drain": total_drain
    }

# --- CALCULATIONS ---
p1 = calculate_metrics(acct_size * target_p1_pct, ratio_p1, risk_p1_in, lev_p1_in)

total_sunk_per_acct = fee + p1['pass_cost']
if chal_type == "2-Step Classic":
    p2 = calculate_metrics(acct_size * target_p2_pct, ratio_p2, risk_p2_in, lev_p2_in)
    total_sunk_per_acct += p2['pass_cost']

# --- DYNAMIC RISK MATRIX VISUALIZATION (MAIN SCREEN TOP) ---
st.markdown("### 📊 Live Risk Allocation Matrix")
calc_prop_risk_trade = p1['risk_usd'] * num_accounts
calc_cex_risk_trade = calc_prop_risk_trade * ratio_p1
calc_prop_drain = p1['total_drain'] * num_accounts
calc_cex_drain_win = calc_prop_drain * ratio_p1

risk_matrix_data = {
    "Execution Metric": ["Per-Trade Risk", "Full-Account Risk (Max Drawdown)"],
    "Prop Account Exposure": [f"${calc_prop_risk_trade:,.2f} ({risk_p1_in*100:.1f}%)", f"${calc_prop_drain:,.2f} ({max_dd_pct*100:.1f}%)"],
    "CEX Hedge Target Outcome": [f"+${calc_cex_risk_trade:,.2f} (Gross Win)", f"+${calc_cex_drain_win:,.2f} (Gross Win)"]
}
st.table(pd.DataFrame(risk_matrix_data))

st.markdown(f"""
<div class="info-box">
    <b>💡 Execution Rule:</b> When executing trades, if you risk exactly <b>${calc_prop_risk_trade:,.2f}</b> on your Breakout account, your corresponding position size on your CEX futures exchange must target a gross profit of <b>${calc_cex_risk_trade:,.2f}</b> if the trade fails on the prop side.
</div>
""", unsafe_allow_html=True)

# --- WALLET LEDGER LOGIC ---
st.sidebar.markdown("---")
st.sidebar.header("💳 Live CEX Wallet Ledger")
if 'starting_capital' not in st.session_state: st.session_state.starting_capital = 5000.0
start_cap = st.sidebar.number_input("Starting CEX Balance ($)", min_value=100.0, value=st.session_state.starting_capital, step=500.0)
st.session_state.starting_capital = start_cap

realized_debt = 0.0
if st.session_state.phase1_status == "Passed":
    realized_debt += (fee + p1['pass_cost']) * num_accounts
if chal_type == "2-Step Classic" and st.session_state.phase2_status == "Passed":
    realized_debt += p2['pass_cost'] * num_accounts

current_wallet = start_cap - realized_debt
st.sidebar.metric("Live CEX Wallet Available", f"${current_wallet:,.2f}", f"-${realized_debt:,.2f} Sunk" if realized_debt > 0 else None, delta_color="normal")

# --- TABS ---
if chal_type != "2-Step Classic":
    tabs = st.tabs(["Phase 1 (Eval)", "Funded Phase (Sniper)"])
    t1, t3 = tabs[0], tabs[1]
else:
    tabs = st.tabs(["Phase 1", "Phase 2", "Funded Phase"])
    t1, t2, t3 = tabs[0], tabs[1], tabs[2]

# === PHASE 1 ===
with t1:
    target_str = f"Target: {target_p1_pct*100:.0f}% (${acct_size*target_p1_pct:,.0f})"
    st.markdown(f"<div class='big-header'>Phase 1 Execution ({target_str})</div>", unsafe_allow_html=True)
    
    if st.session_state.phase1_status == "Pending":
        pass_cost_disp = p1['pass_cost'] * num_accounts
        full_refund_disp = p1['fail_refund_full'] * num_accounts
        fees_paid = fee * num_accounts
        net_full_drain = full_refund_disp - fees_paid
        
        col_pass, col_fail = st.columns(2)
        with col_pass:
            st.info(f"Hedge Loss if Pass: -${pass_cost_disp:,.2f}")
            st.markdown(f"**Wallet After Pass:** <span style='color:#ccc;'>${start_cap - fees_paid - pass_cost_disp:,.2f}</span>", unsafe_allow_html=True)
            if st.button("Phase 1 PASSED", key="p1_pass"): st.session_state.phase1_status="Passed"; st.rerun()
        
        with col_fail:
            card_html = f"""
            <div class="result-card" style="border-left: 5px solid #FF4B4B;">
                <div class="fail-header">SCENARIO B: STRATEGIC FAIL</div>
                <div class="money-row"><span><b>CEX Win ({max_dd_pct*100:.0f}% Drain):</b></span><span class="money-pos">+${full_refund_disp:,.2f}</span></div>
                <div class="money-row"><span>Fees Paid:</span><span class="money-neg">-${fees_paid:,.2f}</span></div>
                <div class="money-row" style="border-top:1px solid #333; padding-top:5px;"><span><b>Net Farm Cash:</b></span><span class="{'money-pos' if net_full_drain>0 else 'money-neg'}">${net_full_drain:,.2f}</span></div>
                <br>
                <div class="money-row" style="font-size:1.1em;"><span><b>💳 Wallet After Drain:</b></span><span style="color:#FFF;"><b>${start_cap + net_full_drain:,.2f}</b></span></div>
            </div>"""
            st.markdown(card_html, unsafe_allow_html=True)
            if st.button("Phase 1 FAILED (Reset)", key="p1_fail"): st.session_state.phase1_status="Pending"; st.rerun()

    elif st.session_state.phase1_status == "Passed":
        html_p1 = f"""
        <div class="result-card" style="border-left: 5px solid #00FF7F;">
            <div class="pass-header">✅ Phase 1 Passed</div>
            <div class="money-row"><span>Fees Paid:</span><span class="money-neg">-${fee * num_accounts:,.2f}</span></div>
            <div class="money-row"><span>Hedge Cost:</span><span class="money-neg">-${p1['pass_cost'] * num_accounts:,.2f}</span></div>
            <div class="total-row"><span>Sunk Debt (So Far):</span><span class="money-neg">-${(fee + p1['pass_cost']) * num_accounts:,.2f}</span></div>
        </div>"""
        st.markdown(html_p1, unsafe_allow_html=True)
        if st.button("Undo Phase 1"): st.session_state.phase1_status="Pending"; st.rerun()

# === PHASE 2 ===
if chal_type == "2-Step Classic":
    with t2:
        if st.session_state.phase1_status != "Passed":
            st.warning("🔒 Complete Phase 1 first.")
        else:
            target_str_p2 = f"Target: {target_p2_pct*100:.0f}% (${acct_size*target_p2_pct:,.0f})"
            st.markdown(f"<div class='big-header'>Phase 2 Execution ({target_str_p2})</div>", unsafe_allow_html=True)
            
            pass_cost_disp = p2['pass_cost'] * num_accounts
            fail_refund_disp = p2['fail_refund_full'] * num_accounts
            
            if st.session_state.phase2_status == "Pending":
                col_pass, col_fail = st.columns(2)
                with col_pass:
                    st.info(f"Hedge Loss if Pass: -${pass_cost_disp:,.2f}")
                    st.markdown(f"**Wallet After Pass:** <span style='color:#ccc;'>${current_wallet - pass_cost_disp:,.2f}</span>", unsafe_allow_html=True)
                    if st.button("Phase 2 PASSED", key="p2_pass"): st.session_state.phase2_status="Passed"; st.rerun()
                with col_fail:
                    st.error(f"Refund if Fail (Full DD): +${fail_refund_disp:,.2f}")
                    st.markdown(f"**Wallet After Fail:** <span style='color:#ccc;'>${current_wallet + fail_refund_disp:,.2f}</span>", unsafe_allow_html=True)
                    if st.button("Phase 2 FAILED", key="p2_fail"): st.session_state.phase2_status="Failed"; st.rerun()

            elif st.session_state.phase2_status == "Passed":
                html_p2 = f"""
                <div class="result-card" style="border-left: 5px solid #00FF7F;">
                    <div class="pass-header">🏆 YOU ARE FUNDED</div>
                    <div class="total-row"><span>TOTAL INVESTMENT (DEBT):</span><span class="money-neg">-${realized_debt:,.2f}</span></div>
                </div>"""
                st.markdown(html_p2, unsafe_allow_html=True)
                if st.button("Undo Phase 2"): st.session_state.phase2_status="Pending"; st.rerun()

# === FUNDED PHASE ===
with t3:
    st.markdown("<div class='big-header'>Funded Phase Execution</div>", unsafe_allow_html=True)
    
    if chal_type == "2-Step Classic" and st.session_state.phase2_status != "Passed":
        st.warning("🔒 Complete Phase 2 first to unlock Funded Math.")
        st.stop()
    elif chal_type != "2-Step Classic" and st.session_state.phase1_status != "Passed":
        st.warning("🔒 Complete Phase 1 first to unlock Funded Math.")
        st.stop()

    target_profit_amt = st.number_input("Target Withdrawal Amount (Per Account):", value=4000.0, step=100.0)
    
    if st.button("🧪 Calculate Auto-Breakeven Ratio"):
        full_drain = acct_size * max_dd_pct
        safe_ratio = realized_debt / full_drain
        st.session_state.funded_ratio = safe_ratio
        st.success(f"Ratio updated to {safe_ratio:.2f}")

    if 'funded_ratio' not in st.session_state: st.session_state.funded_ratio = 0.85
    f_ratio = st.slider("Funded Hedge Ratio (Multiplier)", 0.1, 1.5, st.session_state.funded_ratio, 0.01)
    st.session_state.funded_ratio = f_ratio

    active_risk = risk_p1_in if chal_type != "2-Step Classic" else risk_p2_in
    active_lev = lev_p1_in if chal_type != "2-Step Classic" else lev_p2_in
    
    f_metrics = calculate_metrics(target_profit_amt, f_ratio, active_risk, active_lev)
    payout_one = target_profit_amt * profit_split_pct
    
    cex_margin_req = (f_metrics['cex_size'] / cex_lev_in) * num_accounts
    max_cex_loss = f_metrics['pass_cost'] * num_accounts
    safe_balance_needed = cex_margin_req + max_cex_loss
    
    shortfall = safe_balance_needed - current_wallet

    if shortfall <= 0:
        safety_html = f"""
        <div class="safety-box" style="border-color: #00FF7F;">
            <h4 style="color:#00FF7F; margin-top:0;">✅ Liquidation Safety Check Passed</h4>
            <span>To hold this trade safely, you need <b>${cex_margin_req:,.2f}</b> for Initial Margin ({cex_lev_in}x Lev) + <b>${max_cex_loss:,.2f}</b> to absorb the floating loss before Prop hits TP. <br>Total Required: <b>${safe_balance_needed:,.2f}</b>. Your Wallet: <b>${current_wallet:,.2f}</b>.</span>
        </div>
        """
    else:
        safety_html = f"""
        <div class="safety-box" style="border-color: #FF4B4B;">
            <h4 style="color:#FF4B4B; margin-top:0;">⚠️ DANGER: Liquidation Risk</h4>
            <span>You need <b>${safe_balance_needed:,.2f}</b> (Margin @ {cex_lev_in}x: ${cex_margin_req:,.0f} + Loss Buffer: ${max_cex_loss:,.0f}) to hold this trade. Your wallet only has <b>${current_wallet:,.2f}</b>. <br><br><b>❌ You are short by <span style="color:#FFD700;">${shortfall:,.2f}</span>.</b><br>Add this exact amount to your CEX or increase your leverage to avoid early liquidation.</span>
        </div>
        """
    st.markdown(safety_html, unsafe_allow_html=True)

    total_drain = acct_size * max_dd_pct
    days_to_drain = math.ceil(max_dd_pct / active_risk)
    
    cex_fric_fail = (f_metrics['cex_size'] * (max_dd_pct / active_risk) * cex_comm_rate * 2)
    cex_win_net_drain = (total_drain * f_ratio) - cex_fric_fail
    
    net_trade_cash_win_total = (payout_one - f_metrics['pass_cost']) * num_accounts
    net_trade_cash_fail_total = cex_win_net_drain * num_accounts
    
    net_fail_total = net_trade_cash_fail_total - realized_debt
    net_win_total = net_trade_cash_win_total - realized_debt
    
    wallet_after_win = current_wallet + net_trade_cash_win_total
    wallet_after_fail = current_wallet + net_trade_cash_fail_total

    c1, c2 = st.columns(2)
    win_title = "SCENARIO A: ACCIDENTAL WIN (RELOAD)" if chal_type != "2-Step Classic" else "SCENARIO A: WIN & WITHDRAW"
    fail_title = "SCENARIO B: FINAL EXIT DRAIN" if chal_type != "2-Step Classic" else "SCENARIO B: FAIL & DRAIN"

    with c1:
        st.markdown(f"""
        <div class="result-card" style="border: 1px solid #FFD700;">
            <div class="pass-header" style="color:#FFD700;">{win_title}</div>
            <div class="money-row"><span>Payout ({profit_split_pct*100:.0f}%):</span><span class="money-pos">+${payout_one * num_accounts:,.2f}</span></div>
            <div class="money-row"><span>Trade Hedge Loss:</span><span class="money-neg">-${f_metrics['pass_cost'] * num_accounts:,.2f}</span></div>
            <div class="money-row" style="border-top:1px solid #333; padding-top:5px;"><span><b>Net Trade Cash Flow:</b></span><span class="{'money-pos' if net_trade_cash_win_total>0 else 'money-neg'}">+${net_trade_cash_win_total:,.2f}</span></div>
            <br>
            <div class="money-row" style="font-size:1.1em;"><span><b>💳 Wallet After Win:</b></span><span style="color:#FFF;"><b>${wallet_after_win:,.2f}</b></span></div>
            <div class="total-row"><span>LIFETIME NET (Vs Debt):</span><span class="{'money-pos' if net_win_total>0 else 'money-neg'}">${net_win_total:,.2f}</span></div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="result-card" style="border: 1px solid #FF4B4B;">
            <div class="fail-header">{fail_title}</div>
            <span style="color:#888; font-size: 0.9em;"><i>*Draining {max_dd_pct*100}% takes <b>{days_to_drain} days</b> (risking {active_risk*100}%/day) to avoid the {daily_limit*100:.0f}% daily limit.</i></span><br><br>
            <div class="money-row"><span>CEX Win ({max_dd_pct*100:.0f}% DD Total):</span><span class="money-pos">+${net_trade_cash_fail_total:,.2f}</span></div>
            <div class="money-row" style="border-top:1px solid #333; padding-top:5px;"><span><b>Net Trade Cash Flow:</b></span><span class="{'money-pos' if net_trade_cash_fail_total>0 else 'money-neg'}">+${net_trade_cash_fail_total:,.2f}</span></div>
            <br>
            <div class="money-row" style="font-size:1.1em;"><span><b>💳 Wallet After Drain:</b></span><span style="color:#FFF;"><b>${wallet_after_fail:,.2f}</b></span></div>
            <div class="total-row"><span>LIFETIME NET (Vs Debt):</span><span class="{'money-pos' if net_fail_total>0 else 'money-neg'}">${net_fail_total:,.2f}</span></div>
        </div>
        """, unsafe_allow_html=True)
