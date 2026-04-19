import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
from datetime import datetime
import os
from config import DB_CONFIG
import sys
import subprocess
import psutil
import time

# ── Page Configuration & CSS ──────────────────────────────────────────────────
st.set_page_config(page_title="OptimaCV", layout="wide", page_icon="🎯", initial_sidebar_state="expanded")

# Inject Custom Professional CSS
st.markdown("""
<style>
    /* Hide Streamlit menu and footer, but keep header for sidebar toggle */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    
    /* Professional Typography & Styling */
    .stApp {
        background-color: #0d1117;
        color: #e6edf3;
    }
    
    /* Elegant Title for Splash Screens */
    .splash-title {
        font-size: 4rem !important;
        font-weight: 800;
        text-align: center;
        background: -webkit-linear-gradient(45deg, #a855f7, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    .splash-subtitle {
        font-size: 1.5rem;
        color: #8b949e;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    /* Explanation Box */
    .info-box {
        background: linear-gradient(145deg, #161b22, #0d1117);
        border-left: 4px solid #3b82f6;
        padding: 2rem;
        border-radius: 8px;
        font-size: 1.2rem;
        line-height: 1.8;
        color: #c9d1d9;
    }
    
    /* Button centering hack */
    .stButton > button {
        display: block;
        margin: 0 auto;
        padding: 0.5rem 2rem;
        font-size: 1.2rem;
        border-radius: 8px;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# ── Session State for Onboarding ──────────────────────────────────────────────
if 'onboarding_step' not in st.session_state:
    st.session_state.onboarding_step = 1

def next_step():
    st.session_state.onboarding_step += 1

# ── Initialization Helpers ────────────────────────────────────────────────────
PID_FILE = "scraper.pid"

def get_scraper_pid():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            if psutil.pid_exists(pid):
                p = psutil.Process(pid)
                cmd = " ".join(p.cmdline()).lower()
                if "python" in cmd and "run.py" in cmd:
                    return pid
        except Exception:
            pass
    return None

@st.cache_resource
def init_connection():
    # Use PyMySQL driver for SQLAlchemy
    conn_str = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['db']}?charset=utf8mb4"
    return create_engine(conn_str)

def load_data():  # Removed ttl cache so it reloads fresh data live
    try:
        engine = init_connection()
        df = pd.read_sql("SELECT * FROM job_listings ORDER BY created_at DESC", engine)
        return df
    except Exception as e:
        return pd.DataFrame()


# ── Render App by Step ───────────────────────────────────────────────────────

if st.session_state.onboarding_step == 1:
    # STEP 1: WELCOME
    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    st.markdown("<h1 class='splash-title'>Welcome to OptimaCV Job Scraper</h1>", unsafe_allow_html=True)
    st.markdown("<p class='splash-subtitle'>Advanced Stealth Job Aggregation Engine</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.button("Continue ➡️", on_click=next_step, use_container_width=True)

elif st.session_state.onboarding_step == 2:
    # STEP 3: EXPLANATION
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center;'>How It Works</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.markdown("""
        <div class="info-box">
            <p><strong>OptimaCV</strong> is an automated, high-stealth job collection system built to bypass modern bot protection mechanisms.</p>
            <p>It continuously explores platforms like LinkedIn and Indeed in the background, rotating screen resolutions, simulating human reading patterns, and utilizing multi-threaded Playwright environments.</p>
            <p>Job data is aggregated, parsed through Gemini AI, and stored directly into your localized dashboard for instant business intelligence.</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    colA, colB, colC = st.columns([1, 1, 1])
    with colB:
        st.button("Launch Dashboard 🚀", on_click=next_step, use_container_width=True, type="primary")

elif st.session_state.onboarding_step >= 3:
    # MAINT DASHBOARD
    
    # Sidebar Controls
    st.sidebar.markdown("<h2 style='text-align: center;'>⚙️ Control Panel</h2>", unsafe_allow_html=True)
    running_pid = get_scraper_pid()
    
    if running_pid:
        st.sidebar.success(f"🟢 Active (PID: {running_pid})")
        if st.sidebar.button("⏹️ Halt Process"):
            try:
                p = psutil.Process(running_pid)
                p.terminate()
                if os.path.exists(PID_FILE):
                    os.remove(PID_FILE)
                st.sidebar.warning("Scheduler stopped.")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Failed to stop: {e}")
    else:
        st.sidebar.warning("🔴 Engine Offline")
        interval = st.sidebar.number_input("Interval (hours)", min_value=1, max_value=24, value=4)
        if st.sidebar.button("▶️ Initialize Engine"):
            flags = subprocess.CREATE_NEW_CONSOLE | subprocess.DETACHED_PROCESS if sys.platform == "win32" else 0
            p = subprocess.Popen(
                [sys.executable, "run.py", "--continuous", "--interval", str(interval)],
                creationflags=flags
            )
            with open(PID_FILE, "w") as f:
                f.write(str(p.pid))
            st.sidebar.success("Engine Engaged!")
            time.sleep(1) # small delay to let process start
            st.rerun()
            
    st.sidebar.divider()
    if st.sidebar.button("🚀 Force Run Now", type="secondary"):
        with st.spinner("Executing pipeline..."):
            subprocess.run([sys.executable, "run.py"])
        st.sidebar.success("Execution Complete!")
        st.rerun()

    
    # Main Content Area
    st.markdown("<h1 class='splash-title' style='text-align: left; font-size: 3rem !important;'>OptimaCV Dashboard</h1>", unsafe_allow_html=True)
    
    df = load_data()
    
    # Define Tabs
    tab_dash, tab_explore, tab_logs = st.tabs(["📊 Analytics Overview", "🔎 Job Explorer", "📄 Engine Logs"])
    
    with tab_dash:
        if df.empty:
            st.warning("Database empty. Initiate the engine from the control panel.")
        else:
            df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
            df['post_date'] = pd.to_datetime(df['post_date'], errors='coerce')
            today = datetime.now().date()
            jobs_today = df[df['created_at'].dt.date == today].shape[0]

            # Top Metrics
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Intel Gathered", f"{len(df):,}")
            c2.metric("New Today", f"+{jobs_today}")
            c3.metric("Data Sources", f"{df['source'].nunique()}")
            c4.metric("Entities Targeted", f"{df['company'].nunique():,}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Charts
            c_left, c_right = st.columns(2)
            with c_left:
                st.subheader("Source Distribution")
                src = df['source'].value_counts().reset_index()
                src.columns = ['source', 'count']
                fig1 = px.bar(src, x='source', y='count', color='source', text_auto=True,
                              color_discrete_sequence=px.colors.qualitative.Pastel)
                fig1.update_layout(showlegend=False, xaxis_title="", yaxis_title="Records", 
                                   paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#c9d1d9'))
                st.plotly_chart(fig1, use_container_width=True)
                
            with c_right:
                st.subheader("Location Density")
                df['clean_loc'] = df['location'].astype(str).str.split(',').str[0].str.strip()
                loc = df['clean_loc'].value_counts().reset_index().head(5)
                loc.columns = ['clean_loc', 'count']
                fig2 = px.pie(loc, values='count', names='clean_loc', hole=0.5,
                              color_discrete_sequence=px.colors.qualitative.Pastel)
                fig2.update_traces(textposition='inside', textinfo='percent+label')
                fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#c9d1d9'))
                st.plotly_chart(fig2, use_container_width=True)

    with tab_explore:
        if not df.empty:
            search_query = st.text_input("Deep Search (Title/Company)", placeholder="e.g. Machine Learning...")
            
            mask = df.copy()
            if search_query:
                sq = search_query.lower()
                mask = mask[
                    mask['title'].astype(str).str.lower().str.contains(sq) | 
                    mask['company'].astype(str).str.lower().str.contains(sq)
                ]
            
            display_cols = ["title", "company", "location", "apply_url", "source", "post_date"]
            st.dataframe(
                mask[display_cols],
                use_container_width=True,
                hide_index=True,
                height=600,
                column_config={
                    "apply_url": st.column_config.LinkColumn("Apply Link", display_text="Open Link 🔗"),
                    "post_date": st.column_config.DateColumn("System Time", format="YYYY-MM-DD"),
                    "title": st.column_config.TextColumn("Designation"),
                    "company": st.column_config.TextColumn("Entity"),
                    "location": st.column_config.TextColumn("Vector"),
                    "source": st.column_config.TextColumn("Node"),
                }
            )

    with tab_logs:
        st.subheader("Live System Output")
        colA, colB = st.columns([6, 2])
        with colB:
            if st.button("🔄 Refresh", use_container_width=False):
                st.rerun()
                
        log_file = "logs/scraper.log"
        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                    recent_logs = "".join(lines[-150:]) # show deeper logs in main dash
                
                # Render logs with fixed width styling to look like a terminal
                st.markdown(f"""
                <div style="background-color: #000; padding: 15px; border-radius: 8px; font-family: monospace; color: #0f0; max-height: 500px; overflow-y: scroll;">
                    <pre style="color: #0f0; background: transparent; border: none; white-space: pre-wrap;">{recent_logs}</pre>
                </div>
                """, unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"Error reading logs: {e}")
        else:
            st.info("System logs are currently empty. Awaiting execution.")
