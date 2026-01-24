import streamlit as st
import pandas as pd

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Breakout Hedge Commander v7.0 (Doctor Mode)", layout="wide", page_icon="🩺")

# --- SESSION STATE ---
if 'phase1_status' not in st.session_state: st.session_state.phase1_status = "Pending"
if 'phase2_status' not in st.session_state: st.session_state.phase2_status = "Pending"

# --- STYLING ---
st.markdown("""
<style>
    .doctor-box { background-color: #0e1117; border: 1px solid #FFD700; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
    .doctor-title { color: #FFD700; font-weight: bold; font-size: 1.1em; display: flex; align-items: center; }
    .fix-btn { background-color: #FFD700; color: black; font-weight: bold; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; }
    .big-header { font-size: 22px; font-weight: bold; color: #4CAF50; margin-bottom: 10px; }
    .pass-box { background-color: #0d3316; border: 1px solid #1f7a37; padding: 20px; border-radius: 10px; text-align: center; }
    .fail-box { background-color: #330d0d; border: 1px solid #7a1f1f; padding: 20px; border-radius: 10px; text-align: center; }
    .metric-container { background-color: #262730; padding: 10px; border-radius: 5px; text-align: center; }
</style>
""", unsafe_allow_html=True)

st.title("🩺 Breakout Hedge Commander v7.0")
st.markdown("**Includes 'Strategy Doctor' to auto-correct your math.**")

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
    ratio_p1 = st.number_input("Phase 1 Ratio", 5.8, step=0.1)
    ratio_p2 = st.number_input("Phase 2 Ratio", 3.2, step=0.1)
    ratio_funded = st.number_input("Funded Ratio", 0.75, step=0.05)
    
    st.header("4. Market Friction")
    comm_rate = st.number_input("Commission (%)", 0.04, format="%.4f") / 100
    
    st.markdown("---")
    include_swap = st.checkbox("Include Swap Fees?", value=True)
    if include_swap:
        swap_rate = st.number_input("Swap Rate (%)", 0.03, format="%.4f") / 100
        days_held = st.number_input("Avg Days Held", 2)
    else:
        swap_rate = 0.0
        days_held = 0.0
    
    st.markdown("---")
    if st.button("🔄 FULL RESET"):
        st.session_state.phase1_status = "Pending"
        st.session_state.phase2_status = "Pending"
        st.rerun()

# --- ENGINE ---
def calculate_scenario(target_profit, ratio):
    risk_amount_usd = acct_size * risk_per_trade_pct
    sl_distance = 0.01 
    prop_size_notional = risk_amount_usd / sl_distance
    cex_size_notional = prop_size_notional / ratio
    
    prop_swap_cost = (prop_size_notional * swap_rate * days_held) if include_swap else 0
    cex_swap_cost = (cex_size_notional * swap_rate * days_held) if include_swap else 0
    
    prop_friction = (prop_size_notional * comm_rate * 2) + prop_swap_cost
    cex_friction = (cex_size_notional * comm_rate * 2) + cex_swap_cost
    
    prop_gross_needed = target_profit + prop_friction
    cex_loss_if_pass = (prop_gross_needed / ratio) + cex_friction
    
    # Fail Logic: Max Drain
    total_prop_loss = acct_size * max_dd_pct
    total_cex_win = (total_prop_loss / ratio) - (cex_friction * (max_dd_pct/risk_per_trade_pct)) 
    
    return {
        "cex_loss_pass": cex_loss_if_pass,
        "cex_win_fail": total_cex_win,
        "risk_usd": risk_amount_usd,
        "prop_size": prop_size_notional,
        "cex_size": cex_size_notional
    }

p1 = calculate_scenario(acct_size * 0.05, ratio_p1)
p2 = calculate_scenario(acct_size * 0.10, ratio_p2)
funded = calculate_scenario(acct_size * 0.05, ratio_funded)

# --- 🩺 STRATEGY DOCTOR (DIAGNOSTICS) ---
st.markdown("### 🔍 Diagnostics")

issues_found = []

# Check 1: Phase 1 Break Even
net_fail_p1 = p1['cex_win_fail'] - fee
if net_fail_p1 < 0:
    # Calculate required ratio to break even
    # Win = Fee -> (MaxLoss / Ratio) = Fee (ignoring friction for rough est)
    rec_ratio = (acct_size * max_dd_pct) / fee
    issues_found.append({
        "severity": "High",
        "title": "Phase 1: Guaranteed Loss on Failure",
        "msg": f"Your Phase 1 Ratio ({ratio_p1}) is too high. If you fail, you only recover ${p1['cex_win_fail']:,.0f}, but you paid ${fee}.",
        "fix": f"Lower Phase 1 Ratio to **{rec_ratio:.1f}** or less."
    })

# Check 2: Phase 2 Break Even (Fail P2 covers P1 Cost + Fee)
cost_p1 = p1['cex_loss_pass']
net_fail_p2 = p2['cex_win_fail'] - (fee + cost_p1)
if net_fail_p2 < 0:
    # Rough estimate fix
    target_recovery = fee + cost_p1
    rec_ratio_p2 = (acct_size * max_dd_pct) / target_recovery
    issues_found.append({
        "severity": "Medium",
        "title": "Phase 2: Loss on Failure",
        "msg": f"If you fail Phase 2, your refund ($ {p2['cex_win_fail']:,.0f}) won't cover your Fee + Phase 1 costs.",
        "fix": f"Lower Phase 2 Ratio to **{rec_ratio_p2:.1f}**."
    })

# Check 3: Risk Per Trade vs Daily Limit
if risk_per_trade_pct >= daily_dd_pct:
    issues_found.append({
        "severity": "Critical",
        "title": "Risk Too High (Instant Fail Warning)",
        "msg": f"Your Risk Per Trade ({risk_per_trade_pct*100}%) is equal to or higher than the Daily Limit ({daily_dd_pct*100}%). A single bad tick will blow the account.",
        "fix": f"Lower Risk Per Trade to **{(daily_dd_pct*100)-1}%**."
    })

# RENDER DOCTOR
if not issues_found:
    st.success("✅ **Strategy Healthy:** All ratios allow for profitable refunds or safe execution.")
else:
    for issue in issues_found:
        icon = "🚨" if issue['severity'] == "Critical" else "⚠️"
        st.markdown(f"""
        <div class="doctor-box">
            <div class="doctor-title">{icon} {issue['title']}</div>
            <p>{issue['msg']}</p>
            <p style="color: #00FF7F;"><strong>💡 FIX: {issue['fix']}</strong></p>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["PHASE 1 (Eval)", "PHASE 2 (Verify)", "PHASE 3 (Funded)"])

# === PHASE 1 ===
with tab1:
    st.markdown("<div class='big-header'>Phase 1: The Setup</div>", unsafe_allow_html=True)
    if st.session_state.phase1_status == "Pending":
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Risk", f"${p1['risk_usd']:,.0f}")
        c2.metric("Daily Limit", f"${acct_size*daily_dd_pct:,.0f}")
        c3.metric("Prop Size", f"${p1['prop_size']:,.0f}")
        c4.metric("CEX Size", f"${p1['cex_size']:,.0f}")
        
        st.markdown("---")
        cp, cf = st.columns(2)
        with cp:
            st.info(f"**Cost to Pass:** -${p1['cex_loss_pass']:,.2f}")
            if st.button("Phase 1 PASSED", key="p1_pass"): st.session_state.phase1_status = "Passed"; st.rerun()
        with cf:
            st.error(f"**Refund if Fail:** +${p1['cex_win_fail']:,.2f}")
            if st.button("Phase 1 FAILED", key="p1_fail"): st.session_state.phase1_status = "Failed"; st.rerun()

    elif st.session_state.phase1_status == "Passed":
        st.markdown(f"<div class='pass-box'><h3>✅ Phase 1 Passed</h3><p>Proceed to Phase 2</p></div>", unsafe_allow_html=True)
        if st.button("Undo"): st.session_state.phase1_status = "Pending"; st.rerun()
    elif st.session_state.phase1_status == "Failed":
        st.markdown(f"<div class='fail-box'><h3>❌ Phase 1 Failed</h3><p>Net Result: ${p1['cex_win_fail'] - fee:,.2f}</p></div>", unsafe_allow_html=True)
        if st.button("Restart"): st.session_state.phase1_status = "Pending"; st.rerun()

# === PHASE 2 ===
with tab2:
    if st.session_state.phase1_status != "Passed":
        st.warning("Locked: Complete Phase 1 first.")
    elif st.session_state.phase2_status == "Pending":
        st.markdown("<div class='big-header'>Phase 2: Verification</div>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Risk", f"${p2['risk_usd']:,.0f}")
        c2.metric("Prop Size", f"${p2['prop_size']:,.0f}")
        c3.metric("CEX Size", f"${p2['cex_size']:,.0f}")
        
        st.markdown("---")
        cp, cf = st.columns(2)
        with cp:
            st.info(f"**Cost to Pass:** -${p2['cex_loss_pass']:,.2f}")
            if st.button("Phase 2 PASSED", key="p2_pass"): st.session_state.phase2_status = "Passed"; st.rerun()
        with cf:
            st.error(f"**Refund if Fail:** +${p2['cex_win_fail']:,.2f}")
            if st.button("Phase 2 FAILED", key="p2_fail"): st.session_state.phase2_status = "Failed"; st.rerun()

    elif st.session_state.phase2_status == "Passed":
        total_sunk = fee + p1['cex_loss_pass'] + p2['cex_loss_pass']
        st.markdown(f"<div class='pass-box'><h3>🏆 FUNDED!</h3><p>Total Investment: ${total_sunk:,.2f}</p></div>", unsafe_allow_html=True)
        if st.button("Undo"): st.session_state.phase2_status = "Pending"; st.rerun()
    elif st.session_state.phase2_status == "Failed":
        st.markdown(f"<div class='fail-box'><h3>❌ Phase 2 Failed</h3><p>Recovered: ${p2['cex_win_fail']:,.2f}</p></div>", unsafe_allow_html=True)
        if st.button("Restart"): st.session_state.phase2_status = "Pending"; st.rerun()

# === PHASE 3 ===
with tab3:
    if st.session_state.phase2_status != "Passed":
        st.warning("Locked: Complete Phase 2 first.")
    else:
        st.markdown("<div class='big-header'>Phase 3: Harvest</div>", unsafe_allow_html=True)
        total_sunk = fee + p1['cex_loss_pass'] + p2['cex_loss_pass']
        payout = (acct_size*0.05)*0.90
        hedge_loss = funded['cex_loss_pass']
        net = payout - hedge_loss - total_sunk
        
        st.markdown(f"""
        <div class="highlight-box">
            <h3>💰 Final Profit Calculation</h3>
            <p>Target Profit: ${acct_size*0.05:,.0f}</p>
            <p>Net Payout (90%): <span style='color:#00FF7F'>+${payout:,.2f}</span></p>
            <p>CEX Burn: <span style='color:#FF4B4B'>-${hedge_loss:,.2f}</span></p>
            <p>Total Sunk Costs: <span style='color:#FF4B4B'>-${total_sunk:,.2f}</span></p>
            <hr>
            <h2>Final Net Profit: ${net:,.2f}</h2>
        </div>
        """, unsafe_allow_html=True)
