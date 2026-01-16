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
    .grade-box { padding:20px; border-radius:10px; text-align:center; color:white; margin-bottom: 20px;}
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
    start_time = ny_time.replace(hour=9, minute=30, second=0, microsecond=0)
    end_time = ny_time.replace(hour=11, minute=0, second=0, microsecond=0)
    return start_time <= ny_time <= end_time

def reset_callbacks():
    keys = ['p1_c1', 'p1_c2', 'p1_c3', 'p1_c4', 
            'p2_c1', 'p2_c2', 'p2_c3', 'p2_c4', 
            'p3_c1', 'p3_c2', 'p3_c3', 'p3_c4']
    for key in keys:
        if key in st.session_state:
            st.session_state[key] = False

# --- SIDEBAR ---
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
st.info("Finding the 'Magnet' that pulls the price.")

p1_c1 = st.checkbox("Identify 15m DOL: Where is the 'pile of money'? (Old High/Low, Equal Highs)", key='p1_c1')
p1_c2 = st.checkbox("Confirm 15m Trend: Is price clearly 'stepping' higher or lower?", key='p1_c2')
p1_c3 = st.checkbox("Liquidity Sweep: Has price taken out a recent 5m/15m swing?", key='p1_c3')
p1_c4 = st.checkbox("Time Check: Am I inside 9:30 AM – 11:00 AM NY?", key='p1_c4')

st.markdown("---")

# --- PHASE 2: THE EXECUTION ---
st.header("Phase 2: The Execution (1m)")
st.info("Waiting for the 'Robot' to switch directions.")

p2_c1 = st.checkbox("Displacement: Big, fast candles moving away from the sweep?", key='p2_c1')
p2_c2 = st.checkbox("MSS: Did price break the last 1m swing point?", key='p2_c2')
p2_c3 = st.checkbox("Identify IFVG: Aggressive close through a previous FVG?", key='p2_c3')
p2_c4 = st.checkbox("Entry Trigger: Did a 1m candle close above/below the IFVG?", key='p2_c4')

st.markdown("---")

# --- PHASE 3: THE BUSINESS ---
st.header("Phase 3: The Business (Risk & Mgmt)")
st.info("Mechanical rules for the funded account.")

p3_c1 = st.checkbox("Stop Loss: Is SL safe at the recent 1m swing point?", key='p3_c1')
p3_c2 = st.checkbox("RR Check: At least 1:1 RR before the next obstacle?", key='p3_c2')
p3_c3 = st.checkbox("$400 Rule: If this hits 1R, is profit >= $400?", key='p3_c3')
p3_c4 = st.checkbox("Bank 1R Plan: Prepared to exit if it stalls at 1R?", key='p3_c4')

st.markdown("---")

# --- SCORING SYSTEM ---
# Count total checked boxes
total_score = sum([
    p1_c1, p1_c2, p1_c3, p1_c4,
    p2_c1, p2_c2, p2_c3, p2_c4,
    p3_c1, p3_c2, p3_c3, p3_c4
])

st.subheader("🏁 Trade Quality Score")

# Logic for Grades
if total_score == 12:
    grade = "A+"
    color = "#28a745" # Green
    msg = "🦄 UNICORN SETUP (All Systems Go)"
elif total_score >= 10:
    grade = "A"
    color = "#5a9bd4" # Blue
    msg = "High Probability Trade (Execute with Confidence)"
elif total_score >= 8:
    grade = "B"
    color = "#ffc107" # Yellow/Orange (Text black for contrast usually, but keeping white text for simple CSS)
    # Adjusting text color for yellow background visibility if needed, or using a darker orange
    color = "#fd7e14" # Orange
    msg = "Decent Setup (Watch Risk Carefully)"
elif total_score >= 5:
    grade = "C"
    color = "#6c757d" # Grey
    msg = "Weak / Forced Trade (Lower Size Recommended)"
else:
    grade = "D"
    color = "#dc3545" # Red
    msg = "NO TRADE (Stay Away)"

# Display the Score Card
st.markdown(f"""
    <div class="grade-box" style="background-color: {color};">
        <h1>Grade: {grade}</h1>
        <h3>{total_score} / 12 Criteria Met</h3>
        <p>{msg}</p>
    </div>
""", unsafe_allow_html=True)

# --- POST TRADE LOGGING ---
st.markdown("### 📝 Post-Trade Outcome")
st.write("If you took the trade, how did it go?")

col_win, col_loss = st.columns(2)
journal_url = "https://wide-kayak-822.notion.site/Backtesting-2e7a40276b1081a1acffc5fb1f07503a"

with col_win:
    if st.button("🏆 WIN"):
        st.balloons()
        st.success(f"Great work! Journal it: [Open Notion]({journal_url})")
        
with col_loss:
    if st.button("❌ LOSS"):
        st.info(f"Review the data: [Open Notion]({journal_url})")

st.markdown("---")

# --- RESET BUTTON ---
st.button("Reset Checklist", on_click=reset_callbacks)
