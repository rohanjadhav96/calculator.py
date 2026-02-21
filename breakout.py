import streamlit as st
import pandas as pd

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Breakout Hedge Commander v41", layout="wide", page_icon="🛡️")

# --- SESSION STATE INITIALIZATION ---
if 'phase1_status' not in st.session_state: st.session_state.phase1_status = "Pending"

# Default to Standard Multipliers
if 'risk_p1' not in st.session_state: st.session_state.risk_p1 = 2.5
if 'lev_p1' not in st.session_state: st.session_state.lev_p1 = 2.5
if 'risk_p2' not in st.session_state: st.session_state.risk_p2 = 2.5
if 'lev_p2' not in st.session_state: st.session_state.lev_p2 = 2.5
if 'ratio_p1_set' not in st.session_state: st.session_state.ratio_p1_set = 0.25
if 'ratio_p2_set' not in st.session_state: st.session_state.ratio_p2_set = 0.35
if 'chal_type' not in st.session_state: st.session_state.chal_type = "1-Step Pro"

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

st.title("🛡️ Breakout Hedge Commander v41")
st.caption("Update: The 0.25 Ratio Fix for 1-Step 50k")

# --- SIDEBAR ---
with st.sidebar:
    st.header("1. Choose Your Mode")
    
    # PRESET BUTTONS
    c_farm, c_1step = st.columns(2)
    
    if c_farm.button("💸 2-STEP"):
        st.session_state.chal_type = "Standard 2-Step"
        st.session_state.risk_p1 = 4.5
        st.session_state.lev_p1 = 5.0
        st.session_state.ratio_p1_set = 0.24
        st.rerun()

    if c_1step.button("🎯 1-STEP (0.25)"):
        st.session_state.chal_type = "1-Step Pro"
        st.session_state.risk_p1 = 2.5
        st.session_state.lev_p1 = 2.5
        st.session_state.ratio_p1_set = 0.25
        st.rerun()

    chal_type = st.radio("Challenge Type", ["Standard 2-Step", "1-Step Pro"], index=["Standard 2-Step", "1-Step Pro"].index(st.session_state.chal_type))
    st.session_state.chal_type = chal_type

    if chal_type == "1-Step Pro":
        st.markdown("""<div class='farm-box'><b>Mode: 1-Step Pro (50k)</b><br>Target: 12% | Max DD: 5%<br><i>Ratio set to 0.25 ($125 loss per 1%)</i></div>""", unsafe_allow_html=True)
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
        elif acct_choice == 100000: final_fee = 760.0
        else: final_fee = 220.0
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
    
    st.header("3. Risk Settings")
    if chal_type == "1-Step Pro":
        max_dd_pct = 0.05
        target_p1_pct = 0.12
    else:
        max_dd_pct = st.number_input("Max Drawdown Limit (%)", 8.0) / 100
        target_p1_pct = 0.05
        target_p2_pct = 0.10
    
    c1, c2 = st.columns(2)
    risk_p1_in = c1.number_input("Daily Risk (%)", 0.1, 10.0, st.session_state.risk_p1, 0.1) / 100
    lev_p1_in = c2.number_input("Leverage (x)", 1.0, 20.0, st.session_state.lev_p1, 0.1)
    
    st.header("4. Hedge Ratio (Multiplier)")
    ratio_p1 = st.number_input("P1 Ratio (e.g., 0.25)", min_value=0.01, max_value=5.0, value=st.session_state.ratio_p1_set, step=0.01, format="%.2f")
    
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

    # Friction
    prop_fric_trade = (prop_size * prop_comm_rate * 2)
    cex_fric_trade = (cex_size * cex_comm_rate * 2)
    
    # Drain Logic
    total_drain = acct_size * max_dd_pct
    vol_mult = max_dd_pct / risk_pct
    prop_fric_drain = prop_fric_trade * vol_mult
    cex_fric_drain = cex_fric_trade * vol_mult
    
    cex_win_net_trade = (risk_usd * ratio_val) - cex_fric_trade
    cex_win_net_drain = (total_drain * ratio_val) - cex_fric_drain

    # Pass Cost
    prop_gross = target_profit + (prop_size * prop_comm_rate * 2)
    cex_loss_pass = (prop_gross * ratio_val) + (cex_size * cex_comm_rate * 2)

    return {
        "pass_cost": cex_loss_pass, 
        "fail_refund_trade": cex_win_net_trade,
        "fail_refund_full": cex_win_net_drain,
        "prop_size": prop_size, 
        "cex_size": cex_size
    }

# --- CALCULATIONS ---
p1 = calculate_metrics(acct_size * target_p1_pct, ratio_p1, risk_p1_in, lev_p1_in)
total_sunk = fee + p1['pass_cost']

# --- TABS ---
if chal_type == "1-Step Pro":
    tabs = st.tabs(["Phase 1 (Eval)", "Funded Phase (The Drain)"])
    t1, t3 = tabs[0], tabs[1]
else:
    tabs = st.tabs(["Phase 1", "Phase 2", "Funded"])
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
            if st.button("Phase 1 PASSED", key="p1_pass"): st.session_state.phase1_status="Passed"; st.rerun()
        
        with col_fail:
            card_html = f"""
            <div class="result-card" style="border-left: 5px solid #FF4B4B;">
                <div class="fail-header">SCENARIO B: STRATEGIC FAIL</div>
                <div class="money-row"><span><b>CEX Win ({max_dd_pct*100:.0f}% Drain):</b></span><span class="money-pos">+${full_refund_disp:,.2f}</span></div>
                <div class="money-row"><span>Fees Paid:</span><span class="money-neg">-${fees_paid:,.2f}</span></div>
                <div class="money-row" style="border-top:1px solid #333; padding-top:5px;"><span><b>Net Farm Cash:</b></span><span class="{'money-pos' if net_full_drain>0 else 'money-neg'}">${net_full_drain:,.2f}</span></div>
            </div>"""
            st.markdown(card_html, unsafe_allow_html=True)
            if st.button("Phase 1 FAILED (Reset)", key="p1_fail"): st.session_state.phase1_status="Pending"; st.rerun()

    elif st.session_state.phase1_status == "Passed":
        html_p1 = f"""
        <div class="result-card" style="border-left: 5px solid #00FF7F;">
            <div class="pass-header">✅ Phase 1 Passed</div>
            <div class="money-row"><span>Fees Paid:</span><span class="money-neg">-${fee * num_accounts:,.2f}</span></div>
            <div class="money-row"><span>Hedge Cost:</span><span class="money-neg">-${p1['pass_cost'] * num_accounts:,.2f}</span></div>
            <div class="total-row"><span>Total Sunk (Debt):</span><span class="money-neg">-${total_sunk * num_accounts:,.2f}</span></div>
        </div>"""
        st.markdown(html_p1, unsafe_allow_html=True)
        if st.button("Undo Phase 1"): st.session_state.phase1_status="Pending"; st.rerun()

# === FUNDED ===
with t3:
    st.markdown("<div class='big-header'>Funded Phase: Debt Recovery</div>", unsafe_allow_html=True)
    
    if chal_type == "1-Step Pro":
        st.markdown(f"""
        <div class='info-box'>
        <b>The Math:</b> You are in a -${total_sunk:,.0f} hole. You have ${acct_size * max_dd_pct:,.0f} of drawdown to burn.<br>
        To get your money back, crank the Hedge Ratio up (e.g., 0.85) and drain the account.
        </div>
        """, unsafe_allow_html=True)

    target_profit_amt = st.number_input("Target Withdrawal Amount (If you try to win):", value=4000.0, step=100.0)
    
    if 'funded_ratio' not in st.session_state: st.session_state.funded_ratio = 0.85
    f_ratio = st.slider("Funded Hedge Ratio (Multiplier)", 0.1, 1.5, st.session_state.funded_ratio, 0.01)
    st.session_state.funded_ratio = f_ratio

    f_metrics = calculate_metrics(target_profit_amt, f_ratio, risk_p1_in, lev_p1_in)
    payout_one = target_profit_amt * profit_split_pct
    
    # Drain logic
    total_drain = acct_size * max_dd_pct
    cex_fric_fail = (f_metrics['cex_size'] * (max_dd_pct / risk_p1_in) * cex_comm_rate * 2)
    cex_win_net_drain = (total_drain * f_ratio) - cex_fric_fail
    
    net_fail_one = cex_win_net_drain - total_sunk
    net_win_one = payout_one - f_metrics['pass_cost'] - total_sunk

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""
        <div class="result-card" style="border: 1px solid #FFD700;">
            <div class="pass-header" style="color:#FFD700;">SCENARIO A: ACCIDENTAL WIN</div>
            <div class="money-row"><span>Payout ({profit_split_pct*100:.0f}%):</span><span class="money-pos">+${payout_one:,.2f}</span></div>
            <div class="money-row"><span>Trade Hedge Loss:</span><span class="money-neg">-${f_metrics['pass_cost']:,.2f}</span></div>
            <div class="money-row"><span>Eval Sunk Cost:</span><span class="money-neg">-${total_sunk:,.2f}</span></div>
            <div class="total-row"><span>LIFETIME NET:</span><span class="{'money-pos' if net_win_one>0 else 'money-neg'}">${net_win_one:,.2f}</span></div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="result-card" style="border: 1px solid #FF4B4B;">
            <div class="fail-header">SCENARIO B: INTENTIONAL DRAIN</div>
            <div class="money-row"><span>CEX Win ({max_dd_pct*100:.0f}% DD):</span><span class="money-pos">+${cex_win_net_drain:,.2f}</span></div>
            <div class="money-row"><span>Eval Sunk Cost:</span><span class="money-neg">-${total_sunk:,.2f}</span></div>
            <div class="total-row"><span>LIFETIME NET:</span><span class="{'money-pos' if net_fail_one>0 else 'money-neg'}">${net_fail_one:,.2f}</span></div>
        </div>
        """, unsafe_allow_html=True)
