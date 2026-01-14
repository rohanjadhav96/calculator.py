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
    a { text-decoration: none; font-weight: bold; }
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
    # Clears all checkboxes
    keys = ['p1_c1', 'p1_c2', 'p1_c3', 'p1_c4', 
            'p2_c1', 'p2_c2', 'p2_c3', 'p2_c4', 
            'p3_c1', 'p3_c2', 'p3_c3', 'p3_c4']
    for key in keys:
        if key in st.session_state:
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

# --- PHASE 1: THE NARRATIVE ---
st.header("Phase 1: The Narrative (15m & 5m)")
st.info("This phase is about finding the 'Magnet' that pulls the price.")

p1_c1 = st.checkbox("Identify 15m DOL: Where is the most obvious 'pile of money'? (Old High/Low, Equal Highs)", key='p1_c1')
p1_c2 = st.checkbox("Confirm 15m Trend: Is price clearly 'stepping' higher or lower on the 15m?", key='p1_c2')
p1_c3 = st.checkbox("Liquidity Sweep: Has price taken out a recent 5m or 15m swing to 'activate' the algo?", key='p1_c3')
p1_c4 = st.checkbox("Time Check: Am I looking at the chart during 9:30 AM – 11:00 AM NY?", key='p1_c4')

phase1_complete = all([p1_c1, p1_c2, p1_c3, p1_c4])

if phase1_complete:
    st.success("Narrative is clear. Proceed to Execution.")
else:
    st.stop() 

st.markdown("---")

# --- PHASE 2: THE EXECUTION ---
st.header("Phase 2: The Execution (1m)")
st.info("This is where you look for the 'Robot' to switch directions.")

p2_c1 = st.checkbox("Displacement Check: Did price move away from sweep with big, fast candles (High Energy)?", key='p2_c1')
p2_c2 = st.checkbox("Market Structure Shift (MSS): Did price break the last 1m swing point that led to sweep?", key='p2_c2')
p2_c3 = st.checkbox("Identify IFVG: Did price aggressively close through a previous Fair Value Gap?", key='p2_c3')
p2_c4 = st.checkbox("The Entry: Did a 1m candle close above/below the IFVG? (Your entry trigger).", key='p2_c4')

phase2_complete = all([p2_c1, p2_c2, p2_c3, p2_c4])

if phase2_complete:
    st.success("Setup valid. Calculate risk.")
else:
    st.warning("Waiting for entry setup...")
    st.stop()

st.markdown("---")

# --- PHASE 3: THE BUSINESS ---
st.header("Phase 3: The Business (Risk & Mgmt)")
st.info("The mechanical rules for your prop firm funded accounts.")

p3_c1 = st.checkbox("Stop Loss Placement: Is SL safe at the recent 1m swing point (peak of sweep)?", key='p3_c1')
p3_c2 = st.checkbox("RR Check: At least 1:1 RR before the next major 1m obstacle?", key='p3_c2')
p3_c3 = st.checkbox("The '$400 Rule': If this hits 1R, is profit $400+? (If yes, be ready to book).", key='p3_c3')
p3_c4 = st.checkbox("'Bank the 1R' Plan: If it slows at 1R, am I prepared to exit and 'pay the trader'?", key='p3_c4')

phase3_complete = all([p3_c1, p3_c2, p3_c3, p3_c4])

st.markdown("---")

# --- FINAL DECISION & JOURNALING ---
st.subheader("🏁 Trade Decision")

if phase3_complete:
    st.markdown("""
        <div style="background-color: #28a745; color: white; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px;">
            <h1>EXECUTE TRADE</h1>
            <p>All systems go. Stick to the plan.</p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("### 📝 Post-Trade Outcome")
    st.write("Once the trade is closed, select the outcome:")
    
    col_win, col_loss = st.columns(2)
    
    journal_url = "https://wide-kayak-822.notion.site/Backtesting-2e7a40276b1081a1acffc5fb1f07503a"
    
    with col_win:
        if st.button("🏆 WIN"):
            st.balloons()
            st.success(f"Great work! Now lock it in: [Open Journal]({journal_url})")
            
    with col_loss:
        if st.button("❌ LOSS"):
            st.info(f"Part of the game. Review the data: [Open Journal]({journal_url})")
            
else:
    st.markdown("""
        <div style="background-color: #dc3545; color: white; padding: 20px; border-radius: 10px; text-align: center;">
            <h1>NO TRADE</h1>
            <p>Risk parameters or time check not met.</p>
        </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# --- RESET BUTTON ---
st.button("Reset Checklist", on_click=reset_callbacks)
