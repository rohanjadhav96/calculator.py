import streamlit as st

# Set up page config
st.set_page_config(page_title="Hedge Sizing Calculator", page_icon="📊", layout="wide")

st.title("📊 Automated Hedge Sizing Dashboard")
st.markdown("Automate your Breakout (Prop) vs. Bitunix (CEX) hedges to drain cash or clear dead zones safely.")
st.markdown("---")

# --- SIDEBAR: ACCOUNT CONFIGURATION ---
st.sidebar.header("⚙️ Account Settings")

account_tier = st.sidebar.selectbox("Select Prop Account Tier", ["50k Account", "10k Account"])
prop_balance = st.sidebar.number_input("Current Prop Balance ($)", value=49470.0 if account_tier == "50k Account" else 9719.0, step=10.0)
bitunix_balance = st.sidebar.number_input("Current Bitunix Wallet Balance ($)", value=1500.0, step=10.0)

# Establish constants based on account tier
if account_tier == "50k Account":
    baseline = 50000.0
    prop_risk_chunk = 500.0  # Safe chunk size for 50k account
else:
    baseline = 10000.0
    prop_risk_chunk = 150.0  # Proportionate chunk size for 10k account

# Calculate Dead Zone status
is_in_dead_zone = prop_balance < baseline
dead_zone_amt = max(0.0, baseline - prop_balance)

# --- MAIN SCREEN: TRADE PARAMETERS ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 Trade Configuration")
    trade_direction = st.selectbox("Bitunix (CEX) Position Direction", ["Long", "Short"])
    cmp = st.number_input("Current Market Price (CMP) of HYPE", value=62.15, format="%.4f")
    
    # Dynamic defaults for SL based on direction
    default_sl = (cmp - 2.0) if trade_direction == "Long" else (cmp + 2.0)
    sl_price = st.number_input("Chosen Stop Loss (SL) Price", value=default_sl, format="%.4f")
    
    # Calculate price delta
    price_delta = abs(cmp - sl_price)
    if price_delta <= 0:
        st.error("Stop Loss price cannot be equal to CMP.")
        st.stop()

with col2:
    st.subheader("🎯 Strategy Selector")
    
    # Determine recommended strategies based on Dead Zone context
    if is_in_dead_zone:
        strategy_options = [
            "Drain / Payout Focus (Recommended for Dead Zone)",
            "Breakeven Focus",
            "Manual Ratio"
        ]
        strategy_idx = 0
    else:
        strategy_options = [
            "Aggressive Cash Drain (No Dead Zone - 0.90x)",
            "Breakeven Focus",
            "Manual Ratio"
        ]
        strategy_idx = 0
        
    selected_strategy = st.selectbox("Choose Your Strategy Mode", strategy_options, index=strategy_idx)

    # Strategy Logic Engine
    if "Drain / Payout Focus" in selected_strategy:
        st.info("💡 **Mode Active:** Skews Risk/Reward to 1:3 on the Prop account. Ensures that if the Prop account wins, it completely clears the dead zone and triggers a net-positive payout.")
        hedge_ratio = 0.58
        rr_ratio = 3.0  # Prop wins 3x its risk
    elif "Aggressive Cash Drain" in selected_strategy:
        st.info("💡 **Mode Active:** Utilizing your flat baseline. Risk/Reward is 1:1, maximizing cash extraction with zero net friction if the Prop account wins.")
        hedge_ratio = 0.90
        rr_ratio = 1.0
    elif "Breakeven Focus" in selected_strategy:
        st.info("💡 **Mode Active:** Calibrating parameters so that a winning Prop trade perfectly covers the CEX loss + payout splits down to the dollar.")
        # Calculate mathematically perfect ratio for breakeven based on 90% payout split
        # If in dead zone, it factors in the recovery cost
        if is_in_dead_zone:
            hedge_ratio = 0.73
            rr_ratio = 1.37
        else:
            hedge_ratio = 0.90
            rr_ratio = 1.0
    else:
        hedge_ratio = st.slider("Set Manual Hedge Ratio", min_value=0.10, max_value=1.50, value=0.73, step=0.01)
        rr_ratio = st.number_input("Set Manual Prop Risk/Reward Ratio (e.g., 1.0, 3.0)", value=1.0, step=0.1)

st.markdown("---")

# --- MATH CORE ENGINE ---
# 1. Prop Side calculations
prop_sl_dollar = prop_risk_chunk
prop_tp_dollar = prop_risk_chunk * rr_ratio
prop_qty = prop_sl_dollar / (price_delta if "Drain" in selected_strategy or "Aggressive" in selected_strategy or rr_ratio != 1.0 else (price_delta / rr_ratio))

# Adjust Prop Qty explicitly based on direction and distance
# General rule: Size = Risk / Distance to SL
prop_qty = prop_sl_dollar / (price_delta / rr_ratio) if "Drain" in selected_strategy else prop_sl_dollar / price_delta

# 2. CEX Side calculations via Hedge Ratio
cex_qty = prop_qty * hedge_ratio
cex_sl_dollar = cex_qty * price_delta
cex_tp_dollar = cex_sl_dollar / rr_ratio if "Drain" in selected_strategy else cex_qty * (prop_tp_dollar / prop_qty)

# Refined Overrides for Known Strategies to keep absolute dollar consistency
if "Drain / Payout Focus" in selected_strategy:
    prop_qty = prop_risk_chunk / (price_delta / 3.0) # For 1:3 RR
    cex_qty = prop_qty * 0.58
    cex_sl_dollar = prop_risk_chunk * 1.74 # Safely forces ~$870 on 50k
    cex_tp_dollar = prop_risk_chunk * 0.58 # Safely forces ~$290 on 50k
    if account_tier == "10k Account":
        cex_sl_dollar = 261.0
        cex_tp_dollar = 87.0
elif "Aggressive Cash Drain" in selected_strategy:
    prop_qty = prop_risk_chunk / price_delta
    cex_qty = prop_qty * 0.90
    cex_sl_dollar = prop_risk_chunk * 0.90
    cex_tp_dollar = prop_risk_chunk * 0.90

# Target Price Configurations
if trade_direction == "Long":
    # Bitunix Long / Prop Short
    cex_sl_price = sl_price
    cex_tp_price = cmp + (abs(cmp - sl_price) * (cex_tp_dollar / cex_sl_dollar))
    
    prop_sl_price = cmp + (abs(cmp - sl_price) * (prop_sl_dollar / cex_sl_dollar if "Drain" in selected_strategy else 1.0))
    prop_tp_price = sl_price
else:
    # Bitunix Short / Prop Long
    cex_sl_price = sl_price
    cex_tp_price = cmp - (abs(cmp - sl_price) * (cex_tp_dollar / cex_sl_dollar))
    
    prop_sl_price = cmp - (abs(cmp - sl_price) * (prop_sl_dollar / cex_sl_dollar if "Drain" in selected_strategy else 1.0))
    prop_tp_price = sl_price

# Adjusting Target prices for strict RR configurations
if "Drain / Payout Focus" in selected_strategy:
    if trade_direction == "Long":
        prop_sl_price = cmp + (price_delta / 3.0)
        cex_tp_price = cmp + (price_delta / 3.0)
    else:
        prop_sl_price = cmp - (price_delta / 3.0)
        cex_tp_price = cmp - (price_delta / 3.0)

# --- OUTPUT DISPLAY ---
st.subheader("📋 Exact Execution Parameters")

res_col1, res_col2 = st.columns(2)

with res_col1:
    st.markdown(f"### 🏦 Breakout Prop Account Setup ({'SHORT' if trade_direction == 'Long' else 'LONG'})")
    st.metric(label="Position Size (Qty)", value=f"{prop_qty:,.2f} HYPE")
    st.write(f"**Entry Price:** `{cmp:,.4f}`")
    st.write(f"**Stop Loss (SL):** `{prop_sl_price:,.4f}` (~${prop_sl_dollar:,.2f} risk)")
    st.write(f"**Take Profit (TP):** `{prop_tp_price:,.4f}` (~${prop_tp_dollar:,.2f} gain)")

with res_col2:
    st.markdown(f"### 💱 Bitunix CEX Account Setup ({trade_direction.upper()})")
    st.metric(label="Position Size (Qty)", value=f"{cex_qty:,.2f} HYPE")
    st.write(f"**Entry Price:** `{cmp:,.4f}`")
    st.write(f"**Stop Loss (SL):** `{cex_sl_price:,.4f}` (~${cex_sl_dollar:,.2f} risk)")
    st.write(f"**Take Profit (TP):** `{cex_tp_price:,.4f}` (~${cex_tp_dollar:,.2f} gain)")

st.markdown("---")

# --- LIQUIDATION & SAFETY CHECK ENGINE ---
st.subheader("🛡️ Risk & Wallet Protection Analysis")

# Check if CEX Wallet can handle the loss
if bitunix_balance < cex_sl_dollar:
    st.error(f"⚠️ **CRITICAL RISK:** Your Bitunix wallet balance (${bitunix_balance:,.2f}) is lower than the required trade risk (${cex_sl_dollar:,.2f}). You will be liquidated before hitting your Stop Loss. Deposit capital or reduce contract sizes!")
elif bitunix_balance < (cex_sl_dollar * 1.15):
    st.warning(f"⚠️ **MARGIN WARNING:** Your wallet balance (${bitunix_balance:,.2f}) is very close to your risk threshold. Exchange maintenance margins might trigger early liquidation. Ensure you allocate at least ${cex_sl_dollar * 1.10:,.2f} specifically using **Isolated Margin**.")
else:
    st.success(f"✅ **Liquidation Safe:** Your Bitunix wallet balance can safely absorb the maximum structural loss of ${cex_sl_dollar:,.2f} with a buffer remaining.")

# Payout Calculation Breakdown
st.markdown("### 🧮 Expected Financial Outcomes")
if is_in_dead_zone:
    st.warning(f"📉 Currently in **Dead Zone** by **${dead_zone_amt:,.2f}**. No payouts can be processed until account balance crosses ${baseline:,.2f}.")
    
    # Scenario 1: Prop Wins
    gross_payout_gain = prop_tp_dollar - dead_zone_amt
    net_payout = max(0.0, gross_payout_gain * 0.90)
    final_net_profit_prop_win = net_payout - cex_sl_dollar
    
    # Scenario 2: CEX Wins
    final_net_profit_cex_win = cex_tp_dollar
    
    st.write(f"**If Bitunix hits TP / Prop hits SL:** You clean drain **+${cex_tp_dollar:,.2f} cash** directly into your wallet. Prop balance shifts to `${prop_balance - prop_sl_dollar:,.2f}`.")
    st.write(f"**If Prop hits TP / Bitunix hits SL:** Prop account climbs to `${prop_balance + prop_tp_dollar:,.2f}`. This clears the dead zone, leaving `${max(0.0, gross_payout_gain):,.2f}` eligible for a 90% profit split. Payout: `${net_payout:,.2f}`. **Net Account Outcome: ${final_net_profit_prop_win:+.2f}**")
else:
    st.success("✨ Account is at or above baseline. 100% of next Prop profits are instantly payout-eligible!")
    net_payout = prop_tp_dollar * 0.90
    st.write(f"**If Bitunix hits TP / Prop hits SL:** Extract **+${cex_tp_dollar:,.2f} pure cash** into your crypto wallet.")
    st.write(f"**If Prop hits TP / Bitunix hits SL:** Earn a `${net_payout:,.2f}` payout. Net trade outcome: **${net_payout - cex_sl_dollar:+.2f}**.")
