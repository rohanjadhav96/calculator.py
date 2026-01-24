import streamlit as st
import pandas as pd
import math

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Breakout Hedge Commander", layout="wide", page_icon="🛡️")

# --- SESSION STATE INITIALIZATION ---
if 'phase1_status' not in st.session_state: st.session_state.phase1_status = "Pending"
if 'phase2_status' not in st.session_state: st.session_state.phase2_status = "Pending"
if 'risk_preset' not in st.session_state: st.session_state.risk_preset = 4.8
if 'days_preset' not in st.session_state: st.session_state.days_preset = 0
if 'funded_ratio' not in st.session_state: st.session_state.funded_ratio = 0.75

# --- STYLING ---
st.markdown("""
<style>
    /* Main Layout */
    .big-header { font-size: 24px; font-weight: bold; color: #FFD700; margin-bottom: 15px; }
    .sub-header { font-size: 18px; font-weight: bold; color: #00BFFF; margin-top: 20px; margin-bottom: 10px; }
    
    /* Result Cards */
    .result-card { background-color: #0e1117; border: 1px solid #333; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
    
    /* Money Colors */
    .money-pos { color: #00FF7F; font-weight: bold; }
    .money-neg { color: #FF4B4B; font-weight: bold; }
    .money-neu { color: #aaa; font-weight: bold; }
    
    /* Headers inside cards */
    .pass-header { color: #00FF7F; font-size: 1.4em; font-weight: bold; margin-bottom: 10px; border-bottom: 1px solid #333; padding-bottom: 5px; }
    .fail-header { color: #FF4B4B; font-size: 1.4em; font-weight: bold; margin-bottom: 10px; border-bottom: 1px solid #333; padding-bottom: 5px; }
    
    /* Rows */
    .money-row { display: flex; justify-content: space-between; margin-bottom: 6px; }
    .total-row { display: flex; justify-content: space-between; margin-top: 15px; padding-top: 10px; border-top: 1px solid #444; font-size: 1.2em; font-weight: bold; }
    
    /* Tools */
    .solver-box { border: 1px solid #00BFFF; background-color: #0a1320; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
    .cycle-box { border: 1px solid #FFD700; background-color: #1a1a0a; padding: 15px; border-radius: 8px; margin-top: 20px; }
    
    /* Info/Warning Boxes */
    .info-box { background-color: #1c1c1c; padding: 10px; border-left: 3px solid #888; font-size: 0.9em; color: #ccc; margin-bottom: 10px; }
    .warning-box { background-color: #2e0b0b; padding: 10px; border-left: 3px solid #FF4B4B; font-size: 0.9em; color: #ffcccc; margin-bottom: 15px; }
    .success-box { background-color: #0a1f0a; padding: 10px; border-left: 3px solid #00FF7F; font-size: 0.9em; color: #ccffcc; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Breakout Hedge Commander v27")
st.caption("The Ultra Suite: Multi-Account Scaling & Cycle Projection")

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
    
    # MULTI-ACCOUNT SCALER
    num_accounts = st.number_input("Number of Accounts to Trade", min_value=1, max_value=20, value=1)
    
    # ACCOUNT SELECTION
    acct_choice = st.selectbox("Select Account Size", [25000, 50000, 100000], index=1)
    split_choice = st.radio("Profit Split", ["90% (Pro)", "80% (Standard)"], horizontal=True)
    apply_discount = st.checkbox("Apply 2% Discount Code?", value=False)
    
    # FEE LOGIC
    # 25k: Base 250 | +25 for 90%
    # 50k: Base 450 | +45 for 90%
    # 100k: Base 750 | +75 for 90%
    if acct_choice == 25000:
        base_fee = 250; add_on = 25
    elif acct_choice == 50000:
        base_fee = 450; add_on = 45
    elif acct_choice == 100000:
        base_fee = 750; add_on = 75
        
    raw_fee = base_fee + add_on if "90%" in split_choice else base_fee
    final_fee = raw_fee * 0.98 if apply_discount else raw_fee
    
    st.metric(f"Fee (Per Account)", f"${final_fee:.2f}")
    if num_accounts > 1:
        st.metric(f"Total Investment ({num_accounts}x)", f"${final_fee * num_accounts:.2f}")
    
    acct_size = acct_choice
    fee = final_fee
    profit_split_pct = 0.90 if "90%" in split_choice else 0.80
    
    st.header("3. Risk Management")
    max_dd_pct = st.number_input("Max Drawdown Limit (%)", 8.0) / 100
    daily_dd_pct = st.number_input("Daily Drawdown Limit (%)", 5.0) / 100
    risk_per_trade_pct = st.number_input("RISK PER TRADE (%)", value=st.session_state.risk_preset, step=0.1, format="%.1f") / 100
    
    st.header("4. Hedge Ratios")
    ratio_p1 = st.number_input("Phase 1 Ratio", 5.8, step=0.1)
    ratio_p2 = st.number_input("Phase 2 Ratio", 3.2, step=0.1)
    
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
        
    st.markdown("---")
    # DRAWDOWN BUFFER TOOL
    with st.expander("📉 Drawdown Safety Check"):
        curr_bal = st.number_input("Current Balance", value=float(acct_size))
        hwm = st.number_input("High Water Mark", value=float(acct_size))
        
        # Drawdown is 8% of Initial Balance, Trailing from HWM? 
        # Wait, the rule is usually "Max Trailing Drawdown is 8% from HWM" OR "Fixed 8% trailing".
        # Based on standard 2-step trailing: It trails HWM until it locks at Initial Balance.
        # Let's assume standard trailing logic for the buffer check.
        
        max_loss_allowed = hwm * (1 - max_dd_pct) # Simple proxy for visual
        # Or usually it's static relative to HWM. 
        # Let's stick to the prompt: "Trailing Drawdown stays static while trade is open".
        
        buffer = curr_bal - (hwm - (acct_size * max_dd_pct)) # Approx logic for trailing from HWM
        # Actually simplest Breakout logic:
        # Breach Level = High Water Mark - (Initial Balance * 0.08)
        breach_level = hwm - (acct_size * max_dd_pct)
        # But it usually doesn't trail past initial balance?
        # Let's just calculate distance to 8% from HWM.
        
        dist_dollars = curr_bal - breach_level
        st.write(f"Breach Level: **${breach_level:,.2f}**")
        st.write(f"Safety Buffer: **${dist_dollars:,.2f}**")
        if dist_dollars < 0:
            st.error("BREACHED!")
        elif dist_dollars < (acct_size * 0.02):
            st.warning("⚠️ Danger Zone")
        else:
            st.success("✅ Safe")

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
    if num_accounts > 1: st.info(f"📊 Displaying totals for {num_accounts} accounts.")

    # Apply Multiplier
    fee_disp = fee * num_accounts
    pass_cost_disp = p1['pass_cost'] * num_accounts
    fail_refund_disp = p1['fail_refund'] * num_accounts
    sunk_disp = (fee + p1['pass_cost']) * num_accounts
    
    if st.session_state.phase1_status == "Pending":
        c1, c2, c3 = st.columns(3)
        c1.metric("Prop Size", f"${p1['prop_size']:,.0f}")
        c2.metric("CEX Size", f"${p1['cex_size']:,.0f}")
        c3.metric("One-Shot Risk", f"${acct_size*risk_per_trade_pct:,.0f}")
        
        col_pass, col_fail = st.columns(2)
        with col_pass:
            st.info(f"Total Cost to Pass: -${pass_cost_disp:,.2f}")
            if st.button("Phase 1 PASSED", key="p1_pass"): st.session_state.phase1_status="Passed"; st.rerun()
        with col_fail:
            st.error(f"Total Refund if Fail: +${fail_refund_disp:,.2f}")
            if st.button("Phase 1 FAILED", key="p1_fail"): st.session_state.phase1_status="Failed"; st.rerun()

    elif st.session_state.phase1_status == "Passed":
        html_p1 = f"""
        <div class="result-card" style="border-left: 5px solid #00FF7F;">
            <div class="pass-header">✅ Phase 1 Passed ({num_accounts} Accts)</div>
            <div class="money-row"><span>Total Fees:</span><span class="money-neg">-${fee_disp:,.2f}</span></div>
            <div class="money-row"><span>Total Hedge Cost:</span><span class="money-neg">-${pass_cost_disp:,.2f}</span></div>
            <div class="total-row"><span>Total Sunk Cost:</span><span class="money-neg">-${sunk_disp:,.2f}</span></div>
        </div>"""
        st.markdown(html_p1, unsafe_allow_html=True)
        if st.button("Undo Phase 1"): st.session_state.phase1_status="Pending"; st.rerun()

    elif st.session_state.phase1_status == "Failed":
        net = fail_refund_disp - fee_disp
        html_fail = f"""
        <div class="result-card" style="border-left: 5px solid #FF4B4B;">
            <div class="fail-header">❌ Phase 1 Failed ({num_accounts} Accts)</div>
            <div class="money-row"><span>Total Refund:</span><span class="money-pos">+${fail_refund_disp:,.2f}</span></div>
            <div class="money-row"><span>Total Fees:</span><span class="money-neg">-${fee_disp:,.2f}</span></div>
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
        
        # Apply Multiplier
        pass_cost_disp = p2['pass_cost'] * num_accounts
        fail_refund_disp = p2['fail_refund'] * num_accounts
        prev_sunk_disp = (fee + p1['pass_cost']) * num_accounts
        
        if st.session_state.phase2_status == "Pending":
            col_pass, col_fail = st.columns(2)
            with col_pass:
                st.info(f"Total Cost to Pass: -${pass_cost_disp:,.2f}")
                if st.button("Phase 2 PASSED", key="p2_pass"): st.session_state.phase2_status="Passed"; st.rerun()
            with col_fail:
                st.error(f"Total Refund if Fail: +${fail_refund_disp:,.2f}")
                if st.button("Phase 2 FAILED", key="p2_fail"): st.session_state.phase2_status="Failed"; st.rerun()

        elif st.session_state.phase2_status == "Passed":
            total_inv_disp = total_sunk * num_accounts
            html_p2 = f"""
            <div class="result-card" style="border-left: 5px solid #00FF7F;">
                <div class="pass-header">🏆 YOU ARE FUNDED ({num_accounts} Accts)</div>
                <div class="money-row"><span>Total Phase 1 Cost:</span><span class="money-neg">-${p1['pass_cost']*num_accounts:,.2f}</span></div>
                <div class="money-row"><span>Total Phase 2 Cost:</span><span class="money-neg">-${pass_cost_disp:,.2f}</span></div>
                <div class="total-row"><span>TOTAL INVESTMENT:</span><span class="money-neg">-${total_inv_disp:,.2f}</span></div>
            </div>"""
            st.markdown(html_p2, unsafe_allow_html=True)
            if st.button("Undo Phase 2"): st.session_state.phase2_status="Pending"; st.rerun()

        elif st.session_state.phase2_status == "Failed":
            net = fail_refund_disp - prev_sunk_disp
            html_f2 = f"""
            <div class="result-card" style="border-left: 5px solid #FF4B4B;">
                <div class="fail-header">❌ Phase 2 Failed</div>
                <div class="money-row"><span>Total Refund:</span><span class="money-pos">+${fail_refund_disp:,.2f}</span></div>
                <div class="money-row"><span>Total Sunk:</span><span class="money-neg">-${prev_sunk_disp:,.2f}</span></div>
                <div class="total-row"><span>NET RESULT:</span><span class="{'money-pos' if net>0 else 'money-neg'}">${net:,.2f}</span></div>
            </div>"""
            st.markdown(html_f2, unsafe_allow_html=True)
            if st.button("Restart Phase 2"): st.session_state.phase2_status="Pending"; st.rerun()

# === FUNDED ===
with t3:
    st.markdown("<div class='big-header'>Funded Phase: Sniper Mode</div>", unsafe_allow_html=True)
    st.markdown(f"**Accounts Active:** {num_accounts} | **Profit Split:** {split_choice}")

    target_profit_amt = st.number_input("I want to withdraw this amount (Per Account) ($):", value=4000.0, step=100.0)
    
    # 1. RATIO SELECTOR
    col_tools, col_ratio = st.columns([1, 2])
    with col_tools:
        st.markdown("**Tools:**")
        if st.button("🧪 Auto-Breakeven Ratio"):
            # Breakeven = Total_Sunk / (8% Drain)
            full_drain = acct_size * max_dd_pct
            safe_ratio = total_sunk / full_drain
            if safe_ratio > 2.0: safe_ratio = 2.0
            st.session_state.funded_ratio = safe_ratio
            st.success(f"Set to {safe_ratio:.2f}")
            st.rerun()
            
    with col_ratio:
        f_ratio = st.slider("Hedge Ratio (CEX Risk per $1 Prop)", 0.1, 2.0, st.session_state.funded_ratio, 0.01)
        st.session_state.funded_ratio = f_ratio

    # CALC PER ACCOUNT
    f_metrics = calculate_metrics(target_profit_amt, 0, is_funded=True, funded_ratio=f_ratio)
    
    # TOTALS
    payout_gross_total = (target_profit_amt * profit_split_pct) * num_accounts
    pass_cost_total = f_metrics['pass_cost'] * num_accounts
    monthly_net_total = payout_gross_total - pass_cost_total
    
    fail_refund_total = f_metrics['fail_refund'] * num_accounts
    sunk_total = total_sunk * num_accounts
    fail_net_total = fail_refund_total - sunk_total

    # DISPLAY CARDS
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""
        <div class="result-card" style="border: 1px solid #00FF7F;">
            <div class="pass-header">SCENARIO A: ALL PASS</div>
            <div class="money-row"><span>Goal ({num_accounts}x):</span><span style="color:white;">${target_profit_amt*num_accounts:,.2f}</span></div>
            <div class="money-row"><span>Total Payout:</span><span class="money-pos">+${payout_gross_total:,.2f}</span></div>
            <div class="money-row"><span>Total Hedge Cost:</span><span class="money-neg">-${pass_cost_total:,.2f}</span></div>
            <div class="total-row"><span>TOTAL NET PROFIT:</span><span class="{'money-pos' if monthly_net_total>0 else 'money-neg'}">${monthly_net_total:,.2f}</span></div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="result-card" style="border: 1px solid #FF4B4B;">
            <div class="fail-header">SCENARIO B: ALL FAIL</div>
            <div class="money-row"><span>Total Refund:</span><span class="money-pos">+${fail_refund_total:,.2f}</span></div>
            <div class="money-row"><span>Total Sunk:</span><span class="money-neg">-${sunk_total:,.2f}</span></div>
            <div class="total-row"><span>TOTAL EXIT PROFIT:</span><span class="{'money-pos' if fail_net_total>0 else 'money-neg'}">${fail_net_total:,.2f}</span></div>
        </div>
        """, unsafe_allow_html=True)
        
    # --- CYCLE PROJECTOR ---
    st.markdown("<div class='sub-header'>🔄 Cycle Projector</div>", unsafe_allow_html=True)
    
    with st.expander("Run Simulation (Mixed Results)", expanded=True):
        col_sim1, col_sim2 = st.columns(2)
        with col_sim1:
            wins = st.number_input("Accounts Passed (Payout)", min_value=0, max_value=num_accounts, value=int(num_accounts/2))
        with col_sim2:
            fails = st.number_input("Accounts Failed (Burn)", min_value=0, max_value=num_accounts, value=int(num_accounts - (num_accounts/2)))
            
        if wins + fails != num_accounts:
            st.warning(f"Note: {wins} + {fails} does not equal your total {num_accounts} accounts.")
            
        # Calc Mixed
        profit_from_wins = (target_profit_amt * profit_split_pct - f_metrics['pass_cost']) * wins
        profit_from_fails = (f_metrics['fail_refund'] - total_sunk) * fails
        
        # Sunk cost of winners is already factored into "Net Monthly" in previous logic? 
        # Wait, "Monthly Net" above = Payout - Hedge Cost. It does NOT subtract the original fee/eval cost.
        # To be accurate for "Cycle Profit", we must subtract Sunk Cost from winners too.
        
        # Correct Net Logic:
        # Winner = (Payout - HedgeCost) - SunkCost
        # Loser = (Refund) - SunkCost
        
        net_per_winner = (target_profit_amt * profit_split_pct) - f_metrics['pass_cost'] - total_sunk
        net_per_loser = f_metrics['fail_refund'] - total_sunk
        
        sim_total = (net_per_winner * wins) + (net_per_loser * fails)
        
        st.markdown(f"""
        <div class="cycle-box">
            <div class="money-row"><span>Profit from {wins} Winners:</span><span class="money-pos">${net_per_winner * wins:,.2f}</span></div>
            <div class="money-row"><span>Profit from {fails} Losers:</span><span class="{'money-pos' if net_per_loser>0 else 'money-neg'}">${net_per_loser * fails:,.2f}</span></div>
            <div style="border-top:1px solid #444; margin:10px 0;"></div>
            <h3 style="text-align:center; color:{'#00FF7F' if sim_total>0 else '#FF4B4B'};">PROJECTED TOTAL: ${sim_total:,.2f}</h3>
        </div>
        """, unsafe_allow_html=True)
