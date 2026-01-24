import streamlit as st
import pandas as pd

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Breakout Hedge Commander v5.0", layout="wide", page_icon="🛡️")

# --- SESSION STATE ---
if 'phase1_status' not in st.session_state: st.session_state.phase1_status = "Pending"
if 'phase2_status' not in st.session_state: st.session_state.phase2_status = "Pending"

# --- STYLING ---
st.markdown("""
<style>
    .big-header { font-size: 22px; font-weight: bold; color: #4CAF50; margin-bottom: 10px; }
    .highlight-box { background-color: #262730; border: 1px solid #444; padding: 20px; border-radius: 10px; margin-bottom: 15px; }
    .success-text { color: #00FF7F; font-weight: bold; }
    .fail-text { color: #FF4B4B; font-weight: bold; }
    .metric-label { font-size: 0.9em; color: #aaa; }
    .metric-value { font-size: 1.4em; font-weight: bold; color: #fff; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Breakout Hedge Commander v5.0")
st.markdown("**Multi-Day 'Max Drain' Protocol + Intraday Toggle**")

# --- SIDEBAR: INPUTS ---
with st.sidebar:
    st.header("1. Account Rules")
    acct_size = st.number_input("Account Size ($)", 50000, step=10000)
    fee = st.number_input("Signup Fee ($)", 450)
    
    st.header("2. Risk Management")
    max_dd_pct = st.number_input("Max Drawdown Limit (%)", 8.0, help="Total allowed loss before account is blown.") / 100
    daily_dd_pct = st.number_input("Daily Drawdown Limit (%)", 5.0, help="Max loss in a single day.") / 100
    risk_per_trade_pct = st.number_input("RISK PER TRADE (%)", 4.0, help="Set this LOWER than Daily Limit (e.g. 4%) to survive multiple days.") / 100
    
    st.header("3. Hedge Ratios")
    ratio_p1 = st.number_input("Phase 1 Ratio", 5.8, step=0.1)
    ratio_p2 = st.number_input("Phase 2 Ratio", 3.2, step=0.1)
    ratio_funded = st.number_input("Funded Ratio", 0.75, step=0.05)
    
    st.header("4. Market Friction")
    comm_rate = st.number_input("Commission (%)", 0.04, format="%.4f") / 100
    
    # NEW: SWAP TOGGLE
    st.markdown("---")
    st.markdown("**⏱️ Duration Settings**")
    include_swap = st.checkbox("Include Rollover/Swap Fees?", value=True, help="Uncheck this if you plan to close trades within the same day (Intraday).")
    
    if include_swap:
        swap_rate = st.number_input("Swap/Funding (%)", 0.03, format="%.4f") / 100
        days_held = st.number_input("Avg Days Held", 2)
    else:
        swap_rate = 0.0
        days_held = 0.0

# --- ENGINE ---
def calculate_scenario(target_profit, ratio):
    # 1. Trade Sizing (Based on USER RISK PER TRADE, not Max DD)
    risk_amount_usd = acct_size * risk_per_trade_pct
    
    # Assume 1% Stop Loss Distance for sizing calculation
    sl_distance = 0.01 
    prop_size_notional = risk_amount_usd / sl_distance
    cex_size_notional = prop_size_notional / ratio
    
    # 2. Friction Costs (Swap is 0 if unchecked)
    prop_swap_cost = (prop_size_notional * swap_rate * days_held) if include_swap else 0
    cex_swap_cost = (cex_size_notional * swap_rate * days_held) if include_swap else 0
    
    prop_friction = (prop_size_notional * comm_rate * 2) + prop_swap_cost
    cex_friction = (cex_size_notional * comm_rate * 2) + cex_swap_cost
    
    # 3. SCENARIO A: PASS (One Shot)
    # To Net the target, we must Gross: Target + Friction
    prop_gross_needed = target_profit + prop_friction
    cex_loss_if_pass = (prop_gross_needed / ratio) + cex_friction
    
    # 4. SCENARIO B: TOTAL FAILURE (The "Drain" Strategy)
    # If we fail, we assume we drain the FULL Max Drawdown (e.g. 8%) over multiple days.
    # Total Drained Amount = Account * Max_DD_Pct
    total_prop_loss = acct_size * max_dd_pct
    
    # CEX Win = (Total_Prop_Loss / Ratio) - Total_Friction
    # Note: Friction applies to the total volume traded to lose that amount.
    total_cex_win = (total_prop_loss / ratio) - (cex_friction * (max_dd_pct/risk_per_trade_pct)) 
    
    return {
        "prop_size": prop_size_notional,
        "cex_size": cex_size_notional,
        "cex_loss_pass": cex_loss_if_pass,
        "cex_win_fail": total_cex_win,
        "risk_usd": risk_amount_usd,
        "trades_to_die": max_dd_pct / risk_per_trade_pct # How many trades until blown?
    }

# Run Calculations
p1 = calculate_scenario(acct_size * 0.05, ratio_p1)
p2 = calculate_scenario(acct_size * 0.10, ratio_p2)
funded = calculate_scenario(acct_size * 0.05, ratio_funded)

# --- DASHBOARD ---
tab1, tab2, tab3 = st.tabs(["PHASE 1 (Eval)", "PHASE 2 (Verify)", "PHASE 3 (Funded)"])

# === PHASE 1 ===
with tab1:
    st.markdown("<div class='big-header'>Phase 1: The Setup</div>", unsafe_allow_html=True)
    
    # Top Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Risk Per Trade (4%)", f"${p1['risk_usd']:,.0f}", help="Your loss if ONE trade hits Stop Loss")
    c2.metric("Daily Limit (5%)", f"${acct_size*daily_dd_pct:,.0f}", delta=f"${(acct_size*daily_dd_pct)-p1['risk_usd']:,.0f} Buffer")
    c3.metric("Prop Position Size", f"${p1['prop_size']:,.0f}", help="Notional Value (Leverage)")
    c4.metric("CEX Position Size", f"${p1['cex_size']:,.0f}", help="Hedge Short")

    st.markdown("---")
    
    st.markdown("### 🔮 Outcome Projection")
    col_pass, col_fail = st.columns(2)
    
    with col_pass:
        st.markdown("""<div class='highlight-box' style='border-color: #00FF7F'>
        <h3 class='success-text'>✅ IF YOU PASS</h3>
        <p>You hit the 5% Target in one trade.</p>
        </div>""", unsafe_allow_html=True)
        st.metric("Cost Paid on CEX", f"-${p1['cex_loss_pass']:,.2f}")
        
    with col_fail:
        st.markdown("""<div class='highlight-box' style='border-color: #FF4B4B'>
        <h3 class='fail-text'>❌ IF YOU FAIL (Full Drain)</h3>
        <p>You lose 4% today, then 4% tomorrow.</p>
        </div>""", unsafe_allow_html=True)
        st.metric("CEX Total Refund", f"+${p1['cex_win_fail']:,.2f}")
        net_res = p1['cex_win_fail'] - fee
        st.metric("Net Profit (Refund - Fee)", f"${net_res:,.2f}", delta_color="normal")

    # Action Buttons
    st.markdown("---")
    st.caption("Update status to proceed:")
    b1, b2 = st.columns(2)
    if b1.button("Phase 1 PASSED"): st.session_state.phase1_status = "Passed"; st.rerun()
    if b2.button("Phase 1 FAILED"): st.session_state.phase1_status = "Failed"; st.rerun()

    if st.session_state.phase1_status == "Failed":
        st.error(f"Account Blown. Net Result: ${net_res:,.2f}. If positive, you made profit failing.")

# === PHASE 2 ===
with tab2:
    if st.session_state.phase1_status != "Passed":
        st.warning("Complete Phase 1 to unlock.")
    else:
        st.markdown("<div class='big-header'>Phase 2: Verification</div>", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Risk Per Trade", f"${p2['risk_usd']:,.0f}")
        c2.metric("Prop Position Size", f"${p2['prop_size']:,.0f}")
        c3.metric("CEX Position Size", f"${p2['cex_size']:,.0f}")
        
        st.markdown("### 🔮 Outcome Projection")
        cp, cf = st.columns(2)
        with cp:
            st.info(f"**Cost to Pass P2:** ${p2['cex_loss_pass']:,.2f}")
        with cf:
            st.error(f"**Refund if Fail (Max Drain):** +${p2['cex_win_fail']:,.2f}")
            net_fail_p2 = p2['cex_win_fail'] - (fee + p1['cex_loss_pass'])
            st.caption(f"Net vs Sunk Costs: ${net_fail_p2:,.2f}")

        if st.button("Phase 2 PASSED"): st.session_state.phase2_status = "Passed"; st.rerun()

# === PHASE 3 ===
with tab3:
    if st.session_state.phase2_status != "Passed":
        st.warning("Complete Phase 2 to unlock.")
    else:
        st.markdown("<div class='big-header'>Phase 3: The Harvest</div>", unsafe_allow_html=True)
        
        total_sunk = fee + p1['cex_loss_pass'] + p2['cex_loss_pass']
        
        st.markdown(f"""
        <div class='highlight-box'>
            <h3>💰 Final Calculations</h3>
            <p><strong>Total Sunk Cost (Investment):</strong> <span style='color:#FF4B4B'>${total_sunk:,.2f}</span></p>
            <hr>
            <p>Target Profit (5%): <strong>${acct_size*0.05:,.0f}</strong></p>
            <p>Prop Payout (90%): <span style='color:#00FF7F'>+${(acct_size*0.05)*0.90:,.2f}</span></p>
            <p>CEX Hedge Burn: <span style='color:#FF4B4B'>-${funded['cex_loss_pass']:,.2f}</span></p>
            <hr>
            <h2>Net Take Home: ${(acct_size*0.05)*0.90 - funded['cex_loss_pass'] - total_sunk:,.2f}</h2>
        </div>
        """, unsafe_allow_html=True)

st.caption("v5.0 - Updated with Intraday (No Swap) Toggle")
