import streamlit as st
import pandas as pd

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Breakout Hedge Commander v3.0", layout="wide", page_icon="🛡️")

# --- SESSION STATE INITIALIZATION ---
# This allows the app to remember where you are in the process
if 'phase1_status' not in st.session_state:
    st.session_state.phase1_status = "Pending" # Pending, Passed, Failed
if 'phase2_status' not in st.session_state:
    st.session_state.phase2_status = "Pending"
if 'current_step' not in st.session_state:
    st.session_state.current_step = 1

# --- STYLING ---
st.markdown("""
<style>
    .big-header { font-size: 24px; font-weight: bold; color: #4CAF50; margin-bottom: 10px; }
    .warning-box { background-color: #332b00; border-left: 5px solid #ffcc00; padding: 15px; border-radius: 5px; }
    .fail-box { background-color: #330000; border-left: 5px solid #ff4b4b; padding: 15px; border-radius: 5px; }
    .pass-box { background-color: #002200; border-left: 5px solid #00ff00; padding: 15px; border-radius: 5px; }
    .metric-container { background-color: #1E1E1E; padding: 10px; border-radius: 8px; border: 1px solid #333; text-align: center; }
    .stButton>button { width: 100%; border-radius: 5px; height: 50px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Breakout Hedge Commander v3.0")
st.markdown("**Interactive Execution Protocol with 'True Cost' Accounting**")

# --- SIDEBAR: INPUTS ---
with st.sidebar:
    st.header("⚙️ 1. Account Config")
    acct_size = st.number_input("Account Size ($)", 50000, step=10000)
    fee = st.number_input("Signup Fee ($)", 450)
    
    st.header("⚖️ 2. Strategy Ratios")
    ratio_p1 = st.number_input("Phase 1 Ratio (Prop:CEX)", 5.8, step=0.1, help="Higher = Cheaper hedge, but riskier refund.")
    ratio_p2 = st.number_input("Phase 2 Ratio", 3.2, step=0.1)
    ratio_funded = st.number_input("Funded Ratio", 0.75, step=0.05)
    
    st.header("📉 3. Risk & Friction")
    daily_dd_pct = st.number_input("Daily Drawdown Limit (%)", 5.0, help="Breakout is usually 5% daily.") / 100
    slippage_buffer = st.number_input("Safety Buffer (%)", 0.5, help="Reduces trade size to prevent daily breach.") / 100
    comm_rate = st.number_input("Commission (%)", 0.04, format="%.4f") / 100
    swap_rate = st.number_input("Daily Swap/Funding (%)", 0.03, format="%.4f") / 100
    days_held = st.number_input("Est. Days to Pass", 2)

# --- BACKEND CALCULATION ENGINE ---
def calculate_metrics(target_profit, ratio, is_funded=False):
    # 1. Safe Risk Limit (Daily DD - Buffer)
    safe_risk_usd = acct_size * (daily_dd_pct - slippage_buffer)
    
    # 2. Position Sizing (Derived from Safe Risk)
    # We assume a standard stop loss distance (e.g. 1%) to calculate leverage/size
    # If SL is 1%, Size = Risk / 0.01
    sl_distance = 0.01 
    prop_size_notional = safe_risk_usd / sl_distance
    cex_size_notional = prop_size_notional / ratio
    
    # 3. True Cost Calculation (Friction)
    # How much extra do we need to win on Prop to cover fees?
    prop_friction = (prop_size_notional * comm_rate * 2) + (prop_size_notional * swap_rate * days_held)
    cex_friction = (cex_size_notional * comm_rate * 2) + (cex_size_notional * swap_rate * days_held)
    
    # 4. Gross Targets
    # To NET the target profit, Prop must Gross: Target + Prop Friction
    required_prop_gross = target_profit + prop_friction
    
    # 5. CEX Impact
    # If Prop wins (Pass): CEX loses (Gross Win / Ratio) + CEX Friction
    cex_loss_if_pass = (required_prop_gross / ratio) + cex_friction
    
    # If Prop fails (Fail): CEX wins (Risk / Ratio) - CEX Friction
    cex_win_if_fail = (safe_risk_usd / ratio) - cex_friction
    
    return {
        "prop_size": prop_size_notional,
        "cex_size": cex_size_notional,
        "cex_loss_pass": cex_loss_if_pass,
        "cex_win_fail": cex_win_if_fail,
        "safe_risk": safe_risk_usd,
        "prop_friction": prop_friction
    }

# Run Calcs
p1 = calculate_metrics(acct_size * 0.05, ratio_p1)
p2 = calculate_metrics(acct_size * 0.10, ratio_p2)
funded = calculate_metrics(acct_size * 0.05, ratio_funded, is_funded=True) # 5% profit target for funded

# --- MAIN INTERFACE ---

# PROGRESS BAR
progress = 0
if st.session_state.phase1_status == "Passed": progress = 50
if st.session_state.phase2_status == "Passed": progress = 100
st.progress(progress)

# TABS (Controlled by Session State)
tab1, tab2, tab3 = st.tabs(["1️⃣ PHASE 1 (Eval)", "2️⃣ PHASE 2 (Verify)", "3️⃣ FUNDED (Harvest)"])

# ================= PHASE 1 =================
with tab1:
    st.markdown("<div class='big-header'>Phase 1: The Filter</div>", unsafe_allow_html=True)
    
    # 1. SETUP SECTION
    c1, c2, c3 = st.columns(3)
    with c1:
        st.info("🎯 **Target: Reach +5%**")
        st.write(f"Net Profit Needed: **${acct_size*0.05:,.0f}**")
        st.caption(f"Est. Friction/Fees: -${p1['prop_friction']:,.2f}")
    with c2:
        st.warning(f"🛑 **Max Risk: -${p1['safe_risk']:,.0f}**")
        st.write(f"Based on {daily_dd_pct*100}% Daily Limit")
        st.caption(f"Includes {slippage_buffer*100}% Buffer")
    with c3:
        st.error("**Hedge Ratio: " + str(ratio_p1) + "**")
        st.write(f"Prop Size: **${p1['prop_size']:,.0f}**")
        st.write(f"CEX Size: **${p1['cex_size']:,.0f}**")

    st.markdown("---")
    
    # 2. CHECKLIST
    st.subheader("✅ Execution Checklist")
    chk1 = st.checkbox("1. I have deposited funds into CEX.", key="p1_c1")
    chk2 = st.checkbox(f"2. I have calculated Lot Size for ${p1['prop_size']:,.0f} (Prop) and ${p1['cex_size']:,.0f} (CEX).", key="p1_c2")
    chk3 = st.checkbox("3. I have opened BOTH trades simultaneously.", key="p1_c3")
    
    if chk1 and chk2 and chk3:
        st.markdown("### 🎱 Report Outcome")
        col_pass, col_fail = st.columns(2)
        
        with col_pass:
            if st.button("✅ Phase 1 PASSED"):
                st.session_state.phase1_status = "Passed"
                st.rerun()
        
        with col_fail:
            if st.button("❌ Phase 1 FAILED (Hit Stop)"):
                st.session_state.phase1_status = "Failed"
                st.rerun()

    # 3. RESULT DISPLAY
    if st.session_state.phase1_status == "Passed":
        st.markdown(f"""
        <div class='pass-box'>
            <h3>🎉 Phase 1 Complete</h3>
            <p>You paid <b>${p1['cex_loss_pass']:,.2f}</b> on CEX to pass Phase 1.</p>
            <p><strong>Status:</strong> Unlocking Phase 2...</p>
        </div>
        """, unsafe_allow_html=True)
        
    elif st.session_state.phase1_status == "Failed":
        refund = p1['cex_win_fail']
        net = refund - fee
        color = "green" if net > 0 else "red"
        st.markdown(f"""
        <div class='fail-box'>
            <h3>💀 Phase 1 Failed</h3>
            <p>Prop Account Blown (Hit Daily Limit).</p>
            <p>CEX Profit: <b>+${refund:,.2f}</b></p>
            <p>Evaluation Fee: <b>-${fee:,.2f}</b></p>
            <hr>
            <h2 style='color:{color}'>Net Result: ${net:,.2f}</h2>
            <p><em>Check your bankroll. If positive, you made money failing. Buy a new account.</em></p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🔄 Reset / Try Again"):
            st.session_state.phase1_status = "Pending"
            st.session_state.phase2_status = "Pending"
            st.rerun()

# ================= PHASE 2 =================
with tab2:
    if st.session_state.phase1_status != "Passed":
        st.markdown("### 🔒 Locked")
        st.warning("Please complete Phase 1 successfully to unlock this step.")
    else:
        st.markdown("<div class='big-header'>Phase 2: Verification</div>", unsafe_allow_html=True)
        
        # 1. SETUP
        c1, c2, c3 = st.columns(3)
        with c1:
            st.info("🎯 **Target: Reach +10%**")
            st.write(f"Net Profit Needed: **${acct_size*0.10:,.0f}**")
        with c2:
            st.warning(f"🛑 **Max Risk: -${p2['safe_risk']:,.0f}**")
        with c3:
            st.error("**Hedge Ratio: " + str(ratio_p2) + "**")
            st.write(f"Prop Size: **${p2['prop_size']:,.0f}**")
            st.write(f"CEX Size: **${p2['cex_size']:,.0f}**")

        st.markdown("---")
        
        # 2. CHECKLIST
        st.subheader("✅ Execution Checklist")
        chk_p2_1 = st.checkbox("1. I have adjusted CEX leverage for new ratio.", key="p2_c1")
        chk_p2_2 = st.checkbox(f"2. I have opened Prop Long (${p2['prop_size']:,.0f}) and CEX Short (${p2['cex_size']:,.0f}).", key="p2_c2")
        
        if chk_p2_1 and chk_p2_2:
            st.markdown("### 🎱 Report Outcome")
            col_pass_2, col_fail_2 = st.columns(2)
            
            with col_pass_2:
                if st.button("✅ Phase 2 PASSED"):
                    st.session_state.phase2_status = "Passed"
                    st.rerun()
            
            with col_fail_2:
                if st.button("❌ Phase 2 FAILED"):
                    st.session_state.phase2_status = "Failed"
                    st.rerun()

        # 3. RESULT DISPLAY
        if st.session_state.phase2_status == "Passed":
            total_sunk = fee + p1['cex_loss_pass'] + p2['cex_loss_pass']
            st.markdown(f"""
            <div class='pass-box'>
                <h3>🏆 YOU ARE FUNDED!</h3>
                <p>Phase 2 Cost: <b>${p2['cex_loss_pass']:,.2f}</b></p>
                <hr>
                <h4>💰 Total Investment: ${total_sunk:,.2f}</h4>
                <p>This is the amount you need to recover in Phase 3.</p>
            </div>
            """, unsafe_allow_html=True)
            
        elif st.session_state.phase2_status == "Failed":
            refund_p2 = p2['cex_win_fail']
            sunk_p1 = fee + p1['cex_loss_pass']
            net_p2 = refund_p2 - sunk_p1
            st.markdown(f"""
            <div class='fail-box'>
                <h3>💀 Phase 2 Failed</h3>
                <p>CEX Profit: <b>+${refund_p2:,.2f}</b></p>
                <p>Sunk Costs (Fee + P1): <b>-${sunk_p1:,.2f}</b></p>
                <hr>
                <h2 style='color:red'>Net Loss: ${net_p2:,.2f}</h2>
                <p>You recovered some capital, but not all. Restart.</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("🔄 Reset"):
                st.session_state.phase1_status = "Pending"
                st.session_state.phase2_status = "Pending"
                st.rerun()

# ================= PHASE 3 =================
with tab3:
    if st.session_state.phase2_status != "Passed":
        st.markdown("### 🔒 Locked")
        st.warning("Get Funded (Pass Phase 2) to see this section.")
    else:
        st.markdown("<div class='big-header'>Phase 3: The Harvest</div>", unsafe_allow_html=True)
        st.info("ℹ️ Strategy Change: Now we want the PROP account to WIN. We burn CEX cash to secure the 90% Payout.")
        
        funded_target = acct_size * 0.05
        total_sunk = fee + p1['cex_loss_pass'] + p2['cex_loss_pass']
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 📊 Trade Setup")
            st.write(f"Target Profit (5%): **${funded_target:,.0f}**")
            st.write(f"Prop Size: **${funded['prop_size']:,.0f}**")
            st.write(f"CEX Size (Hedge): **${funded['cex_size']:,.0f}**")
        
        with c2:
            st.markdown("### 💰 Financial Projection")
            prop_payout = funded_target * 0.90
            cex_burn = funded['cex_loss_pass']
            net_take_home = prop_payout - cex_burn
            
            st.write(f"Expected Payout (90%): **+${prop_payout:,.2f}**")
            st.write(f"CEX Hedge Loss: **-${cex_burn:,.2f}**")
            st.write(f"Previous Sunk Costs: **-${total_sunk:,.2f}**")
            
            final_pnl = net_take_home - total_sunk
            
            if final_pnl > 0:
                st.success(f"🎉 TOTAL PROFIT (After recovering all costs): +${final_pnl:,.2f}")
            else:
                st.warning(f"⚠️ almost break-even. You need {abs(final_pnl/net_take_home):.1f} more payouts to be profitable.")

st.markdown("---")
st.caption("v3.0 - 'True Cost' algorithm active. Slippage, Swaps, and Commissions included in all PnL projections.")
