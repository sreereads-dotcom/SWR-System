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
    c.execute('CREATE TABLE IF NOT EXISTS transactions (DDO TEXT, Date TEXT, Amount REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS linked (DDO TEXT, Scroll_Date TEXT, Cheque_Date TEXT, Amount REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS ob_master (DDO TEXT, Head_Office TEXT, ob_count INTEGER, ob_amount REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS staff_mapping (Employee_Name TEXT, DDO TEXT)')
    conn.commit()
    conn.close()

init_db()

def color_closing(val):
    color = 'background-color: #d4edda; color: #155724;' if val == 0 else 'background-color: #f8d7da; color: #721c24;'
    return color

st.title("🏦 SWR Professional Management System")

# --- 1. DATA CENTER ---
st.subheader("⚙️ Data Management Hub")
tabs = st.tabs(["📤 Upload Data", "🗑️ Manage/Delete Data"])

with tabs[0]:
    col1, col2 = st.columns(2)
    with col1:
        st.info("📊 Step 1: Upload Reports")
        u_t = st.file_uploader("Transaction Report", type=['xlsx'], key="ut")
        if u_t and st.button("Save Transactions"):
            df = pd.read_excel(u_t)
            df.columns = [str(c).strip().lower() for c in df.columns]
            df_final = df[['ddo', 'date', 'amount']]
            df_final.columns = ['DDO', 'Date', 'Amount']
            conn = sqlite3.connect(DB_FILE)
            df_final.to_sql('transactions', conn, if_exists='append', index=False)
            conn.close()
            st.success("Transactions Saved!")

        u_l = st.file_uploader("Linked Report", type=['xlsx'], key="ul")
        if u_l and st.button("Save Linked Data"):
            df = pd.read_excel(u_l)
            df.columns = [str(c).strip().lower() for c in df.columns]
            # Flexible mapping for Linked report
            df_final = df[['ddo', 'scroll date', 'cheque/trans date', 'transaction amount']]
            df_final.columns = ['DDO', 'Scroll_Date', 'Cheque_Date', 'Amount']
            conn = sqlite3.connect(DB_FILE)
            df_final.to_sql('linked', conn, if_exists='append', index=False)
            conn.close()
            st.success("Linked Data Saved!")

    with col2:
        st.info("📋 Step 2: Upload Permanent Masters")
        u_ob = st.file_uploader("OB Master", type=['xlsx'], key="uob")
        if u_ob and st.button("Save OB Master"):
            df = pd.read_excel(u_ob)
            # CLEANING: Remove spaces and lowercase all column names
            df.columns = [str(c).strip().lower() for c in df.columns]
            try:
                # Find columns even if they have spaces like 'head office' or 'ob amount'
                df_db = df[['ddo', 'head office', 'ob_count', 'ob_amount']]
                df_db.columns = ['DDO', 'Head_Office', 'ob_count', 'ob_amount']
                conn = sqlite3.connect(DB_FILE)
                df_db.to_sql('ob_master', conn, if_exists='append', index=False)
                conn.close()
                st.success("OB Saved!")
            except KeyError as e:
                st.error(f"Could not find required columns in OB file. Found: {list(df.columns)}")

        u_s = st.file_uploader("Staff Mapping", type=['xlsx'], key="us")
        if u_s and st.button("Save Staff Mapping"):
            df = pd.read_excel(u_s)
            df.columns = [str(c).strip().lower() for c in df.columns]
            df.columns = ['employee_name', 'ddo'] # Force standard names
            conn = sqlite3.connect(DB_FILE)
            df.to_sql('staff_mapping', conn, if_exists='append', index=False)
            conn.close()
            st.success("Staff Saved!")

with tabs[1]:
    conn = sqlite3.connect(DB_FILE)
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("🗑️ Clear Transactions"):
        conn.execute("DELETE FROM transactions"); conn.commit(); st.rerun()
    if c2.button("🗑️ Clear Linked"):
        conn.execute("DELETE FROM linked"); conn.commit(); st.rerun()
    if c3.button("🗑️ Clear OB"):
        conn.execute("DELETE FROM ob_master"); conn.commit(); st.rerun()
    if c4.button("🗑️ Clear Staff"):
        conn.execute("DELETE FROM staff_mapping"); conn.commit(); st.rerun()
    conn.close()

# --- 2. REPORT GENERATION ---
st.divider()
st.subheader("📊 Step 3: Generate SWR Analysis")

conn = sqlite3.connect(DB_FILE)
df_staff = pd.read_sql('SELECT * FROM staff_mapping', conn)
df_ob = pd.read_sql('SELECT * FROM ob_master', conn)
df_t = pd.read_sql('SELECT * FROM transactions', conn)
df_l = pd.read_sql('SELECT * FROM linked', conn)
conn.close()

if not df_staff.empty and not df_ob.empty:
    for df_tmp in [df_ob, df_staff, df_t, df_l]:
        if 'DDO' in df_tmp.columns: df_tmp['DDO'] = df_tmp['DDO'].astype(str).str.strip()
        if 'ddo' in df_tmp.columns: df_tmp['ddo'] = df_tmp['ddo'].astype(str).str.strip()

    df_t['Date'] = pd.to_datetime(df_t['Date'], errors='coerce')
    df_l['Scroll_Date'] = pd.to_datetime(df_l['Scroll_Date'], errors='coerce')

    # Mapping staff columns correctly
    staff_col = 'employee_name' if 'employee_name' in df_staff.columns else 'Employee_Name'
    ddo_col = 'ddo' if 'ddo' in df_staff.columns else 'DDO'

    staff_list = sorted(df_staff[staff_col].unique().tolist())
    sel_staff = st.selectbox("👤 Select Employee", staff_list)
    my_ddos = df_staff[df_staff[staff_col] == sel_staff][ddo_col].tolist()
    
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
                    'Opening_Cnt': int(curr_cnt), 'Opening_Amt': round(float(curr_amt), 2),
                    'New_Raised_Cnt': int(n_cnt), 'New_Raised_Amt': round(float(n_amt), 2),
                    'Linked_Cnt': int(li_cnt), 'Linked_Amt': round(float(li_amt), 2),
                    'Closing_Cnt': int(cl_cnt), 'Closing_Amt': round(float(cl_amt), 2)
                })
                curr_amt, curr_cnt = cl_amt, cl_cnt

        if final_rows:
            report_df = pd.DataFrame(final_rows)
            st.write("#### 📅 Monthly Detailed Breakdown")
            styled_df = report_df.style.applymap(color_closing, subset=['Closing_Cnt'])
            st.dataframe(styled_df, use_container_width=True)

            st.write("#### 🎯 Final Unlinked Position Summary")
            summary_df = report_df.groupby('DDO').last().reset_index()
            summary_df = summary_df[['DDO', 'Office', 'Month', 'Closing_Cnt', 'Closing_Amt']]
            summary_df.columns = ['DDO', 'Head Office', 'As of Month', 'Final Pending Count', 'Final Pending Amount']
            styled_summary = summary_df.style.applymap(color_closing, subset=['Final Pending Count'])
            st.table(styled_summary)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                report_df.to_excel(writer, index=False, sheet_name='Monthly_Details')
                summary_df.to_excel(writer, index=False, sheet_name='Summary')
            st.download_button("📥 Download Excel Report", output.getvalue(), "SWR_Analysis.xlsx")
else:
    st.info("Please upload Staff Mapping and OB Master in the Hub above.")
