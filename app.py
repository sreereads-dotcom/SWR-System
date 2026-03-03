import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import io

st.set_page_config(page_title="SWR Local System", layout="wide")

# --- DATABASE ENGINE ---
DB_FILE = "swr_database.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Create tables if they don't exist
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (DDO TEXT, Date TEXT, Amount REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS linked (DDO TEXT, Scroll_Date TEXT, Cheque_Date TEXT, Amount REAL)''')
    conn.commit()
    conn.close()

init_db()

st.title("🏦 SWR Management System (Local DB)")

# --- 1. DATA UPLOAD SECTION ---
with st.expander("📥 STEP 1: UPLOAD & SAVE DATA", expanded=True):
    col1, col2 = st.columns(2)
    
    with col1:
        u_trans = st.file_uploader("Upload New Transactions (Excel)", type=['xlsx'])
        if u_trans and st.button("💾 Save to Local DB"):
            df = pd.read_excel(u_trans)
            conn = sqlite3.connect(DB_FILE)
            df.to_sql('transactions', conn, if_exists='append', index=False)
            conn.close()
            st.success(f"Added {len(df)} rows to Transactions!")

    with col2:
        u_linked = st.file_uploader("Upload New Linked Report (Excel)", type=['xlsx'])
        if u_linked and st.button("💾 Save to Local DB "):
            df = pd.read_excel(u_linked)
            # Rename columns to match DB
            df.columns = ['DDO', 'Scroll_Date', 'Cheque_Date', 'Amount']
            conn = sqlite3.connect(DB_FILE)
            df.to_sql('linked', conn, if_exists='append', index=False)
            conn.close()
            st.success(f"Added {len(df)} rows to Linked!")

# --- 2. REPORT GENERATION ---
st.divider()
st.subheader("📊 Generate SWR Report")

c1, c2 = st.columns(2)
with c1:
    u_ob = st.file_uploader("Upload OB Master (ob.xlsx)", type=['xlsx'])
with c2:
    u_staff = st.file_uploader("Upload Staff Mapping (staff.xlsx)", type=['xlsx'])

if all([u_ob, u_staff]):
    df_ob = pd.read_excel(u_ob)
    df_staff = pd.read_excel(u_staff)
    
    # FETCH FROM LOCAL SQLITE
    conn = sqlite3.connect(DB_FILE)
    df_t = pd.read_sql('SELECT * FROM transactions', conn)
    df_l = pd.read_sql('SELECT * FROM linked', conn)
    conn.close()

    if df_t.empty or df_l.empty:
        st.warning("Database is empty. Please upload data in Step 1 first.")
        st.stop()

    # Clean dates
    df_l['Scroll_Date'] = pd.to_datetime(df_l['Scroll_Date'], errors='coerce')
    df_l['cheque_clean'] = pd.to_datetime(df_l['Cheque_Date'], errors='coerce')
    df_t['trans_clean'] = pd.to_datetime(df_t['Date'], errors='coerce')

    staff_list = sorted(df_staff['Employee_Name'].unique().tolist())
    selected_staff = st.selectbox("👤 Select Employee", staff_list)
    my_ddos = df_staff[df_staff['Employee_Name'] == selected_staff]['DDO'].tolist()
    
    date_range = st.date_input("Select Range", value=(datetime(2025, 7, 1), datetime(2025, 9, 30)))
    
    if len(date_range) == 2:
        start_date, end_date = date_range
        months = pd.date_range(start=start_date, end=end_date, freq='MS').strftime('%Y-%m').tolist()
        final_rows = []

        for ddo in my_ddos:
            ob_row = df_ob[df_ob['DDO'] == ddo]
            if ob_row.empty: continue
            
            curr_amt = ob_row['ob_amount'].sum()
            curr_cnt = ob_row['ob_count'].sum()
            office = ob_row['Head Office'].iloc[0]

            for month in months:
                t_m = df_t[(df_t['DDO'] == ddo) & (df_t['trans_clean'].dt.strftime('%Y-%m') == month)]
                l_curr = df_l[(df_l['DDO'] == ddo) & (df_l['Scroll_Date'].dt.strftime('%Y-%m') == month) & (df_l['cheque_clean'].dt.strftime('%Y-%m') == month)]
                l_prev = df_l[(df_l['DDO'] == ddo) & (df_l['Scroll_Date'].dt.strftime('%Y-%m') == month) & (df_l['cheque_clean'].dt.strftime('%Y-%m') < month)]

                un_amt = (curr_amt + t_m['Amount'].sum()) - l_curr['Amount'].sum()
                un_cnt = (curr_cnt + len(t_m)) - len(l_curr)
                
                cl_amt = un_amt - l_prev['Amount'].sum()
                cl_cnt = un_cnt - len(l_prev)

                final_rows.append({
                    'Month': month, 'DDO': ddo, 'Office': office,
                    'Opening_Cnt': curr_cnt, 'Opening_Amt': curr_amt,
                    'Raised_Cnt': len(t_m), 'Raised_Amt': t_m['Amount'].sum(),
                    'Closing_Cnt': cl_cnt, 'Closing_Amt': cl_amt
                })
                curr_amt, curr_cnt = cl_amt, cl_cnt

        st.dataframe(pd.DataFrame(final_rows))
