import streamlit as st
import math

# --- Page Config ---
st.set_page_config(page_title="Prop Command Center", page_icon="🚀", layout="wide")

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

st.title("🚀 Prop Command Center")

# --- SIDEBAR: LIVE SESSION DATA ---
with st.sidebar:
    st.header("🔴 Live Session Data")
    
    current_pnl = st.number_input(
        "Current Daily P&L ($):", 
        value=0.0, step=50.0,
        help="Enter your Realized P&L for today. \n\nIf you are down -$500, the calculator will reduce your risk budget to prevent blowing the account."
    )
    
    st.divider()
    
    use_commissions = st.checkbox(
        "Include Commissions?", 
        value=True,
        help="If checked, subtracts estimated commissions from profits and adds them to losses.\n\n(~ $4.00 for Minis, ~$0.88 for Micros)"
    )
    
    st.divider()
    st.caption("⚙️ Configuration")
    
    account_choice = st.selectbox(
        "Account Preset:", 
        list(PRESETS.keys()),
        help="Select your Prop Firm account type to auto-load rules (Drawdown, Limits, etc.)."
    )
    
    stage = st.selectbox(
        "Stage:", 
        ["Evaluation", "Funded"],
        help="Evaluation often has Consistency Rules. Funded accounts usually remove them but keep Drawdown limits."
    )

# Load Rules
defaults = PRESETS[account_choice]
is_custom = (account_choice == "🛠️ Custom / Other")

# --- 1. RULES EXPANDER (With Tooltips) ---
with st.expander("📝 Account Rules (Click to Edit Custom)", expanded=False):
    st.caption(defaults.get("desc", ""))
    col1, col2, col3 = st.columns(3)
    
    with col1:
        acc_size = st.number_input("Account Size ($)", value=defaults["size"], disabled=not is_custom, help="Total starting balance of the account.")
        max_dd = st.number_input("Max Drawdown ($)", value=defaults["max_dd"], disabled=not is_custom, help="The maximum loss allowed from the high-water mark (EOD Trailing) or starting balance.")
    with col2:
        profit_target = st.number_input("Profit Target ($)", value=defaults["target"], disabled=not is_custom, help="The dollar amount needed to pass the evaluation.")
        consistency_pct = st.number_input("Consistency %", value=defaults["consistency"], step=0.1, disabled=not is_custom, help="Rule: No single day's profit can exceed this % of the total Profit Target.\n\n(e.g., 50% of $3000 target = Max $1500/day).")
    with col3:
        limit_mini = st.number_input("Max Minis", value=defaults["max_minis"], disabled=not is_custom, help="Hard limit on how many Mini contracts (NQ, ES) you can hold at once.")
        limit_micro = st.number_input("Max Micros", value=defaults["max_micros"], disabled=not is_custom, help="Hard limit on how many Micro contracts (MNQ, MES) you can hold at once.")
        daily_loss = st.number_input("Daily Loss Limit ($)", value=defaults["daily_loss"], disabled=not is_custom, help="The maximum amount you are allowed to lose in a single trading day before the account is breached.")

# --- 2. RISK HEALTH BAR ---
# Logic: Calculate remaining budget
risk_budget = defaults["max_dd"] + current_pnl 
reason = "Max Drawdown"

if daily_loss > 0:
    daily_budget = daily_loss + current_pnl 
    if daily_budget < risk_budget:
        risk_budget = daily_budget
        reason = "Daily Loss Limit"

st.subheader("🛡️ Available Risk Budget")
if risk_budget <= 0:
    st.error(f"🚫 **TRADING HALTED:** You have hit your {reason}.")
    st.stop()
else:
    color = "green" if risk_budget > 1000 else "orange" if risk_budget > 500 else "red"
    st.markdown(f"""
    <div style="padding:15px; border-radius:10px; border: 1px solid #444; background-color: #262730;">
        <h3 style='margin:0; color:{color}'>${risk_budget:,.2f}</h3>
        <small style='color:#bbb'>Remaining buffer before hitting <b>{reason}</b>.</small>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# --- 3. CALCULATOR INPUTS ---
c1, c2, c3 = st.columns([1,1,2])
with c1:
    view_mode = st.radio(
        "View Mode:", 
        ["Comparison (Mini vs Micro)", "Single Instrument"],
        help="Select 'Comparison' to see NQ and MNQ side-by-side. Select 'Single' for a focused view."
    )
with c2:
    calc_mode = st.radio(
        "Calculation Mode:", 
        ["Risk Based ($)", "Manual Qty"],
        help="'Risk Based': You enter $ Risk, we calculate Quantity.\n'Manual Qty': You enter Quantity, we calculate $ Risk."
    )
with c3:
    if "Comparison" in view_mode:
        asset_group = st.selectbox("Asset Group:", ["Nasdaq (NQ & MNQ)", "S&P 500 (ES & MES)"])
        data = {"mini":"NQ", "micro":"MNQ", "mini_val":20, "micro_val":2} if "Nasdaq" in asset_group else {"mini":"ES", "micro":"MES", "mini_val":50, "micro_val":5}
    else:
        single_asset = st.selectbox("Instrument:", ["NQ", "MNQ", "ES", "MES"])
        map_ = {"NQ":20, "MNQ":2, "ES":50, "MES":5}
        type_ = "mini" if single_asset in ["NQ", "ES"] else "micro"
        data = {"name":single_asset, "val":map_[single_asset], "type":type_}

# Points Inputs with Tooltips
c_sl, c_tp = st.columns(2)
sl_pts = c_sl.number_input(
    "Stop Loss (Points):", 1.0, 500.0, 10.0, 0.5,
    help="The distance in points from your entry where you will exit the trade if it goes against you."
)
tp_pts = c_tp.number_input(
    "Take Profit (Points):", 1.0, 1000.0, 20.0, 0.5,
    help="The distance in points from your entry where you will exit the trade for a profit."
)

# --- ENGINE ---
def calculate_stats(qty, point_val, is_micro):
    if qty == 0: return None
    gross_risk = qty * sl_pts * point_val
    gross_reward = qty * tp_pts * point_val
    comm = (COMMISSIONS["micro"] if is_micro else COMMISSIONS["mini"]) * qty if use_commissions else 0
    return {
        "qty": qty, "net_risk": gross_risk + comm, 
        "net_reward": gross_reward - comm, "comm": comm, "gross": gross_reward
    }

# --- RENDER RESULTS ---
st.divider()

if "Comparison" in view_mode:
    # Auto-Calc Quantity logic
    if "Risk Based" in calc_mode:
        input_risk = st.number_input(
            "Max Risk allowed for this trade ($):", 
            50.0, float(risk_budget), min(500.0, float(risk_budget)), 10.0,
            help=f"How much are you willing to lose on this specific trade? (Max allowed: ${risk_budget})"
        )
        q_mini = min(math.floor(input_risk / (sl_pts * data["mini_val"])), defaults["max_minis"])
        q_micro = min(math.floor(input_risk / (sl_pts * data["micro_val"])), defaults["max_micros"])
    else:
        col_q1, col_q2 = st.columns(2)
        q_mini = col_q1.number_input(f"Qty {data['mini']}", 0, defaults["max_minis"], 1)
        q_micro = col_q2.number_input(f"Qty {data['micro']}", 0, defaults["max_micros"], 1)

    # Render Side-by-Side
    stats_mini = calculate_stats(q_mini, data["mini_val"], False)
    stats_micro = calculate_stats(q_micro, data["micro_val"], True)
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader(f"🦁 {data['mini']} (Mini)")
        if stats_mini:
            st.info(f"Size: **{stats_mini['qty']} Contracts**")
            st.metric("Net Risk", f"-${stats_mini['net_risk']:,.2f}")
            st.metric("Net Profit", f"+${stats_mini['net_reward']:,.2f}")
        else:
            st.warning("Stop Loss too wide (Risk > Limit).")
            
    with col_b:
        st.subheader(f"🐭 {data['micro']} (Micro)")
        if stats_micro:
            st.info(f"Size: **{stats_micro['qty']} Contracts**")
            st.metric("Net Risk", f"-${stats_micro['net_risk']:,.2f}")
            st.metric("Net Profit", f"+${stats_micro['net_reward']:,.2f}")
        else:
            st.warning("Stop Loss too wide.")

else:
    # Single View Logic
    limit = defaults["max_minis"] if data["type"] == "mini" else defaults["max_micros"]
    if "Risk Based" in calc_mode:
        input_risk = st.number_input(
            "Max Risk allowed for this trade ($):", 
            50.0, float(risk_budget), min(500.0, float(risk_budget)), 10.0,
            help=f"How much are you willing to lose? (Capped at budget: ${risk_budget})"
        )
        qty = min(math.floor(input_risk / (sl_pts * data["val"])), limit)
    else:
        qty = st.number_input("Quantity:", 1, limit, 1)

    stats = calculate_stats(qty, data["val"], data["type"] == "micro")
    if stats:
        st.subheader(f"📊 {data['name']} Trade Analysis")
        m1, m2, m3 = st.columns(3)
        m1.metric("Net Risk", f"-${stats['net_risk']:,.2f}")
        m2.metric("Net Profit", f"+${stats['net_reward']:,.2f}")
        m3.metric("R:R", f"1 : {tp_pts/sl_pts:.1f}")
        
        # Consistency Check
        if stage == "Evaluation" and defaults["consistency"] > 0:
            limit_val = defaults["target"] * defaults["consistency"]
            if stats["gross"] > limit_val:
                st.warning(f"⚠️ **Consistency Warning:** Profit (${stats['gross']:.0f}) exceeds daily limit (${limit_val:.0f}).")
            else:
                st.success(f"✅ Safe for consistency (Limit: ${limit_val:.0f})")
