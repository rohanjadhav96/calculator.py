import streamlit as st
import pandas as pd

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Breakout Hedge Commander", layout="wide", page_icon="🛡️")

# --- SESSION STATE ---
if 'phase1_status' not in st.session_state: st.session_state.phase1_status = "Pending"
if 'phase2_status' not in st.session_state: st.session_state.phase2_status = "Pending"

# --- STYLING ---
st.markdown("""
<style>
    /* Main Layout */
    .big-header { font-size: 24px; font-weight: bold; color: #4CAF50; margin-bottom: 10px; }
    
    /* Diagnostic Box (The Doctor) */
    .doctor-box { background-color: #1a1a1a; border-left: 5px solid #FFD700; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
    .doctor-title { color: #FFD700; font-weight: bold; font-size: 1.1em; margin-bottom: 5px; }
    
    /* Result Boxes */
    .pass-box { background-color: #0d3316; border: 1px solid #1f7a37; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 15px; }
    .fail-box { background-color: #330d0d; border: 1px solid #7a1f1f; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 15px; }
    
    /* Text Colors */
    .money-pos { color: #00FF7F; font-weight: bold; }
    .money-neg { color: #FF4B4B; font-weight: bold; }
    .money-neutral { color: #aaa; }
    
    hr { border-color: #444; opacity: 0.5; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Breakout Hedge Commander")

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
    st.caption("Evaluation Phase (Prop > CEX)")
    ratio_p1 = st.number_input("Phase 1 Ratio", 5.8, step=0.1)
    ratio_p2 = st.number_input("Phase 2 Ratio", 3.2, step=0.1)
    
    st.markdown("---")
    st.caption("Funded Phase (Harvest)")
    funded_risk_per_dollar = st.number_input("CEX Risk per $1 Prop (e.g. 0.75)", 0.75, step=0.01)
    
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
    if st.button("🔄 FULL RESET", key="master_reset"):
        st.session_state.phase1_status = "Pending"
        st.session_state.phase2_status = "Pending"
        st.rerun()

# --- CALCULATION ENGINE ---
def calculate_metrics(target_profit, ratio_val, is_funded=False):
    risk_usd = acct_size * risk_per_trade_pct
    sl_dist = 0.01 # Assume 1% SL for sizing calculation
    
    # Position Sizes
    prop_size = risk_usd / sl_dist
    
    if is_funded:
        # Funded: CEX Size = Prop * 0.75
        cex_size = prop_size * funded_risk_per_dollar
        eff_ratio = 1 / funded_risk_per_dollar if funded_risk_per_dollar > 0 else 999
    else:
        # Eval: CEX Size = Prop / Ratio
        cex_size = prop_size / ratio_val
        eff_ratio = ratio_val

    # Friction (Comms + Swap)
    prop_swap = (prop_size * swap_rate * days_held) if include_swap else 0
    cex_swap = (cex_size * swap_rate * days_held) if include_swap else 0
    
    prop_friction = (prop_size * comm_rate * 2) + prop_swap
    cex_friction = (cex_size * comm_rate * 2) + cex_swap
    
    # PASS Logic
    # Prop needs to Gross: Target + Friction
    prop_gross_needed = target_profit + prop_friction
    
    if is_funded:
        cex_loss_pass = (prop_gross_needed * funded_risk_per_dollar) + cex_friction
    else:
        cex_loss_pass = (prop_gross_needed / eff_ratio) + cex_friction

    # FAIL Logic (Max Drain)
    total_prop_drain = acct_size * max_dd_pct
    drain_multiplier = max_dd_pct / risk_per_trade_pct # e.g. 8% / 4% = 2 trades to drain
    
    if is_funded:
        # If we blow funded, we win on CEX
        cex_win_fail = (total_prop_drain * funded_risk_per_dollar) - (cex_friction * drain_multiplier)
    else:
        cex_win_fail = (total_prop_drain / eff_ratio) - (cex_friction * drain_multiplier)

    return {
        "prop_size": prop_size,
        "cex_size": cex_size,
        "cex_loss_pass": cex_loss_pass,
        "cex_win_fail": cex_win_fail,
        "risk_usd": risk_usd,
        "prop_friction": prop_friction,
        "cex_friction": cex_friction
    }

# Execute Calculations
p1 = calculate_metrics(acct_size * 0.05, ratio_p1)
p2 = calculate_metrics(acct_size * 0.10, ratio_p2)
funded = calculate_metrics(acct_size * 0.05, 0, is_funded=True)

# --- DIAGNOSTIC DOCTOR (Auto-Check) ---
issues = []

# 1. Check Phase 1 Fail
net_p1_fail = p1['cex_win_fail'] - fee
if net_p1_fail < 0:
    issues.append(f"⚠️ **Phase 1 Ratio too high:** If you fail, you lose ${abs(net_p1_fail):.0f}. Lower Ratio 1 slightly.")

# 2. Check Funded Profitability (The Fix for your screenshot)
payout_gross = (acct_size * 0.05) * 0.90
monthly_net = payout_gross - funded['cex_loss_pass']
if monthly_net < 0:
    # Calculate Breakeven Ratio
    # Net = Payout - (Prop_Gross * Ratio + Friction)
    # We need to solve for Ratio where Net > 0
    # Approx logic for recommendation:
    prop_gross_approx = (acct_size * 0.05) + funded['prop_friction']
    rec_ratio = (payout_gross - funded['cex_friction']) / prop_gross_approx
    issues.append(f"🚨 **Funded Settings Unprofitable:** You are losing ${abs(monthly_net):.2f} per payout due to fees. **Lower your 'Funded Risk Ratio' to {rec_ratio:.2f} or less.**")

if issues:
    st.markdown('<div class="doctor-box"><div class="doctor-title">🩺 Strategy Doctor Alerts</div>', unsafe_allow_html=True)
    for issue in issues:
        st.markdown(issue)
    st.markdown('</div>', unsafe_allow_html=True)


# --- MAIN TABS ---
tab1, tab2, tab3 = st.tabs(["PHASE 1 (Eval)", "PHASE 2 (Verify)", "PHASE 3 (Funded)"])

# === PHASE 1 ===
with tab1:
    st.markdown("<div class='big-header'>Phase 1: The Setup</div>", unsafe_allow_html=True)
    
    if st.session_state.phase1_status == "Pending":
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Risk (4%)", f"${p1['risk_usd']:,.0f}")
        c2.metric("Prop Size", f"${p1['prop_size']:,.0f}")
        c3.metric("CEX Size", f"${p1['cex_size']:,.0f}")
        c4.metric("Daily Limit", f"${acct_size*daily_dd_pct:,.0f}")
        
        st.markdown("---")
        
        col_pass, col_fail = st.columns(2)
        with col_pass:
            st.info(f"**Cost to Pass:** -${p1['cex_loss_pass']:,.2f}")
            if st.button("Phase 1 PASSED", key="btn_p1_pass"): 
                st.session_state.phase1_status = "Passed"
                st.rerun()
                
        with col_fail:
            st.error(f"**Refund if Fail:** +${p1['cex_win_fail']:,.2f}")
            if st.button("Phase 1 FAILED", key="btn_p1_fail"): 
                st.session_state.phase1_status = "Failed"
                st.rerun()

    elif st.session_state.phase1_status == "Passed":
        st.markdown(f"""
        <div class='pass-box'>
            <h3>✅ Phase 1 Passed</h3>
            <p>You paid a hedge cost of <span class='money-neg'>-${p1['cex_loss_pass']:,.2f}</span></p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Undo Phase 1", key="undo_p1"): 
            st.session_state.phase1_status = "Pending"
            st.rerun()

    elif st.session_state.phase1_status == "Failed":
        net_res = p1['cex_win_fail'] - fee
        color_net = "money-pos" if net_res > 0 else "money-neg"
        st.markdown(f"""
        <div class='fail-box'>
            <h3>❌ Phase 1 Failed (Drained)</h3>
            <p>CEX Refund: <span class='money-pos'>+${p1['cex_win_fail']:,.2f}</span></p>
            <p>Fee Paid: <span class='money-neg'>-${fee:,.2f}</span></p>
            <hr>
            <h4>Net Result: <span class='{color_net}'>${net_res:,.2f}</span></h4>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Restart Phase 1", key="rest_p1"): 
            st.session_state.phase1_status = "Pending"
            st.rerun()

# === PHASE 2 ===
with tab2:
    if st.session_state.phase1_status != "Passed":
        st.warning("🔒 Locked: You must Pass Phase 1 first.")
    
    elif st.session_state.phase2_status == "Pending":
        st.markdown("<div class='big-header'>Phase 2: Verification</div>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Risk", f"${p2['risk_usd']:,.0f}")
        c2.metric("Prop Size", f"${p2['prop_size']:,.0f}")
        c3.metric("CEX Size", f"${p2['cex_size']:,.0f}")
        
        st.markdown("---")
        
        col_pass, col_fail = st.columns(2)
        with col_pass:
            st.info(f"**Cost to Pass:** -${p2['cex_loss_pass']:,.2f}")
            if st.button("Phase 2 PASSED", key="btn_p2_pass"): 
                st.session_state.phase2_status = "Passed"
                st.rerun()
                
        with col_fail:
            st.error(f"**Refund if Fail:** +${p2['cex_win_fail']:,.2f}")
            if st.button("Phase 2 FAILED", key="btn_p2_fail"): 
                st.session_state.phase2_status = "Failed"
                st.rerun()
    
    elif st.session_state.phase2_status == "Passed":
        total_sunk = fee + p1['cex_loss_pass'] + p2['cex_loss_pass']
        st.markdown(f"""
        <div class='pass-box'>
            <h3>🏆 FUNDED!</h3>
            <p>You have passed both evaluations.</p>
            <h4>Total Sunk Cost (Investment): <span class='money-neg'>-${total_sunk:,.2f}</span></h4>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Undo Phase 2", key="undo_p2"): 
            st.session_state.phase2_status = "Pending"
            st.rerun()
            
    elif st.session_state.phase2_status == "Failed":
        st.markdown(f"<div class='fail-box'><h3>❌ Phase 2 Failed</h3><p>Recovered: ${p2['cex_win_fail']:,.2f}</p></div>", unsafe_allow_html=True)
        if st.button("Restart Phase 2", key="rest_p2"): 
            st.session_state.phase2_status = "Pending"
            st.rerun()

# === PHASE 3 ===
with tab3:
    if st.session_state.phase2_status != "Passed":
        st.warning("🔒 Locked: You must Pass Phase 2 first.")
    else:
        st.markdown("<div class='big-header'>Phase 3: The Harvest</div>", unsafe_allow_html=True)
        
        total_sunk = fee + p1['cex_loss_pass'] + p2['cex_loss_pass']
        
        # Calculations
        prop_gross = (acct_size * 0.05)
        payout_net = prop_gross * 0.90
        hedge_cost = funded['cex_loss_pass']
        monthly_profit = payout_net - hedge_cost
        
        total_net = monthly_profit - total_sunk
        
        # Display
        st.markdown(f"""
        <div style="background-color:#1E1E1E; padding:20px; border-radius:10px; border:1px solid #444;">
            <h3 style="margin-top:0;">💰 Profit Calculator</h3>
            <table style="width:100%; color:#eee;">
                <tr>
                    <td>Prop Payout (90%):</td>
                    <td style="text-align:right;" class="money-pos">+${payout_net:,.2f}</td>
                </tr>
                <tr>
                    <td>CEX Hedge Cost:</td>
                    <td style="text-align:right;" class="money-neg">-${hedge_cost:,.2f}</td>
                </tr>
                <tr>
                    <td style="padding-top:10px;"><strong>MONTHLY NET PROFIT:</strong></td>
                    <td style="text-align:right; padding-top:10px;" class="{'money-pos' if monthly_profit > 0 else 'money-neg'}"><strong>${monthly_profit:,.2f}</strong></td>
                </tr>
            </table>
        </div>
        <br>
        """, unsafe_allow_html=True)
        
        # Optimization Tip
        if monthly_profit <= 0:
            st.warning("⚠️ **You are currently losing money.** Reduce the 'Funded Phase' Ratio in the sidebar until Monthly Net Profit turns GREEN.")
        
        st.markdown(f"""
        <div style="background-color:#000; padding:15px; border-radius:5px; margin-top:20px;">
            <p style="color:#888; font-size:0.9em;">Previous Sunk Costs: -${total_sunk:,.2f}</p>
            <h2 style="color:{'#00FF7F' if total_net > 0 else '#FF4B4B'}">TOTAL NET (Lifetime): ${total_net:,.2f}</h2>
        </div>
        """, unsafe_allow_html=True)
