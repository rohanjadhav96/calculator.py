import streamlit as st
import pandas as pd

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Breakout Hedge Commander v8.0 (Fixed)", layout="wide", page_icon="🛡️")

# --- SESSION STATE ---
if 'phase1_status' not in st.session_state: st.session_state.phase1_status = "Pending"
if 'phase2_status' not in st.session_state: st.session_state.phase2_status = "Pending"

# --- STYLING ---
st.markdown("""
<style>
    .doctor-box { background-color: #0e1117; border: 1px solid #FFD700; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
    .doctor-title { color: #FFD700; font-weight: bold; font-size: 1.1em; display: flex; align-items: center; }
    .big-header { font-size: 22px; font-weight: bold; color: #4CAF50; margin-bottom: 10px; }
    
    /* Result Boxes */
    .pass-box { background-color: #0d3316; border: 1px solid #1f7a37; padding: 20px; border-radius: 10px; text-align: center; }
    .fail-box { background-color: #330d0d; border: 1px solid #7a1f1f; padding: 20px; border-radius: 10px; text-align: center; }
    
    /* Profit/Loss Colors */
    .money-pos { color: #00FF7F; font-weight: bold; font-size: 1.1em; }
    .money-neg { color: #FF4B4B; font-weight: bold; font-size: 1.1em; }
    .money-neutral { color: #aaa; font-weight: bold; }
    
    hr { margin: 10px 0; border-color: #444; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Breakout Hedge Commander v8.0")
st.markdown("**Fixed: Unique Button IDs & Detailed Net/Gross Profit Breakdown**")

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
    if st.button("🔄 FULL RESET", key="sidebar_reset"):
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
            if st.button("Phase 1 PASSED", key="p1_pass_btn"): st.session_state.phase1_status = "Passed"; st.rerun()
        with cf:
            st.error(f"**Refund if Fail:** +${p1['cex_win_fail']:,.2f}")
            if st.button("Phase 1 FAILED", key="p1_fail_btn"): st.session_state.phase1_status = "Failed"; st.rerun()

    elif st.session_state.phase1_status == "Passed":
        # Detailed Pass Screen
        st.markdown(f"""
        <div class='pass-box'>
            <h3>✅ Phase 1 Passed</h3>
            <p>You survived, but you paid a cost to hedge.</p>
            <hr>
            <p>Gross Profit (Inflow): <span class='money-neutral'>$0.00</span></p>
            <p>Cost Incurred (CEX Loss): <span class='money-neg'>-${p1['cex_loss_pass']:,.2f}</span></p>
            <p>Evaluation Fee: <span class='money-neg'>-${fee:,.2f}</span></p>
            <hr>
            <h4>Current Net Position: <span class='money-neg'>-${p1['cex_loss_pass'] + fee:,.2f}</span></h4>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Undo Phase 1", key="undo_p1"): st.session_state.phase1_status = "Pending"; st.rerun()

    elif st.session_state.phase1_status == "Failed":
        # Detailed Fail Screen
        net_result = p1['cex_win_fail'] - fee
        color_class = "money-pos" if net_result > 0 else "money-neg"
        
        st.markdown(f"""
        <div class='fail-box'>
            <h3>❌ Phase 1 Failed (Account Blown)</h3>
            <p>You drained the Prop account to your CEX account.</p>
            <hr>
            <p>Gross Profit (CEX Refund): <span class='money-pos'>+${p1['cex_win_fail']:,.2f}</span></p>
            <p>Investment Lost (Fee): <span class='money-neg'>-${fee:,.2f}</span></p>
            <hr>
            <h4>Final Net Profit: <span class='{color_class}'>${net_result:,.2f}</span></h4>
            <p><em>(This is what lands in your pocket after covering the fee)</em></p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Restart / Reset", key="restart_p1"): st.session_state.phase1_status = "Pending"; st.rerun()

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
            if st.button("Phase 2 PASSED", key="p2_pass_btn"): st.session_state.phase2_status = "Passed"; st.rerun()
        with cf:
            st.error(f"**Refund if Fail:** +${p2['cex_win_fail']:,.2f}")
            if st.button("Phase 2 FAILED", key="p2_fail_btn"): st.session_state.phase2_status = "Failed"; st.rerun()

    elif st.session_state.phase2_status == "Passed":
        # Detailed Pass Screen P2
        total_sunk = fee + p1['cex_loss_pass'] + p2['cex_loss_pass']
        st.markdown(f"""
        <div class='pass-box'>
            <h3>🏆 YOU ARE FUNDED!</h3>
            <p>You have passed both stages.</p>
            <hr>
            <p>Phase 1 Cost: <span class='money-neg'>-${p1['cex_loss_pass']:,.2f}</span></p>
            <p>Phase 2 Cost: <span class='money-neg'>-${p2['cex_loss_pass']:,.2f}</span></p>
            <p>Evaluation Fee: <span class='money-neg'>-${fee:,.2f}</span></p>
            <hr>
            <h4>Total Sunk Cost (Investment): <span class='money-neg'>-${total_sunk:,.2f}</span></h4>
            <p><em>(You must recover this amount in Phase 3 to break even)</em></p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Undo Phase 2", key="undo_p2"): st.session_state.phase2_status = "Pending"; st.rerun()

    elif st.session_state.phase2_status == "Failed":
        # Detailed Fail Screen P2
        gross_refund = p2['cex_win_fail']
        sunk_costs = fee + p1['cex_loss_pass']
        net_result = gross_refund - sunk_costs
        color_class = "money-pos" if net_result > 0 else "money-neg"
        
        st.markdown(f"""
        <div class='fail-box'>
            <h3>❌ Phase 2 Failed</h3>
            <p>You failed at the finish line, but recovered funds via hedging.</p>
            <hr>
            <p>Gross Profit (CEX Refund): <span class='money-pos'>+${gross_refund:,.2f}</span></p>
            <p>Sunk Costs (Fee + P1 Cost): <span class='money-neg'>-${sunk_costs:,.2f}</span></p>
            <hr>
            <h4>Final Net Profit: <span class='{color_class}'>${net_result:,.2f}</span></h4>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Restart Phase 2", key="restart_p2"): st.session_state.phase2_status = "Pending"; st.rerun()

# === PHASE 3 ===
with tab3:
    if st.session_state.phase2_status != "Passed":
        st.warning("Locked: Complete Phase 2 first.")
    else:
        st.markdown("<div class='big-header'>Phase 3: Harvest</div>", unsafe_allow_html=True)
        total_sunk = fee + p1['cex_loss_pass'] + p2['cex_loss_pass']
        
        # Calculate Phase 3 PnL
        payout_gross = (acct_size*0.05)*0.90 # 90% split of 5% profit
        hedge_burn = funded['cex_loss_pass'] # Cost to guarantee payout
        
        # Net from Payout alone
        net_from_payout = payout_gross - hedge_burn
        
        # Total Life-cycle Net
        final_net_profit = net_from_payout - total_sunk
        
        color_final = "money-pos" if final_net_profit > 0 else "money-neg"
        
        st.markdown(f"""
        <div class="doctor-box">
            <h3 style="color: #FFD700">💰 Final Profit Calculation</h3>
            <table style="width:100%; color: white;">
                <tr>
                    <td>Prop Firm Payout (90%):</td>
                    <td style="text-align:right;" class="money-pos">+${payout_gross:,.2f}</td>
                </tr>
                <tr>
                    <td>CEX Hedge Burn (Cost):</td>
                    <td style="text-align:right;" class="money-neg">-${hedge_burn:,.2f}</td>
                </tr>
                <tr>
                    <td><strong>Net Payout Profit:</strong></td>
                    <td style="text-align:right;"><strong>${net_from_payout:,.2f}</strong></td>
                </tr>
                <tr><td colspan="2"><hr></td></tr>
                <tr>
                    <td>Previous Sunk Costs (Fee + P1 + P2):</td>
                    <td style="text-align:right;" class="money-neg">-${total_sunk:,.2f}</td>
                </tr>
                <tr>
                    <td style="font-size: 1.2em;"><strong>TOTAL NET PROFIT:</strong></td>
                    <td style="text-align:right; font-size: 1.2em;" class="{color_final}">${final_net_profit:,.2f}</td>
                </tr>
            </table>
        </div>
        """, unsafe_allow_html=True)
