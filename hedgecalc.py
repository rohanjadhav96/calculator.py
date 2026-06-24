import streamlit as st
import pandas as pd

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(page_title="Hedge Sizing Dashboard", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# Custom CSS for metrics to keep them looking sharp
st.markdown("""
    <style>
    .stMetric { background-color: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ Delta Hedge Execution Engine")
st.markdown("Automated position sizing and risk management for Prop vs. CEX strategies.")

# ==========================================
# SIDEBAR: ACCOUNT STATUS & RISK
# ==========================================
with st.sidebar:
    st.header("💼 Account Balances & Risk")
    
    with st.container(border=True):
        account_tier = st.selectbox("Prop Account Tier", ["50k Account", "10k Account"])
        prop_balance = st.number_input("Prop Balance ($)", value=50000.0 if "50k" in account_tier else 10000.0, step=10.0)
        bitunix_balance = st.number_input("Bitunix Wallet ($)", value=2484.0, step=10.0)

    # Calculate Tier Constants
    baseline = 50000.0 if "50k" in account_tier else 10000.0
    default_risk = 1750.0 if "50k" in account_tier else 350.0
    
    st.markdown("### 🎲 Risk Parameters")
    prop_risk_chunk = st.number_input("Prop Risk Per Trade ($)", value=default_risk, step=50.0)
    
    is_in_dead_zone = prop_balance < baseline
    dead_zone_amt = max(0.0, baseline - prop_balance)
    
    st.divider()
    st.subheader("📊 Status")
    if is_in_dead_zone:
        st.error(f"**Dead Zone Active:** ${dead_zone_amt:,.2f} below baseline.")
        st.caption("Focus on Drain or 1:3 Payout strategies to clear this gap safely.")
    else:
        st.success("**Funded & Flat!** 100% of profits are payout eligible.")
        st.caption("You are cleared to use Aggressive 1:1 (0.90x) or High Win-Rate Payouts.")

# ==========================================
# MAIN UI: TRADE SETUP & STRATEGY
# ==========================================
col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        st.subheader("🎯 1. Trade Setup")
        trade_direction = st.radio("Bitunix (CEX) Direction", ["Long 🟢", "Short 🔴"], horizontal=True)
        is_long = "Long" in trade_direction
        
        inner_c1, inner_c2 = st.columns(2)
        with inner_c1:
            cmp = st.number_input("Entry Price (CMP)", value=62.15, format="%.4f")
        with inner_c2:
            default_sl = (cmp - 2.0) if is_long else (cmp + 2.0)
            sl_price = st.number_input("Bitunix Stop Loss (SL)", value=default_sl, format="%.4f")
            
        # price_delta always represents the distance to the CEX Stop Loss
        price_delta = abs(cmp - sl_price)

with col2:
    with st.container(border=True):
        st.subheader("🧠 2. Strategy Engine")
        
        # Smart defaulting based on dead zone
        strategy_options = [
            "High Win-Rate Payout (Asymmetric 3:1)",
            "Drain / Payout Focus (1:3 RR)", 
            "Aggressive Cash Drain (1:1 RR, 0.9x Ratio)", 
            "Perfect Breakeven"
        ]
        
        strategy_idx = 0 if not is_in_dead_zone else 1
        selected_strategy = st.selectbox("Select Hedge Algorithm", strategy_options, index=strategy_idx)
        
        # Dynamic UI elements based on selected strategy
        if "High Win-Rate" in selected_strategy:
            st.success("💡 **Active:** Risking 3 to make 1 on Prop. Generates frequent small payouts while laying a trap for a massive Bitunix win if the Prop blows.")
            target_net_profit = st.slider("Target Net Profit if Prop Wins ($)", min_value=50, max_value=200, value=100, step=10)
            st.caption("🎯 **Strategic Tip:** Aim for $100. If the Prop account hits SL, you will pocket a massive Bitunix win. Switch to 'Drain Mode' afterwards to extract the remaining balance.")
        elif "Drain" in selected_strategy:
            st.info("💡 **Active:** Risking 1 to make 3 on Prop. Perfect for blasting past the dead zone and forcing a payout.")
        elif "Aggressive" in selected_strategy:
            st.info("💡 **Active:** 1:1 Risk/Reward with a 0.90 ratio. Use ONLY when account is flat at baseline.")
        else:
            st.info("💡 **Active:** Matches Prop TP perfectly to CEX SL + Payout splits.")

# ==========================================
# MATH ENGINE (Hidden from UI)
# ==========================================
if price_delta <= 0:
    st.error("Stop loss must be different from entry price.")
    st.stop()

# --- Unified Math Logic ---
# CEX SL hit == Prop TP hit. Therefore, Prop TP distance always equals price_delta.

# Strategy 1: High Win-Rate Payout (Asymmetric 3:1)
if "High Win-Rate" in selected_strategy:
    prop_sl_dollar = prop_risk_chunk
    prop_tp_dollar = prop_risk_chunk / 3.0
    
    gross_payout = prop_tp_dollar - dead_zone_amt
    net_payout = max(0.0, gross_payout * 0.90)
    
    cex_sl_dollar = max(0.0, net_payout - target_net_profit)
    cex_tp_dollar = cex_sl_dollar * 3.0 
    
    prop_qty = prop_tp_dollar / price_delta
    cex_qty = cex_sl_dollar / price_delta

# Strategy 2: Drain / Payout Focus (1:3 RR)
elif "Drain" in selected_strategy:
    prop_sl_dollar = prop_risk_chunk
    prop_tp_dollar = prop_risk_chunk * 3.0
    
    # Pre-calculated safety ratios to ensure Bitunix wallet is safe while clearing dead zones
    cex_sl_dollar = prop_risk_chunk * 1.74 
    cex_tp_dollar = prop_risk_chunk * 0.58 
    
    prop_qty = prop_tp_dollar / price_delta
    cex_qty = cex_sl_dollar / price_delta

# Strategy 3: Aggressive Cash Drain (1:1)
elif "Aggressive" in selected_strategy:
    prop_sl_dollar = prop_risk_chunk
    prop_tp_dollar = prop_risk_chunk
    
    cex_sl_dollar = prop_risk_chunk * 0.90
    cex_tp_dollar = prop_risk_chunk * 0.90
    
    prop_qty = prop_tp_dollar / price_delta
    cex_qty = cex_sl_dollar / price_delta

# Strategy 4: Perfect Breakeven
else:
    hedge_ratio = 0.73 if is_in_dead_zone else 0.90
    rr_ratio = 1.37 if is_in_dead_zone else 1.0
    
    prop_sl_dollar = prop_risk_chunk
    prop_tp_dollar = prop_risk_chunk * rr_ratio
    
    prop_qty = prop_tp_dollar / price_delta
    cex_qty = prop_qty * hedge_ratio
    
    cex_sl_dollar = cex_qty * price_delta
    cex_tp_dollar = cex_qty * (price_delta / rr_ratio)

# ==========================================
# UNIVERSAL TARGET PRICE CALCULATOR
# ==========================================
cex_tp_distance = cex_tp_dollar / cex_qty
prop_sl_distance = prop_sl_dollar / prop_qty

if is_long:
    # Bitunix Long (CEX TP above, CEX SL below) / Prop Short (Prop SL above, Prop TP below)
    cex_sl_price = sl_price
    cex_tp_price = cmp + cex_tp_distance
    prop_tp_price = sl_price
    prop_sl_price = cmp + prop_sl_distance
else:
    # Bitunix Short (CEX TP below, CEX SL above) / Prop Long (Prop SL below, Prop TP above)
    cex_sl_price = sl_price
    cex_tp_price = cmp - cex_tp_distance
    prop_tp_price = sl_price
    prop_sl_price = cmp - prop_sl_distance

# ==========================================
# MAIN UI: EXECUTION PARAMETERS
# ==========================================
st.subheader("📋 3. Exact Execution Blueprints")

ex_col1, ex_col2 = st.columns(2)

with ex_col1:
    prop_direction = "SHORT 🔴" if is_long else "LONG 🟢"
    with st.container(border=True):
        st.markdown(f"### 🏦 Breakout Prop ({prop_direction})")
        st.metric("Position Size (Qty)", f"{prop_qty:,.2f}")
        st.markdown(f"**Entry:** `{cmp:,.4f}`")
        st.markdown(f"**Take Profit:** `{prop_tp_price:,.4f}`  *(+${prop_tp_dollar:,.2f})*")
        st.markdown(f"**Stop Loss:** `{prop_sl_price:,.4f}`  *(-${prop_sl_dollar:,.2f})*")

with ex_col2:
    cex_direction = "LONG 🟢" if is_long else "SHORT 🔴"
    with st.container(border=True):
        st.markdown(f"### 💱 Bitunix CEX ({cex_direction})")
        st.metric("Position Size (Qty)", f"{cex_qty:,.2f}")
        st.markdown(f"**Entry:** `{cmp:,.4f}`")
        st.markdown(f"**Take Profit:** `{cex_tp_price:,.4f}`  *(+${cex_tp_dollar:,.2f})*")
        st.markdown(f"**Stop Loss:** `{cex_sl_price:,.4f}`  *(-${cex_sl_dollar:,.2f})*")

# ==========================================
# MAIN UI: LIQUIDATION & OUTCOMES
# ==========================================
st.divider()

# Liquidation Safety Check
if bitunix_balance < cex_sl_dollar:
    st.error(f"🚨 **LIQUIDATION RISK:** Wallet balance (${bitunix_balance:,.2f}) cannot cover the CEX stop loss (${cex_sl_dollar:,.2f}). **DO NOT EXECUTE.** Deposit funds or reduce risk.")
elif bitunix_balance < (cex_sl_dollar * 1.15):
    st.warning(f"⚠️ **MARGIN WARNING:** Wallet balance is dangerously close to max loss. Allocate at least ${cex_sl_dollar * 1.10:,.2f} on Isolated Margin to avoid early engine liquidation.")
else:
    st.success(f"🛡️ **Wallet Safe:** Bitunix balance (${bitunix_balance:,.2f}) easily absorbs maximum structural risk (${cex_sl_dollar:,.2f}).")

st.subheader("🔮 4. Projected Outcomes")

tab1, tab2 = st.tabs(["Outcome A: The Market Reverses (Prop Blows/Bleeds)", "Outcome B: The Setup Wins (Prop Payout)"])

with tab1:
    st.markdown("### If Market Hits Your CEX Take Profit")
    st.markdown(f"- **Bitunix Wallet:** Pocket **+${cex_tp_dollar:,.2f}** in clean crypto cash.")
    st.markdown(f"- **Prop Account:** Takes a controlled ${prop_sl_dollar:,.2f} loss. Balance drops to `${prop_balance - prop_sl_dollar:,.2f}`.")
    
    if "High Win-Rate" in selected_strategy:
        st.markdown("- **Next Step:** 🚀 **MASSIVE WIN.** Switch your algorithm to 'Drain / Payout Focus' to clean out the remaining wounded balance.")
    else:
        st.markdown("- **Next Step:** Queue up the exact same trade size again.")

with tab2:
    st.markdown("### If Market Hits Your Prop Take Profit")
    if is_in_dead_zone:
        gross_payout_gain = prop_tp_dollar - dead_zone_amt
        net_payout = max(0.0, gross_payout_gain * 0.90)
        net_trade_profit = net_payout - cex_sl_dollar
        
        st.markdown(f"- **Prop Account:** Gains +${prop_tp_dollar:,.2f}, clearing the dead zone.")
        if net_payout > 0:
            st.markdown(f"- **Payout:** You trigger a payout of **${net_payout:,.2f}**.")
        else:
            st.markdown(f"- **Payout:** Still in dead zone. No payout triggered yet.")
            
        st.markdown(f"- **Bitunix Wallet:** Absorbs the **-${cex_sl_dollar:,.2f}** stop loss.")
        st.markdown(f"- **Net Result:** Prop account is recovering/reset. You net **${net_trade_profit:+.2f}** overall.")
    else:
        net_payout = prop_tp_dollar * 0.90
        net_trade_profit = net_payout - cex_sl_dollar
        
        st.markdown(f"- **Prop Account:** Gains +${prop_tp_dollar:,.2f}.")
        st.markdown(f"- **Payout:** You trigger a payout of **${net_payout:,.2f}**.")
        st.markdown(f"- **Bitunix Wallet:** Absorbs the **-${cex_sl_dollar:,.2f}** stop loss.")
        st.markdown(f"- **Net Result:** You net **${net_trade_profit:+.2f}** overall.")
