import streamlit as st
import pandas as pd
import math

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Breakout Hedge Commander v52", layout="wide", page_icon="🛡️")

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
    .info-box { background-color: #1c1c1c; padding: 10px; border-left: 3px solid #888; font-size: 0.9em; color: #ccc; margin-bottom: 10px; }
    .success-box { background-color: #0a1f0a; padding: 10px; border-left: 3px solid #00FF7F; font-size: 0.9em; color: #ccffcc; margin-bottom: 10px; }
    .farm-box { background-color: #1a1a0a; padding: 10px; border-left: 3px solid #FFD700; font-size: 0.9em; color: #fffacd; margin-bottom: 10px; }
    .safety-box { background-color: #0d1b2a; border: 1px solid #4169e1; padding: 15px; border-radius: 8px; margin-top: 10px; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Breakout Hedge Commander v52")
st.caption("Update: Dual Strategy Arbitrage (Classic 0.41 vs Pro 0.294)")

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
    
    # 20% Add-on Logic + 2% MATCH Discount
    add_on = base_fee * 0.20 if "90%" in split_choice else 0.0
    raw_fee = base_fee + add_on
    final_fee = raw_fee * 0.98  # Fixed MATCH 2% Code
    
    st.metric(f"Final Cost (with 'MATCH')", f"${final_fee:.2f}", f"+${add_on:.2f} for 90%" if add_on > 0 else None, delta_color="off")
    
    acct_size = acct_choice
    fee = final_fee
    profit_split_pct = 0.90 if "90%" in split_choice else 0.80

    st.header("3. Prop Firm Settings")
    
    # DYNAMIC TARGETS AND DRAWDOWNS
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
    else: # 2-Step Classic
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
    cex_loss_pass = (prop_gross * ratio_val) + (cex_size * cex_comm_rate
