import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime

st.set_page_config(page_title="SWR System", layout="wide")

# --- DATABASE SETUP ---
DB_FILE = "swr_database.db"

def init_db():
    # This creates the file if it doesn't exist
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS transactions 
                 (DDO TEXT, Date TEXT, Amount REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS linked 
                 (DDO TEXT, Scroll_Date TEXT, Cheque_Date TEXT, Amount REAL)''')
    conn.commit()
    conn.close()

# Run the creator immediately
init_db()

st.title("🏦 SWR Local Management System")

# --- 1. UPLOAD SECTION ---
with st.expander("📥 STEP 1: UPLOAD DATA", expanded=True):
    u_trans = st.file_uploader("Upload Transactions (Excel)", type=['xlsx'])
    if u_trans and st.button("💾 Save Transactions"):
        df = pd.read_excel(u_trans)
        # Ensure column names match DB exactly
        df.columns = [str(c).strip().capitalize() for c in df.columns]
        # Map them correctly
        df_final = df[['Ddo', 'Date', 'Amount']]
        df_final.columns = ['DDO', 'Date', 'Amount']
        
        conn = sqlite3.connect(DB_FILE)
        df_final.to_sql('transactions', conn, if_exists='append', index=False)
        conn.close()
        st.success("Successfully saved to database!")

# --- 2. DATABASE STATUS ---
if os.path.exists(DB_FILE):
    conn = sqlite3.connect(DB_FILE)
    t_count = pd.read_sql("SELECT COUNT(*) as count FROM transactions", conn).iloc[0]['count']
    conn.close()
    st.info(f"Storage Status: {t_count} rows currently saved in system.")
else:
    st.error("Database file initialization failed. Please refresh the page.")
