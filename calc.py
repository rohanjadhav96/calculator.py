import streamlit as st
import math

# --- Page Config ---
st.set_page_config(page_title="Prop Command Center", page_icon="🛡️", layout="wide")

# --- Constants ---
COMMISSIONS = {
    "mini": 3.98,  # NQ/ES Round trip estimate
    "micro": 0.88  # MNQ/MES Round trip estimate
}

# Account Presets
PRESETS = {
    "Lucid Flex 50k": {
        "size": 50000, "target": 3000, "consistency": 0.50,
        "max_dd": 2000, "max_minis": 4, "max_micros": 40, "daily_loss": 0,
        "desc": "Lucid Flex 50k: $2k EOD Drawdown, 50% Consistency."
    },
    "Tradeify Select 50k": {
        "size": 50000, "target": 2500, "consistency": 0.40,
        "max_dd": 2000, "max_minis": 4, "max_micros": 40, "daily_loss": 0,
        "desc": "Tradeify Select: Stricter 40% consistency, lower target."
    },
    "🛠️ Custom / Other": {
        "size": 50000, "target": 3000, "consistency": 0.0,
        "max_dd": 2000, "max_minis": 10, "max_micros": 100, "daily_loss": 0,
        "desc": "Manually enter rules for any other prop firm."
    }
}

st.title("🛡️ Prop Command Center")

# --- SIDEBAR: LIVE SESSION DATA ---
with st.sidebar:
    st.header("🔴 Live Session Data")
    
    current_balance = st.number_input(
        "Current Account Balance ($):", 
        value=50000.0, step=100.0,
        help="Your actual Account Balance (Net Liq) right now."
    )
    
    liq_price = st.number_input(
        "Liquidation Price (Hard Stop) ($):", 
        value=48000.0, step=100.0,
        help="The EXACT price where your account is blown. (Copy from Rithmic/Tradovate 'Auto-Liquidate Threshold')."
    )
    
    # Calculate Risk Budget
    risk_budget = max(0.0, current_balance - liq_price)
    
    st.divider()
    use_commissions = st.checkbox("Include Commissions?", value=True)
    
    st.divider()
    st.caption("⚙️ Configuration")
    account_choice = st.selectbox("Account Preset:", list(PRESETS.keys()))
    stage = st.selectbox("Stage:", ["Evaluation", "Funded"])

# Load Rules
defaults = PRESETS[account_choice]
is_custom = (account_choice == "🛠️ Custom / Other")

# --- 1. RULES EXPANDER ---
with st.expander("📝 Account Rules (Click to Edit)", expanded=False):
    st.caption(defaults.get("desc", ""))
    c1, c2, c3 = st.columns(3)
    with c1:
        acc_size = st.number_input("Account Size", defaults["size"], disabled=not is_custom)
        max_dd = st.number_input("Max Drawdown", defaults["max_dd"], disabled=not is_custom)
    with c2:
        profit_target = st.number_input("Profit Target", defaults["target"], disabled=not is_custom)
        consistency_pct = st.number_input("Consistency %", defaults["consistency"], disabled=not is_custom)
    with c3:
        limit_mini = st.number_input("Max Minis", defaults["max_minis"], disabled=not is_custom)
        limit_micro = st.number_input("Max Micros", defaults["max_micros"], disabled=not is_custom)
        daily_loss = st.number_input("Daily Loss Limit ($)", defaults["daily_loss"], disabled=not is_custom)

# --- 2. RISK BUDGET DISPLAY ---
st.subheader("🛡️ Trading Power")

if risk_budget <= 0:
    st.error(f"🚫 **TRADING HALTED:** You have hit your Liquidation Price.")
    st.stop()
else:
    pct_health = min(1.0, risk_budget / defaults["max_dd"])
    color = "green" if pct_health > 0.5 else "orange" if pct_health > 0.25 else "red"
    
    col_health1, col_health2 = st.columns([1, 3])
    with col_health1:
        st.markdown(f"""
        <div style="text-align:center; padding:10px; border-radius:8px; background-color: #262730; border: 1px solid #555;">
            <div style='font-size: 24px; font-weight: bold; color: {color};'>${risk_budget:,.2f}</div>
            <div style='font-size: 12px; color: #aaa;'>Available Risk</div>
        </div>
        """, unsafe_allow_html=True)
    with col_health2:
        st.progress(pct_health, text="Distance to Liquidation")

st.divider()

# --- 3. CALCULATOR UI ---
c1, c2, c3 = st.columns([1,1,2])
with c1:
    view_mode = st.radio("View Mode:", ["Comparison (Mini vs Micro)", "Single Instrument"])
with c2:
    calc_mode = st.radio("Calculation Mode:", ["Risk Based ($)", "Manual Qty"])
with c3:
    if "Comparison" in view_mode:
        asset_group = st.selectbox("Asset Group:", ["Nasdaq (NQ & MNQ)", "S&P 500 (ES & MES)"])
        data = {"mini":"NQ", "micro":"MNQ", "mini_val":20, "micro_val":2} if "Nasdaq" in asset_group else {"mini":"ES", "micro":"MES", "mini_val":50, "micro_val":5}
    else:
        single_asset = st.selectbox("Instrument:", ["NQ", "MNQ", "ES", "MES"])
        map_ = {"NQ":20, "MNQ":2, "ES":50, "MES":5}
        type_ = "mini" if single_asset in ["NQ", "ES"] else "micro"
        data = {"name":single_asset, "val":map_[single_asset], "type":type_}

c_sl, c_tp = st.columns(2)
sl_pts = c_sl.number_input("Stop Loss (Pts):", 1.0, 500.0, 10.0, 0.5)
tp_pts = c_tp.number_input("Take Profit (Pts):", 1.0, 1000.0, 20.0, 0.5)

# --- 4. CALCULATION ENGINE ---
def calculate_stats(qty, point_val, is_micro):
    if qty == 0: return None
    gross_risk = qty * sl_pts * point_val
    gross_reward = qty * tp_pts * point_val
    comm = (COMMISSIONS["micro"] if is_micro else COMMISSIONS["mini"]) * qty if use_commissions else 0
    return {
        "qty": qty, "net_risk": gross_risk + comm, 
        "net_reward": gross_reward - comm, "gross": gross_reward
    }

def get_rejection_reason(sl, val, user_risk, account_budget):
    """Diagnose why the trade quantity is zero"""
    one_contract_risk = sl * val
    
    if one_contract_risk > account_budget:
        return f"💀 **Insufficient Account Funds:**\n\n1 contract risks **${one_contract_risk:,.0f}**, but you only have **${account_budget:,.0f}** before liquidation."
    elif one_contract_risk > user_risk:
        return f"📉 **Exceeds User Risk Limit:**\n\n1 contract risks **${one_contract_risk:,.0f}**, but you only wanted to risk **${user_risk:,.0f}**."
    else:
        return "⚠️ Quantity is 0. Increase risk amount or decrease Stop Loss."

# --- 5. THE WARNING SYSTEM (Rule Guardian) ---
def check_violations(stats, limit_qty, type_name):
    violations = []
    if not stats: return []
    if stats["net_risk"] > risk_budget:
        violations.append(f"❌ **CRITICAL:** Risk (${stats['net_risk']:.0f}) > Available Funds (${risk_budget:.0f}). You will be liquidated.")
    if daily_loss > 0 and stats["net_risk"] > daily_loss:
        violations.append(f"❌ **Daily Limit:** Risk (${stats['net_risk']:.0f}) exceeds Daily Loss Limit (${daily_loss}).")
    if stats["qty"] > limit_qty:
        violations.append(f"⚠️ **Size Violation:** {stats['qty']} contracts > Max Allowed ({limit_qty}).")
    if stage == "Evaluation" and defaults["consistency"] > 0:
        limit_val = defaults["target"] * defaults["consistency"]
        if stats["gross"] > limit_val:
            violations.append(f"⚠️ **Consistency Risk:** Profit (${stats['gross']:.0f}) > 50% Daily Limit (${limit_val:.0f}).")
    return violations

# --- 6. RENDER RESULTS ---
st.divider()

# Variables to hold inputs for diagnostics
user_risk_input = 0 

if "Comparison" in view_mode:
    # Auto-Calc Logic
    if "Risk Based" in calc_mode:
        rec_risk = min(500.0, float(risk_budget))
        user_risk_input = st.number_input("Willing to Risk ($):", 50.0, 10000.0, rec_risk, 10.0)
        q_mini = math.floor(user_risk_input / (sl_pts * data["mini_val"]))
        q_micro = math.floor(user_risk_input / (sl_pts * data["micro_val"]))
    else:
        col_q1, col_q2 = st.columns(2)
        q_mini = col_q1.number_input(f"Qty {data['mini']}", 0, 100, 1)
        q_micro = col_q2.number_input(f"Qty {data['micro']}", 0, 1000, 1)
        # In manual mode, we treat "user risk" as infinite since they set quantity directly
        user_risk_input = float('inf')

    # Get Stats
    stats_mini = calculate_stats(q_mini, data["mini_val"], False)
    stats_micro = calculate_stats(q_micro, data["micro_val"], True)
    
    # Check Violations
    warn_mini = check_violations(stats_mini, defaults["max_minis"], "Mini")
    warn_micro = check_violations(stats_micro, defaults["max_micros"], "Micro")

    col_a, col_b = st.columns(2)
    
    # --- MINI COLUMN ---
    with col_a:
        st.subheader(f"🦁 {data['mini']} (Mini)")
        if stats_mini:
            if warn_mini:
                for w in warn_mini: st.error(w)
            else:
                st.success("✅ Trade Approved")
            st.info(f"Size: **{stats_mini['qty']}**")
            st.metric("Risk", f"-${stats_mini['net_risk']:,.2f}")
            st.metric("Profit", f"+${stats_mini['net_reward']:,.2f}")
        else:
            # DIAGNOSTIC MESSAGE
            reason = get_rejection_reason(sl_pts, data["mini_val"], user_risk_input, risk_budget)
            st.warning(reason)
            
    # --- MICRO COLUMN ---
    with col_b:
        st.subheader(f"🐭 {data['micro']} (Micro)")
        if stats_micro:
            if warn_micro:
                for w in warn_micro: st.error(w)
            else:
                st.success("✅ Trade Approved")
            st.info(f"Size: **{stats_micro['qty']}**")
            st.metric("Risk", f"-${stats_micro['net_risk']:,.2f}")
            st.metric("Profit", f"+${stats_micro['net_reward']:,.2f}")
        else:
            # DIAGNOSTIC MESSAGE
            reason = get_rejection_reason(sl_pts, data["micro_val"], user_risk_input, risk_budget)
            st.warning(reason)

else:
    # Single View Logic
    limit = defaults["max_minis"] if data["type"] == "mini" else defaults["max_micros"]
    if "Risk Based" in calc_mode:
        rec_risk = min(500.0, float(risk_budget))
        user_risk_input = st.number_input("Willing to Risk ($):", 50.0, 10000.0, rec_risk, 10.0)
        qty = math.floor(user_risk_input / (sl_pts * data["val"]))
    else:
        qty = st.number_input("Quantity:", 1, 1000, 1)
        user_risk_input = float('inf')

    stats = calculate_stats(qty, data["val"], data["type"] == "micro")
    
    if stats:
        warnings = check_violations(stats, limit, "Single")
        st.subheader(f"📊 {data['name']} Analysis")
        if warnings:
            for w in warnings: st.error(w)
        else:
            st.success("✅ Trade Rules Passed")
        m1, m2, m3 = st.columns(3)
        m1.metric("Net Risk", f"-${stats['net_risk']:,.2f}")
        m2.metric("Net Profit", f"+${stats['net_reward']:,.2f}")
        m3.metric("R:R", f"1 : {tp_pts/sl_pts:.1f}")
    else:
        # DIAGNOSTIC MESSAGE (Single View)
        st.subheader(f"📊 {data['name']} Analysis")
        reason = get_rejection_reason(sl_pts, data["val"], user_risk_input, risk_budget)
        st.warning(reason)
