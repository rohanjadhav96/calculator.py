import streamlit as st
import pandas as pd

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Breakout Hedge Commander v9.0 (Profit Fix)", layout="wide", page_icon="🛡️")

# --- SESSION STATE ---
if 'phase1_status' not in st.session_state: st.session_state.phase1_status = "Pending"
if 'phase2_status' not in st.session_state: st.session_state.phase2_status = "Pending"

# --- STYLING ---
st.markdown("""
<style>
    .doctor-box { background-color: #0e1117; border: 1px solid #FFD700; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
    .big-header { font-size: 22px; font-weight: bold; color: #4CAF50; margin-bottom: 10px; }
    .pass-box { background-color: #0d3316; border: 1px solid #1f7a37; padding: 20px; border-radius: 10px; text-align: center; }
    .fail-box { background-color: #330d0d; border: 1px solid #7a1f1f; padding: 20px; border-radius: 10px; text-align: center; }
    .money-pos { color: #00FF7F; font-weight: bold; font-size: 1.1em; }
    .money-neg { color: #FF4B4B; font-weight: bold; font-size: 1.1em; }
    .money-neutral { color: #aaa; font-weight: bold; }
    hr { margin: 10px 0; border-color: #444; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Breakout Hedge Commander v9.0")
st.markdown("**Fixed: Funded Phase Logic now matches '1:0.75' Profit Model**")

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
    ratio_p1 = st.number_input("Phase 1 Ratio (Prop/CEX)", 5.8, step=0.1)
    ratio_p2 = st.number_input("Phase 2 Ratio (Prop/CEX)", 3.2, step=0.1)
    
    st.markdown("---")
    st.caption("Funded Phase (Harvest)")
    # CHANGED: Explicit input to match friend's logic "1:0.75"
    funded_risk_per_dollar = st.number_input("CEX Risk per $1 Prop (e.g. 0.75)", 0.75, step=0.05)
    
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
    if st.button("🔄 FULL RESET", key="sidebar_reset"):
        st.session_state.phase1_status = "Pending"
        st.session_state.phase2_status = "Pending"
        st.rerun()

# --- ENGINE ---
def calculate_scenario(target_profit, ratio_val, is_funded=False):
    risk_amount_usd = acct_size * risk_per_trade_pct
    sl_distance = 0.01 
    prop_size_notional = risk_amount_usd / sl_distance
    
    # LOGIC SWITCH FOR FUNDED PHASE
    if is_funded:
        # If funded, User input 0.75 means: CEX = 0.75 * Prop
        cex_size_notional = prop_size_notional * funded_risk_per_dollar
        # For calculation consistency in the loop below, we determine an effective ratio
        effective_ratio = 1 / funded_risk_per_dollar
    else:
        # Standard Eval Phase: CEX = Prop / Ratio
        cex_size_notional = prop_size_notional / ratio_val
        effective_ratio = ratio_val
    
    # Costs
    prop_swap_cost = (prop_size_notional * swap_rate * days_held) if include_swap else 0
    cex_swap_cost = (cex_size_notional * swap_rate * days_held) if include_swap else 0
    
    prop_friction = (prop_size_notional * comm_rate * 2) + prop_swap_cost
    cex_friction = (cex_size_notional * comm_rate * 2) + cex_swap_cost
    
    # Pass/Win Logic
    prop_gross_needed = target_profit + prop_friction
    
    if is_funded:
        # Funded: CEX Loss = Prop_Gross * 0.75 (approx) + Friction
        cex_loss_if_pass = (prop_gross_needed * funded_risk_per_dollar) + cex_friction
    else:
        cex_loss_if_pass = (prop_gross_needed / effective_ratio) + cex_friction
    
    # Fail Logic
    total_prop_loss = acct_size * max_dd_pct
    
    if is_funded:
        # If we blow a funded account, we win on CEX
        # CEX Win = Total_Prop_Loss * 0.75 (approx) - Friction
        total_cex_win = (total_prop_loss * funded_risk_per_dollar) - (cex_friction * (max_dd_pct/risk_per_trade_pct))
    else:
        total_cex_win = (total_prop_loss / effective_ratio) - (cex_friction * (max_dd_pct/risk_per_trade_pct)) 
    
    return {
        "cex_loss_pass": cex_loss_if_pass,
        "cex_win_fail": total_cex_win,
        "risk_usd": risk_amount_usd,
        "prop_size": prop_size_notional,
        "cex_size": cex_size_notional
    }

# Run Calcs
p1 = calculate_scenario(acct_size * 0.05, ratio_p1)
p2 = calculate_scenario(acct_size * 0.10, ratio_p2)
funded = calculate_scenario(acct_size * 0.05, 0, is_funded=True)

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
        st.markdown(f"""
        <div class='pass-box'>
            <h3>✅ Phase 1 Passed</h3>
            <p>Cost Incurred: <span class='money-neg'>-${p1['cex_loss_pass']:,.2f}</span></p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Undo Phase 1", key="u1"): st.session_state.phase1_status = "Pending"; st.rerun()

    elif st.session_state.phase1_status == "Failed":
        net_result = p1['cex_win_fail'] - fee
        st.markdown(f"""
        <div class='fail-box'>
            <h3>❌ Phase 1 Failed</h3>
            <p>Net Profit (Refund - Fee): <span class='money-pos'>${net_result:,.2f}</span></p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Restart", key="r1"): st.session_state.phase1_status = "Pending"; st.rerun()

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
        st.markdown(f"""
        <div class='pass-box'>
            <h3>🏆 FUNDED!</h3>
            <p>Total Sunk Cost: <span class='money-neg'>-${total_sunk:,.2f}</span></p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Undo Phase 2", key="u2"): st.session_state.phase2_status = "Pending"; st.rerun()

    elif st.session_state.phase2_status == "Failed":
        st.markdown(f"<div class='fail-box'><h3>❌ Failed</h3></div>", unsafe_allow_html=True)
        if st.button("Restart", key="r2"): st.session_state.phase2_status = "Pending"; st.rerun()

# === PHASE 3 ===
with tab3:
    if st.session_state.phase2_status != "Passed":
        st.warning("Locked: Complete Phase 2 first.")
    else:
        st.markdown("<div class='big-header'>Phase 3: Harvest</div>", unsafe_allow_html=True)
        
        total_sunk = fee + p1['cex_loss_pass'] + p2['cex_loss_pass']
        payout_gross = (acct_size * 0.05) * 0.90
        hedge_burn = funded['cex_loss_pass']
        
        net_monthly = payout_gross - hedge_burn
        final_net = net_monthly - total_sunk
        
        st.markdown(f"""
        <div class="doctor-box">
            <h3 style="color: #FFD700">💰 Profit Model (1:{funded_risk_per_dollar})</h3>
            <table style="width:100%; color: white;">
                <tr>
                    <td>Prop Payout (90%):</td>
                    <td style="text-align:right;" class="money-pos">+${payout_gross:,.2f}</td>
                </tr>
                <tr>
                    <td>CEX Hedge Cost (Loss):</td>
                    <td style="text-align:right;" class="money-neg">-${hedge_burn:,.2f}</td>
                </tr>
                <tr>
                    <td><strong>Monthly Net Profit:</strong></td>
                    <td style="text-align:right;" class="money-pos"><strong>+${net_monthly:,.2f}</strong></td>
                </tr>
                 <tr><td colspan="2"><hr></td></tr>
                 <tr>
                    <td>Sunk Costs (Fee + Eval):</td>
                    <td style="text-align:right;" class="money-neg">-${total_sunk:,.2f}</td>
                </tr>
                <tr>
                    <td><strong>TOTAL NET (After Recovering Costs):</strong></td>
                    <td style="text-align:right; font-size:1.2em;" class="{'money-pos' if final_net > 0 else 'money-neg'}">${final_net:,.2f}</td>
                </tr>
            </table>
            <br>
            <p style="text-align:center; color:#888;">*If 'Monthly Net' is positive, you are printing money every month.</p>
        </div>
        """, unsafe_allow_html=True)
