import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
from datetime import datetime
import os
from config import DB_CONFIG

st.set_page_config(page_title="OptimaCV Dashboard", layout="wide", page_icon="🎯")

@st.cache_resource
def init_connection():
    # Use PyMySQL driver for SQLAlchemy
    conn_str = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['db']}?charset=utf8mb4"
    return create_engine(conn_str)

@st.cache_data(ttl=60)
def load_data():
    engine = init_connection()
    df = pd.read_sql("SELECT * FROM job_listings ORDER BY created_at DESC", engine)
    return df

st.title("🎯 OptimaCV Stealth Job Aggregator")
st.markdown("Monitor and explore aggregated jobs matching your keywords across platforms.")

# Load Data
try:
    df = load_data()
except Exception as e:
    st.error(f"Failed to connect to MySQL database: {e}")
    st.stop()

if df.empty:
    st.warning("No jobs found in the database. Run the scraper pipeline first!")
    st.stop()

# Prepare Data
df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
df['post_date'] = pd.to_datetime(df['post_date'], errors='coerce')

# Metrics
today = datetime.now().date()
jobs_today = df[df['created_at'].dt.date == today].shape[0]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Jobs", f"{len(df):,}")
col2.metric("Added Today", f"+{jobs_today}")
col3.metric("Sources", f"{df['source'].nunique()}")
col4.metric("Unique Companies", f"{df['company'].nunique():,}")

st.divider()

# Charts row
c1, c2 = st.columns(2)

with c1:
    st.subheader("📈 Jobs by Source")
    source_counts = df['source'].value_counts().reset_index()
    source_counts.columns = ['source', 'count'] # ensure correct names
    fig1 = px.bar(source_counts, x='source', y='count', color='source', text_auto=True, 
                  color_discrete_sequence=px.colors.qualitative.Pastel)
    fig1.update_layout(showlegend=False, xaxis_title="", yaxis_title="Number of Jobs")
    st.plotly_chart(fig1, use_container_width=True)

with c2:
    st.subheader("🌍 Location Distribution")
    # Clean location text a bit for pie chart
    df['clean_location'] = df['location'].astype(str).str.split(',').str[0].str.strip()
    loc_counts = df['clean_location'].value_counts().reset_index().head(10)
    loc_counts.columns = ['clean_location', 'count']
    fig2 = px.pie(loc_counts, values='count', names='clean_location', hole=0.4,
                  color_discrete_sequence=px.colors.qualitative.Pastel)
    fig2.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# Data Viewer
st.subheader("🔎 Job Explorer")

# Search and filter
search_term = st.text_input("Search by Job Title or Company", "")

filtered_df = df.copy()
if search_term:
    search_term = search_term.lower()
    filtered_df = filtered_df[
        filtered_df['title'].astype(str).str.lower().str.contains(search_term) | 
        filtered_df['company'].astype(str).str.lower().str.contains(search_term)
    ]

# Display dataframe with custom columns
display_cols = ["title", "company", "location", "apply_url", "source", "post_date"]

# Clickable link configuration
st.dataframe(
    filtered_df[display_cols],
    use_container_width=True,
    hide_index=True,
    column_config={
        "apply_url": st.column_config.LinkColumn(
            "Apply Link", 
            display_text="Apply Here 🔗",
            width="small"
        ),
        "post_date": st.column_config.DateColumn("Posted Date", format="YYYY-MM-DD"),
        "title": st.column_config.TextColumn("Job Title"),
        "company": st.column_config.TextColumn("Company"),
        "location": st.column_config.TextColumn("Location"),
        "source": st.column_config.TextColumn("Source"),
    }
)
