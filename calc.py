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

# --- 2. TRADING POWER & INPUTS GRID ---

# A. Risk Budget Display
if risk_budget <= 0:
    st.error(f"🚫 TRADING HALTED: You have hit your Liquidation Price.")
    st.stop()
else:
    color = "#00ff00" if risk_budget > 1000 else "#ffaa00" if risk_budget > 500 else "#ff4b4b"
    st.markdown(f"""
    <div style="text-align:center; padding:10px; border-radius:10px; background-color: #262730; border: 1px solid #444; margin-bottom: 15px;">
        <h3 style='margin:0; color: #aaa; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;'>Available Risk Budget</h3>
        <h2 style='margin:0; color: {color}; font-size: 36px; font-weight: 700;'>${risk_budget:,.2f}</h2>
    </div>
    """, unsafe_allow_html=True)

# B. Control Deck (Container for Inputs)
with st.container():
    # Row 1: Instrument & Mode
    c_inst, c_mode = st.columns([2, 1])
    with c_inst:
        instrument_mode = st.selectbox(
            "Select Instrument / View:",
            [
                "Compare All: NQ & ES",
                "Compare: Nasdaq (NQ & MNQ)",
                "Compare: S&P 500 (ES & MES)",
                "---",
                "Single: NQ (Mini)",
                "Single: MNQ (Micro)",
                "Single: ES (Mini)",
                "Single: MES (Micro)"
            ]
        )
    with c_mode:
        calc_mode = st.radio("Mode:", ["Risk Based ($)", "Manual Qty"], horizontal=True)

    # Determine View & Data
    if "Compare All" in instrument_mode:
        view_mode = "All"
        data = None
    elif "Compare: Nasdaq" in instrument_mode:
        view_mode = "Comparison"
        data = {"mini": "NQ", "micro": "MNQ", "mini_val": 20, "micro_val": 2}
    elif "Compare: S&P" in instrument_mode:
        view_mode = "Comparison"
        data = {"mini": "ES", "micro": "MES", "mini_val": 50, "micro_val": 5}
    elif "---" in instrument_mode:
        st.warning("Please select an instrument.")
        st.stop()
    else:
        view_mode = "Single"
        if "NQ" in instrument_mode: data = {"name": "NQ", "val": 20, "type": "mini"}
        elif "MNQ" in instrument_mode: data = {"name": "MNQ", "val": 2, "type": "micro"}
        elif "ES" in instrument_mode: data = {"name": "ES", "val": 50, "type": "mini"}
        elif "MES" in instrument_mode: data = {"name": "MES", "val": 5, "type": "micro"}

    # Row 2: Trade Parameters (SL, TP, Risk/Qty)
    st.markdown("---")
    
    # Initialize quantity variables
    user_risk_input = 0
    q_mini, q_micro, q_single = 0, 0, 0
    q_nq, q_mnq, q_es, q_mes = 0, 0, 0, 0
    
    if view_mode == "All":
        # 3 Column layout: SL stacked, TP stacked, Risk isolated on the right
        c_sl, c_tp, c_risk = st.columns(3)
        
        with c_sl:
            sl_nq = st.number_input("NQ Stop (Pts)", 1.0, 500.0, 10.0, 0.5)
            sl_es = st.number_input("ES Stop (Pts)", 1.0, 500.0, 4.0, 0.25)
            
        with c_tp:
            tp_nq = st.number_input("NQ Target (Pts)", 1.0, 1000.0, 20.0, 0.5)
            tp_es = st.number_input("ES Target (Pts)", 1.0, 1000.0, 8.0, 0.25)
            
        with c_risk:
            if "Risk Based" in calc_mode:
                rec_risk = min(500.0, float(risk_budget))
                user_risk_input = st.number_input("Risk Amount ($)", 50.0, 10000.0, rec_risk, 10.0)
                # Calculate directly now that SLs are defined
                q_nq = math.floor(user_risk_input / (sl_nq * 20))
                q_mnq = math.floor(user_risk_input / (sl_nq * 2))
                q_es = math.floor(user_risk_input / (sl_es * 50))
                q_mes = math.floor(user_risk_input / (sl_es * 5))
            else:
                st.caption("Manual Qty Selected 👇")
                user_risk_input = float('inf')

    else:
        # Standard 3 column layout for Single/Standard Comparison
        col_sl, col_tp, col_input = st.columns(3)
        with col_sl:
            sl_pts = st.number_input("Stop Loss (Points):", 1.0, 500.0, 10.0, 0.25)
        with col_tp:
            tp_pts = st.number_input("Take Profit (Points):", 1.0, 1000.0, 20.0, 0.25)
        
        with col_input:
            if "Risk Based" in calc_mode:
                rec_risk = min(500.0, float(risk_budget))
                user_risk_input = st.number_input("Willing to Risk ($):", 50.0, 10000.0, rec_risk, 10.0)
                
                if view_mode == "Comparison":
                    q_mini = math.floor(user_risk_input / (sl_pts * data["mini_val"]))
                    q_micro = math.floor(user_risk_input / (sl_pts * data["micro_val"]))
                else:
                    q_single = math.floor(user_risk_input / (sl_pts * data["val"]))
            else:
                if view_mode == "Comparison":
                    st.caption("Manual Qty Input Below 👇") 
                    user_risk_input = float('inf') 
                else:
                    q_single = st.number_input("Quantity:", 1, 1000, 1)
                    user_risk_input = float('inf')

    # Special Case: Manual Mode input rows
    if "Manual" in calc_mode:
        if view_mode == "All":
            c_q1, c_q2, c_q3, c_q4 = st.columns(4)
            with c_q1: q_nq = st.number_input("Qty NQ", 0, 100, 1)
            with c_q2: q_mnq = st.number_input("Qty MNQ", 0, 1000, 1)
            with c_q3: q_es = st.number_input("Qty ES", 0, 100, 1)
            with c_q4: q_mes = st.number_input("Qty MES", 0, 1000, 1)
        elif view_mode == "Comparison":
            c_q1, c_q2 = st.columns(2)
            with c_q1: q_mini = st.number_input(f"Qty {data['mini']}", 0, 100, 1)
            with c_q2: q_micro = st.number_input(f"Qty {data['micro']}", 0, 1000, 1)


# --- 3. CALCULATION ENGINE ---
def calculate_stats(qty, point_val, is_micro, active_sl, active_tp):
    if qty == 0: return None
    gross_risk = qty * active_sl * point_val
    gross_reward = qty * active_tp * point_val
    comm = (COMMISSIONS["micro"] if is_micro else COMMISSIONS["mini"]) * qty if use_commissions else 0
    return {
        "qty": qty, "net_risk": gross_risk + comm, 
        "net_reward": gross_reward - comm, "gross": gross_reward
    }

def get_rejection_reason(active_sl, val, user_risk, account_budget):
    one_contract_risk = active_sl * val
    if one_contract_risk > account_budget:
        return f"Insufficient Funds: 1 contract risks ${one_contract_risk:,.2f} but you only have ${account_budget:,.2f}."
    elif one_contract_risk > user_risk:
        return f"Exceeds Risk Limit: 1 contract risks ${one_contract_risk:,.2f} but limit is ${user_risk:,.2f}."
    else:
        return "Quantity is 0. Adjust inputs."

def check_violations(stats, limit_qty):
    violations = []
    if not stats: return []
    if stats["net_risk"] > risk_budget:
        violations.append(f"CRITICAL: Risk (${stats['net_risk']:,.2f}) > Available Budget.")
    if daily_loss > 0 and stats["net_risk"] > daily_loss:
        violations.append(f"Daily Limit: Risk (${stats['net_risk']:,.2f}) > Limit (${daily_loss:,.2f}).")
    if stats["qty"] > limit_qty:
        violations.append(f"Size Violation: {stats['qty']} > Max ({limit_qty}).")
    if stage == "Evaluation" and defaults["consistency"] > 0:
        limit_val = defaults["target"] * defaults["consistency"]
        if stats["gross"] > limit_val:
            violations.append(f"Consistency Warning: Profit (${stats['gross']:,.0f}) > Limit (${limit_val:,.0f}).")
    return violations


# --- 4. RENDER RESULTS ---
st.divider()

def render_card(title, icon, qty, point_val, is_micro, active_sl, active_tp):
    """Helper function to cleanly render any instrument's stats block."""
    st.subheader(f"{icon} {title}")
    stats = calculate_stats(qty, point_val, is_micro, active_sl, active_tp)
    limit = defaults["max_micros"] if is_micro else defaults["max_minis"]
    
    if stats:
        warns = check_violations(stats, limit)
        if warns:
            for w in warns: st.error(w)
        else:
            st.success("✅ Trade Approved")
            
        c1, c2 = st.columns(2)
        c1.metric("Risk", f"-${stats['net_risk']:,.2f}")
        c2.metric("Profit", f"+${stats['net_reward']:,.2f}")
        st.info(f"Size: **{stats['qty']}**")
    else:
        st.warning(get_rejection_reason(active_sl, point_val, user_risk_input, risk_budget))


# Execute Layout based on View Mode
if view_mode == "All":
    # NQ / MNQ Row
    col_nq, col_mnq = st.columns(2)
    with col_nq: render_card("NQ (Mini)", "🦁", q_nq, 20, False, sl_nq, tp_nq)
    with col_mnq: render_card("MNQ (Micro)", "🐭", q_mnq, 2, True, sl_nq, tp_nq)
    
    st.divider()
    
    # ES / MES Row
    col_es, col_mes = st.columns(2)
    with col_es: render_card("ES (Mini)", "🦅", q_es, 50, False, sl_es, tp_es)
    with col_mes: render_card("MES (Micro)", "🐥", q_mes, 5, True, sl_es, tp_es)

elif view_mode == "Comparison":
    col_a, col_b = st.columns(2)
    with col_a: render_card(f"{data['mini']} (Mini)", "🦁", q_mini, data["mini_val"], False, sl_pts, tp_pts)
    with col_b: render_card(f"{data['micro']} (Micro)", "🐭", q_micro, data["micro_val"], True, sl_pts, tp_pts)

else:
    # Single View
    render_card(f"{data['name']} Analysis", "📊", q_single, data["val"], data["type"] == "micro", sl_pts, tp_pts)
