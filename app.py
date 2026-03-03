import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
import io

st.set_page_config(page_title="SWR Management System", layout="wide")

# --- DATABASE SETUP ---
DB_FILE = "swr_master_database.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Core Tables
    c.execute('CREATE TABLE IF NOT EXISTS transactions (DDO TEXT, Date TEXT, Amount REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS linked (DDO TEXT, Scroll_Date TEXT, Cheque_Date TEXT, Amount REAL)')
    # Permanent Master Tables
    c.execute('CREATE TABLE IF NOT EXISTS ob_master (DDO TEXT, Head_Office TEXT, ob_count INTEGER, ob_amount REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS staff_mapping (Employee_Name TEXT, DDO TEXT)')
    conn.commit()
    conn.close()

init_db()

st.title("🏦 SWR Professional Management System")

# --- 1. DATA CENTER (UPLOAD & DELETE) ---
st.subheader("⚙️ Data Management Hub")
tabs = st.tabs(["📤 Upload Data", "🗑️ Manage/Delete Data"])

with tabs[0]:
    col1, col2 = st.columns(2)
    with col1:
        st.info("📊 Step 1: Upload Reports")
        u_t = st.file_uploader("Transaction Report", type=['xlsx'], key="ut")
        if u_t and st.button("Save Transactions"):
            df = pd.read_excel(u_t)
            df.columns = [str(c).strip().title() for c in df.columns]
            df_final = df[['Ddo', 'Date', 'Amount']].rename(columns={'Ddo': 'DDO'})
            conn = sqlite3.connect(DB_FILE)
            df_final.to_sql('transactions', conn, if_exists='append', index=False)
            conn.close()
            st.success("Transactions Saved!")

        u_l = st.file_uploader("Linked Report", type=['xlsx'], key="ul")
        if u_l and st.button("Save Linked Data"):
            df = pd.read_excel(u_l)
            # Match your 'linked report correct.xlsx' structure
            df_final = df[['DDO', 'Scroll Date', 'Cheque/Trans Date', 'Transaction Amount']]
            df_final.columns = ['DDO', 'Scroll_Date', 'Cheque_Date', 'Amount']
            conn = sqlite3.connect(DB_FILE)
            df_final.to_sql('linked', conn, if_exists='append', index=False)
            conn.close()
            st.success("Linked Data Saved!")

    with col2:
        st.info("📋 Step 2: Upload Permanent Masters")
        u_ob = st.file_uploader("OB Master", type=['xlsx'], key="uob")
        if u_ob and st.button("Save OB Master Permanently"):
            df = pd.read_excel(u_ob)
            df.columns = ['DDO', 'Head_Office', 'ob_count', 'ob_amount', 'Remarks'] # Adjusted for your ob.xlsx
            conn = sqlite3.connect(DB_FILE)
            df[['DDO', 'Head_Office', 'ob_count', 'ob_amount']].to_sql('ob_master', conn, if_exists='append', index=False)
            conn.close()
            st.success("OB Master Saved!")

        u_s = st.file_uploader("Staff Mapping", type=['xlsx'], key="us")
        if u_s and st.button("Save Staff Mapping Permanently"):
            df = pd.read_excel(u_s)
            conn = sqlite3.connect(DB_FILE)
            df.to_sql('staff_mapping', conn, if_exists='append', index=False)
            conn.close()
            st.success("Staff Mapping Saved!")

with tabs[1]:
    st.warning("Danger Zone: Deleting data cannot be undone.")
    conn = sqlite3.connect(DB_FILE)
    
    # Show counts
    t_count = pd.read_sql("SELECT COUNT(*) as c FROM transactions", conn).iloc[0]['c']
    l_count = pd.read_sql("SELECT COUNT(*) as c FROM linked", conn).iloc[0]['c']
    o_count = pd.read_sql("SELECT COUNT(*) as c FROM ob_master", conn).iloc[0]['c']
    s_count = pd.read_sql("SELECT COUNT(*) as c FROM staff_mapping", conn).iloc[0]['c']

    c1, c2, c3, c4 = st.columns(4)
    if c1.button(f"🗑️ Delete Transactions ({t_count})"):
        conn.execute("DELETE FROM transactions")
        conn.commit()
        st.rerun()
    if c2.button(f"🗑️ Delete Linked ({l_count})"):
        conn.execute("DELETE FROM linked")
        conn.commit()
        st.rerun()
    if c3.button(f"🗑️ Delete OB Master ({o_count})"):
        conn.execute("DELETE FROM ob_master")
        conn.commit()
        st.rerun()
    if c4.button(f"🗑️ Delete Staff ({s_count})"):
        conn.execute("DELETE FROM staff_mapping")
        conn.commit()
        st.rerun()
    conn.close()

# --- 2. REPORT GENERATION ---
st.divider()
st.subheader("📊 Step 3: Generate SWR Report")

conn = sqlite3.connect(DB_FILE)
df_staff = pd.read_sql('SELECT * FROM staff_mapping', conn)
df_ob = pd.read_sql('SELECT * FROM ob_master', conn)
df_t = pd.read_sql('SELECT * FROM transactions', conn)
df_l = pd.read_sql('SELECT * FROM linked', conn)
conn.close()

if not df_staff.empty and not df_ob.empty:
    # Cleaning
    for df_tmp in [df_ob, df_staff, df_t, df_l]:
        if 'DDO' in df_tmp.columns:
            df_tmp['DDO'] = df_tmp['DDO'].astype(str).str.strip()

    df_t['Date'] = pd.to_datetime(df_t['Date'], errors='coerce')
    df_l['Scroll_Date'] = pd.to_datetime(df_l['Scroll_Date'], errors='coerce')

    staff_list = sorted(df_staff['Employee_Name'].unique().tolist())
    sel_staff = st.selectbox("👤 Select Employee", staff_list)
    my_ddos = df_staff[df_staff['Employee_Name'] == sel_staff]['DDO'].tolist()
    
    date_range = st.date_input("Select Period", value=(datetime(2025, 7, 1), datetime(2025, 9, 30)))
    
    if len(date_range) == 2:
        start_date, end_date = date_range
        months = pd.date_range(start=start_date, end=end_date, freq='MS').strftime('%Y-%m').tolist()
        final_rows = []

        for ddo in my_ddos:
            ob_row = df_ob[df_ob['DDO'] == ddo]
            curr_amt = ob_row['ob_amount'].sum() if not ob_row.empty else 0
            curr_cnt = ob_row['ob_count'].sum() if not ob_row.empty else 0
            office = ob_row['Head_Office'].iloc[0] if not ob_row.empty else "Unknown"

            for month in months:
                t_m = df_t[(df_t['DDO'] == ddo) & (df_t['Date'].dt.strftime('%Y-%m') == month)]
                l_m = df_l[(df_l['DDO'] == ddo) & (df_l['Scroll_Date'].dt.strftime('%Y-%m') == month)]
                
                n_amt, n_cnt = t_m['Amount'].sum(), len(t_m)
                li_amt, li_cnt = l_m['Amount'].sum(), len(l_m)

                cl_amt = (curr_amt + n_amt) - li_amt
                cl_cnt = (curr_cnt + n_cnt) - li_cnt

                final_rows.append({
                    'Month': month, 'DDO': ddo, 'Office': office,
                    'Opening_Cnt': int(curr_cnt), 'Opening_Amt': float(curr_amt),
                    'New_Raised_Cnt': int(n_cnt), 'New_Raised_Amt': float(n_amt),
                    'Closing_Cnt': int(cl_cnt), 'Closing_Amt': float(cl_amt)
                })
                curr_amt, curr_cnt = cl_amt, cl_cnt

        if final_rows:
            st.dataframe(pd.DataFrame(final_rows), use_container_width=True)
else:
    st.info("Please upload Staff Mapping and OB Master in the Hub above to begin.")
