import streamlit as st
from datetime import datetime
import pytz

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="ICT Execution Checklist",
    page_icon="🕯️",
    layout="centered"
)

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .big-font { font-size:20px !important; font-weight: bold; }
    .success-box { padding:10px; border-radius:5px; background-color:#d4edda; color:#155724; border: 1px solid #c3e6cb; }
    div.stButton > button:first-child { width: 100%; }
    </style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
def get_ny_time():
    ny_tz = pytz.timezone('US/Eastern')
    return datetime.now(ny_tz)

def is_killzone():
    ny_time = get_ny_time()
    # Define 9:30 AM to 11:00 AM
    start_time = ny_time.replace(hour=9, minute=30, second=0, microsecond=0)
    end_time = ny_time.replace(hour=11, minute=0, second=0, microsecond=0)
    return start_time <= ny_time <= end_time

def reset_callbacks():
    # This function clears the specific keys used in the checkboxes
    keys = ['p1_c1', 'p1_c2', 'p1_c3', 'p1_c4', 
            'p2_c1', 'p2_c2', 'p2_c3', 'p2_c4', 
            'p3_c1', 'p3_c2', 'p3_c3', 'p3_c4']
    for key in keys:
        st.session_state[key] = False

# --- SIDEBAR (CALCULATOR LINK) ---
with st.sidebar:
    st.header("🧮 Position Tools")
    st.write("Want to calculate your position size?")
    st.link_button("Go to NQ Calculator", "https://nqchecklist.streamlit.app/")
    st.info("Ensure you calculate risk before entering Phase 3.")

# --- HEADER & TIME DISPLAY ---
st.title("🕯️ ICT Trading Plan Checklist")

ny_now = get_ny_time()
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown(f"**Current NY Time:** `{ny_now.strftime('%H:%M:%S')}`")
    
with col2:
    if is_killzone():
        st.success("✅ Inside Killzone")
    else:
        st.warning("⚠️ Outside Killzone")

st.markdown("---")

# --- PHASE 1: THE STORY ---
st.header("Phase 1: The Story (15m & 5m)")
st.info("Before looking at the 1m chart, the 'Big Picture' must be clear.")

# Note: Added 'key' argument to every checkbox to enable the Reset functionality
p1_c1 = st.checkbox("Identify DOL: Where is the 'Robot' trying to go? (Old High/Low, Equal Highs, FVG)", key='p1_c1')
p1_c2 = st.checkbox("Current Bias: Is 15m structure making HH/HL (Bullish) or LH/LL (Bearish)?", key='p1_c2')
p1_c3 = st.checkbox("Premium/Discount: Is price 'Cheap' (Long) or 'Expensive' (Short)?", key='p1_c3')
p1_c4 = st.checkbox("HTF Liquidity Sweep: Has price taken out a 5m/15m swing? (Green Light)", key='p1_c4')

phase1_complete = all([p1_c1, p1_c2, p1_c3, p1_c4])

if phase1_complete:
    st.success("Story is clear. Proceed to Trigger.")
else:
    st.stop() 

st.markdown("---")

# --- PHASE 2: THE TRIGGER ---
st.header("Phase 2: The Trigger (1m)")
st.info("Once the 15m is pointing the way, zoom into the 1m to find the entry.")

p2_c1 = st.checkbox("Wait for Displacement: High-energy candle, large body, small wicks.", key='p2_c1')
p2_c2 = st.checkbox("Identify IFVG: Aggressive close through a previous FVG?", key='p2_c2')
p2_c3 = st.checkbox("Market Structure Shift (MSS): Break of 1m swing point with energy?", key='p2_c3')
p2_c4 = st.checkbox("FVG Gap Cluster Check: Entering at first FVG (High Energy) or waiting for FVG cluster inversion (Low Energy)?", key='p2_c4')

phase2_complete = all([p2_c1, p2_c2, p2_c3, p2_c4])

if phase2_complete:
    st.success("Trigger validated. Proceed to Risk Management.")
else:
    st.warning("Waiting for entry setup...")
    st.stop()

st.markdown("---")

# --- PHASE 3: THE BUSINESS ---
st.header("Phase 3: The Business (Risk Mgmt)")
st.info("Don't click 'Buy' or 'Sell' until the math makes sense.")

p3_c1 = st.checkbox("Stop Loss Placement: Is my SL at a safe swing point?", key='p3_c1')
p3_c2 = st.checkbox("RR Check: At least 1:1 before first major obstacle?", key='p3_c2')
p3_c3 = st.checkbox("$400 Rule: If this hits 1R, is profit >= $400? (Prepare to bank).", key='p3_c3')
p3_c4 = st.checkbox("Time Check: Is this inside 9:30 AM – 11:00 AM NY Time?", key='p3_c4')

phase3_complete = all([p3_c1, p3_c2, p3_c3, p3_c4])

st.markdown("---")

# --- FINAL DECISION DASHBOARD ---
st.subheader("🏁 Trade Decision")

if phase3_complete:
    st.markdown("""
        <div style="background-color: #28a745; color: white; padding: 20px; border-radius: 10px; text-align: center;">
            <h1>EXECUTE TRADE</h1>
            <p>All systems go. Stick to the plan.</p>
        </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <div style="background-color: #dc3545; color: white; padding: 20px; border-radius: 10px; text-align: center;">
            <h1>NO TRADE</h1>
            <p>Risk parameters or time check not met.</p>
        </div>
    """, unsafe_allow_html=True)

# --- RESET BUTTON ---
# Uses the callback function to clear state before rerunning
st.button("Reset Checklist", on_click=reset_callbacks)
