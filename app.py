import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import io

st.set_page_config(page_title="SWR Cloud System", layout="wide")

# --- CLOUD CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("🏦 SWR Cloud Management System")

# --- 1. CLOUD SYNC SECTION ---
with st.expander("📥 STEP 1: SYNC DATA TO GOOGLE SHEETS", expanded=True):
    col1, col2 = st.columns(2)
    
    with col1:
        u_trans = st.file_uploader("Upload New Transactions (Excel)", type=['xlsx'])
        if u_trans and st.button("💾 Save Transactions to Cloud"):
            new_t = pd.read_excel(u_trans)
            old_t = conn.read(worksheet="Transactions", ttl=0)
            combined_t = pd.concat([old_t, new_t], ignore_index=True)
            conn.update(worksheet="Transactions", data=combined_t)
            st.success("Transactions Synced to Google Sheets!")

    with col2:
        u_linked = st.file_uploader("Upload New Linked Report (Excel)", type=['xlsx'])
        if u_linked and st.button("💾 Save Linked to Cloud"):
            new_l = pd.read_excel(u_linked)
            old_l = conn.read(worksheet="Linked", ttl=0)
            combined_l = pd.concat([old_l, new_l], ignore_index=True)
            conn.update(worksheet="Linked", data=combined_l)
            st.success("Linked Data Synced to Google Sheets!")

# --- 2. REPORT GENERATION ---
st.divider()
st.subheader("📊 Generate SWR Report from Cloud Storage")

c1, c2 = st.columns(2)
with c1:
    u_ob = st.file_uploader("Upload OB Master (ob.xlsx)", type=['xlsx'])
with c2:
    u_staff = st.file_uploader("Upload Staff Mapping (staff.xlsx)", type=['xlsx'])

if all([u_ob, u_staff]):
    df_ob = pd.read_excel(u_ob)
    df_staff = pd.read_excel(u_staff)
    
    # FETCH FROM GOOGLE SHEETS
    df_t = conn.read(worksheet="Transactions", ttl=0)
    df_l = conn.read(worksheet="Linked", ttl=0)

    # --- PROCESSOR ---
    # Standardize column names for processing
    df_l['Scroll Date'] = pd.to_datetime(df_l['Scroll Date'], errors='coerce')
    df_l['cheque_clean'] = pd.to_datetime(df_l['Cheque Date'], errors='coerce')
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
            current_ob_amt = df_ob[df_ob['DDO'] == ddo]['ob_amount'].sum()
            current_ob_cnt = df_ob[df_ob['DDO'] == ddo]['ob_count'].sum()
            office_name = df_ob[df_ob['DDO'] == ddo]['Head Office'].iloc[0] if ddo in df_ob['DDO'].values else "Unknown"

            for month in months:
                # Calculations
                t_m = df_t[(df_t['DDO'] == ddo) & (df_t['trans_clean'].dt.strftime('%Y-%m') == month)]
                l_curr = df_l[(df_l['DDO'] == ddo) & (df_l['Scroll Date'].dt.strftime('%Y-%m') == month) & (df_l['cheque_clean'].dt.strftime('%Y-%m') == month)]
                l_prev = df_l[(df_l['DDO'] == ddo) & (df_l['Scroll Date'].dt.strftime('%Y-%m') == month) & (df_l['cheque_clean'].dt.strftime('%Y-%m') < month)]

                unlinked_amt = (current_ob_amt + t_m['Amount'].sum()) - l_curr['Amount'].sum()
                unlinked_cnt = (current_ob_cnt + len(t_m)) - len(l_curr)
                
                closing_amt = unlinked_amt - l_prev['Amount'].sum()
                closing_cnt = unlinked_cnt - len(l_prev)

                final_rows.append({
                    'Month': month, 'DDO': ddo, 'Office': office_name,
                    'Opening_Cnt': current_ob_cnt, 'Opening_Amt': current_ob_amt,
                    'New_Raised_Cnt': len(t_m), 'New_Raised_Amt': t_m['Amount'].sum(),
                    'Closing_Cnt': closing_cnt, 'Closing_Amt': closing_amt
                })
                current_ob_amt, current_ob_cnt = closing_amt, closing_cnt

        report_df = pd.DataFrame(final_rows)
        st.dataframe(report_df)
        
        # Download
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            report_df.to_excel(writer, index=False)
        st.download_button("📥 Download Report", buffer.getvalue(), "SWR_Report.xlsx")
