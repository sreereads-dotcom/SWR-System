import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
import io

st.set_page_config(page_title="SWR Management System", layout="wide")

# --- DATABASE SETUP ---
DB_FILE = "swr_database.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS transactions 
                 (DDO TEXT, Date TEXT, Amount REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS linked 
                 (DDO TEXT, Scroll_Date TEXT, Cheque_Date TEXT, Amount REAL)''')
    conn.commit()
    conn.close()

init_db()

st.title("🏦 SWR Management System")

# --- 1. DATA UPLOAD SECTION (TO DATABASE) ---
st.subheader("📥 Step 1: Sync Data to Local Storage")
with st.expander("Upload Excel Files to Database", expanded=False):
    col1, col2 = st.columns(2)
    
    with col1:
        u_trans = st.file_uploader("Upload Transactions (Excel)", type=['xlsx'], key="u_t")
        if u_trans and st.button("💾 Save Transactions to DB"):
            df = pd.read_excel(u_trans)
            # Standardize columns: DDO, Date, Amount
            df.columns = [str(c).strip().title() for c in df.columns]
            df_final = df[['Ddo', 'Date', 'Amount']]
            df_final.columns = ['DDO', 'Date', 'Amount']
            
            conn = sqlite3.connect(DB_FILE)
            df_final.to_sql('transactions', conn, if_exists='append', index=False)
            conn.close()
            st.success(f"Added {len(df_final)} rows to Transactions!")

    with col2:
        u_linked = st.file_uploader("Upload Linked Data (Excel)", type=['xlsx'], key="u_l")
        if u_linked and st.button("💾 Save Linked to DB"):
            df = pd.read_excel(u_linked)
            # Standardize columns: DDO, Scroll_Date, Cheque_Date, Amount
            df.columns = ['DDO', 'Scroll_Date', 'Cheque_Date', 'Amount']
            
            conn = sqlite3.connect(DB_FILE)
            df.to_sql('linked', conn, if_exists='append', index=False)
            conn.close()
            st.success(f"Added {len(df)} rows to Linked storage!")

# --- 2. REPORT GENERATION SECTION ---
st.divider()
st.subheader("📊 Step 2: Generate SWR Report")

c1, c2 = st.columns(2)
with c1:
    u_ob = st.file_uploader("Upload OB Master (ob.xlsx)", type=['xlsx'])
with c2:
    u_staff = st.file_uploader("Upload Staff Mapping (staff.xlsx)", type=['xlsx'])

if all([u_ob, u_staff]):
    # Load Master Files
    df_ob = pd.read_excel(u_ob)
    df_staff = pd.read_excel(u_staff)
    
    # Load from Database
    conn = sqlite3.connect(DB_FILE)
    df_t = pd.read_sql('SELECT * FROM transactions', conn)
    df_l = pd.read_sql('SELECT * FROM linked', conn)
    conn.close()

    if df_t.empty:
        st.warning("No Transactions found in Database. Please upload in Step 1.")
        st.stop()

    # Pre-process dates
    df_t['trans_clean'] = pd.to_datetime(df_t['Date'], errors='coerce')
    df_l['Scroll_Date'] = pd.to_datetime(df_l['Scroll_Date'], errors='coerce')
    df_l['cheque_clean'] = pd.to_datetime(df_l['Cheque_Date'], errors='coerce')

    # Selection UI
    staff_list = sorted(df_staff['Employee_Name'].unique().tolist())
    selected_staff = st.selectbox("👤 Select Employee", staff_list)
    
    # Filter DDOs for selected staff
    my_ddos = df_staff[df_staff['Employee_Name'] == selected_staff]['DDO'].tolist()
    
    date_range = st.date_input("Select Report Date Range", 
                               value=(datetime(2025, 7, 1), datetime(2025, 9, 30)))
    
    if len(date_range) == 2:
        start_date, end_date = date_range
        months = pd.date_range(start=start_date, end=end_date, freq='MS').strftime('%Y-%m').tolist()
        
        final_rows = []

        for ddo in my_ddos:
            # Find Opening Balance for this DDO
            ob_row = df_ob[df_ob['DDO'] == ddo]
            if ob_row.empty:
                continue
                
            curr_amt = ob_row['ob_amount'].sum()
            curr_cnt = ob_row['ob_count'].sum()
            office = ob_row['Head Office'].iloc[0]

            for month in months:
                # 1. New Transactions in this month
                t_m = df_t[(df_t['DDO'] == ddo) & (df_t['trans_clean'].dt.strftime('%Y-%m') == month)]
                
                # 2. Linked items (Current month scroll linked to current month cheque)
                l_curr = df_l[(df_l['DDO'] == ddo) & 
                              (df_l['Scroll_Date'].dt.strftime('%Y-%m') == month) & 
                              (df_l['cheque_clean'].dt.strftime('%Y-%m') == month)]
                
                # 3. Linked items (Current month scroll linked to OLD cheques)
                l_prev = df_l[(df_l['DDO'] == ddo) & 
                              (df_l['Scroll_Date'].dt.strftime('%Y-%m') == month) & 
                              (df_l['cheque_clean'].dt.strftime('%Y-%m') < month)]

                # SWR Logic
                # Unlinked = (Opening + New) - (Current Links)
                un_amt = (curr_amt + t_m['Amount'].sum()) - l_curr['Amount'].sum()
                un_cnt = (curr_cnt + len(t_m)) - len(l_curr)
                
                # Closing = Unlinked - (Previous Links cleared this month)
                cl_amt = un_amt - l_prev['Amount'].sum()
                cl_cnt = un_cnt - len(l_prev)

                final_rows.append({
                    'Month': month, 'DDO': ddo, 'Office': office,
                    'Opening_Cnt': curr_cnt, 'Opening_Amt': curr_amt,
                    'New_Raised_Cnt': len(t_m), 'New_Raised_Amt': t_m['Amount'].sum(),
                    'Closing_Cnt': cl_cnt, 'Closing_Amt': cl_amt
                })
                # Update OB for next month iteration
                curr_amt, curr_cnt = cl_amt, cl_cnt

        if final_rows:
            report_df = pd.DataFrame(final_rows)
            st.dataframe(report_df, use_container_width=True)
            
            # Export to Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                report_df.to_excel(writer, index=False)
            st.download_button("📥 Download This Report", output.getvalue(), "SWR_Final_Report.xlsx")
        else:
            st.info("No data found for the selected criteria.")
