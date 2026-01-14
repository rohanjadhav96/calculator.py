import streamlit as st
import numpy as np
import pandas as pd

# --- PAGE CONFIG ---
st.set_page_config(page_title="Prop Equity Simulator", page_icon="🔮", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .big-metric { font-size: 24px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- PRESETS (Using your specific firm rules) ---
PRESETS = {
    "Lucid Flex 50k": {
        "size": 50000, "target": 3000, 
        "max_dd": 2000, "trailing": True
    },
    "Tradeify Select 50k": {
        "size": 50000, "target": 2500, 
        "max_dd": 2000, "trailing": True
    },
    "Standard Static 50k": {
        "size": 50000, "target": 3000, 
        "max_dd": 2500, "trailing": False
    },
    "🛠️ Custom": {
        "size": 50000, "target": 3000, 
        "max_dd": 2000, "trailing": True
    }
}

# --- SIDEBAR: ACCOUNT SETTINGS ---
with st.sidebar:
    st.header("⚙️ Account Rules")
    selected_preset = st.selectbox("Select Prop Firm:", list(PRESETS.keys()))
    defaults = PRESETS[selected_preset]
    is_custom = (selected_preset == "🛠️ Custom")

    acc_size = st.number_input("Account Size ($)", value=defaults["size"], disabled=not is_custom)
    profit_target_amt = st.number_input("Profit Target ($)", value=defaults["target"], disabled=not is_custom)
    max_dd = st.number_input("Max Drawdown ($)", value=defaults["max_dd"], disabled=not is_custom)
    is_trailing = st.checkbox("Trailing Drawdown?", value=defaults["trailing"], disabled=not is_custom)
    
    st.info(f"**Goal:** Reach ${acc_size + profit_target_amt:,.0f}\n\n**Fail:** Hit Drawdown limit.")

# --- MAIN PAGE: STRATEGY INPUTS ---
st.title("🔮 Prop Firm Equity Simulator")
st.markdown("Test your strategy math against the firm's drawdown rules.")

col1, col2, col3, col4 = st.columns(4)

with col1:
    win_rate = st.slider("Win Rate (%)", 10, 90, 45)
with col2:
    risk_per_trade = st.number_input("Risk Per Trade ($)", value=250, step=10)
with col3:
    reward_per_trade = st.number_input("Reward Per Trade ($)", value=500, step=10)
with col4:
    total_trades = st.number_input("Simulate N Trades", value=50, step=10)

# Calculate implied RR
rr = reward_per_trade / risk_per_trade if risk_per_trade > 0 else 0
st.caption(f"**Implied R:R:** 1:{rr:.2f} | **Breakeven Win Rate:** {100/(1+rr):.1f}%")

st.divider()

# --- SIMULATION LOGIC ---
if st.button("🚀 Run Monte Carlo Simulation (100 Iterations)", type="primary"):
    
    n_sims = 100
    results = [] # To store final status
    all_curves = [] # To store data for the chart

    progress_bar = st.progress(0)

    for i in range(n_sims):
        balance = acc_size
        high_water_mark = acc_size
        curve = [balance]
        status = "Survived" # Default if neither passed nor failed
        
        # Calculate Target Level
        pass_level = acc_size + profit_target_amt

        for _ in range(total_trades):
            # 1. Trade Result
            if np.random.rand() < (win_rate / 100):
                balance += reward_per_trade
            else:
                balance -= risk_per_trade
            
            # 2. Update High Water Mark
            if balance > high_water_mark:
                high_water_mark = balance
            
            # 3. Define the Floor (Drawdown Limit)
            if is_trailing:
                # Floor moves up with HWM
                drawdown_floor = high_water_mark - max_dd
            else:
                # Floor is static based on initial balance
                drawdown_floor = acc_size - max_dd

            curve.append(balance)

            # 4. Check Pass/Fail
            if balance >= pass_level:
                status = "Passed"
                break
            if balance <= drawdown_floor:
                status = "Failed"
                break
        
        # Pad curve for chart consistency
        while len(curve) <= total_trades:
            curve.append(curve[-1])
            
        all_curves.append(curve)
        results.append(status)
        
        # Update progress bar
        if (i + 1) % 10 == 0:
            progress_bar.progress((i + 1) / n_sims)
    
    progress_bar.empty()

    # --- PROCESS RESULTS ---
    pass_count = results.count("Passed")
    fail_count = results.count("Failed")
    survive_count = results.count("Survived")

    # --- DISPLAY METRICS ---
    m1, m2, m3 = st.columns(3)
    
    with m1:
        st.metric("🏆 Pass Probability", f"{pass_count}%", help="Reached profit target before hitting drawdown.")
        if pass_count > 60:
            st.success("Strategy is viable.")
    
    with m2:
        st.metric("☠️ Ruin Probability", f"{fail_count}%", help="Blew the account due to drawdown.", delta_color="inverse")
        if fail_count > 30:
            st.error("Risk is too high!")
            
    with m3:
        st.metric("🐢 Stagnation", f"{survive_count}%", help="Neither passed nor failed after N trades.")

    # --- CHART VISUALIZATION ---
    chart_data = pd.DataFrame(all_curves).T
    
    # Add Reference Lines for Visual Clarity (Start, Target, Static DD)
    # Note: Trailing DD is dynamic per line, so we can't plot a single static red line easily, 
    # but we can plot the static Target line.
    
    st.subheader("Equity Curves")
    st.line_chart(chart_data, use_container_width=True)
    
    # --- ANALYSIS TEXT ---
    st.markdown("### 📝 Analysis")
    if fail_count > 50:
        st.warning(f"**Critical Warning:** Your current setup fails {fail_count}% of the time. This is usually due to the 'Trailing Drawdown' rule. Even if your strategy makes money in the long run, the drawdown kills you during normal losing streaks. **Try reducing your Risk Per Trade.**")
    elif pass_count > 70:
        st.success("**Green Light:** This strategy has a very high probability of passing the evaluation.")
    else:
        st.info("**Borderline:** The results are mixed. You are dependent on 'Luck' regarding when your winning or losing streaks happen.")
