import streamlit as st
import pandas as pd
from datetime import datetime
import io
import numpy as np

st.set_page_config(page_title="SWR System - Count First", layout="wide")

st.title("🏦 SWR System: Count & Amount (Reordered)")

# --- 1. UPLOAD SECTION ---
with st.expander("📂 STEP 1: UPLOAD YOUR FILES", expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        u_ob = st.file_uploader("1. OB Master (ob.xlsx)", type=['xlsx', 'csv'])
        u_staff = st.file_uploader("2. Staff Mapping (staff mapping.xlsx)", type=['xlsx', 'csv'])
    with c2:
        u_trans = st.file_uploader("3. Transactions (transaction report.xlsx)", type=['xlsx', 'csv'])
        u_linked = st.file_uploader("4. Linked Report (linked report correct.xlsx)", type=['xlsx', 'csv'])

# --- 2. PROCESSING ENGINE ---
if all([u_ob, u_staff, u_trans, u_linked]):
    def load(f): 
        return pd.read_csv(f) if f.name.endswith('.csv') else pd.read_excel(f)

    df_ob = load(u_ob)
    df_staff = load(u_staff)
    df_t = load(u_trans)
    df_l = load(u_linked)

    # --- SIDEBAR CONFIG ---
    st.sidebar.header("📅 Report Settings")
    date_range = st.sidebar.date_input("Select Range", value=(datetime(2025, 7, 1), datetime(2025, 9, 30)))

    if len(date_range) == 2:
        start_date, end_date = date_range
        
        # Standardize Dates
        df_l['Scroll Date'] = pd.to_datetime(df_l['Scroll Date'], dayfirst=True, errors='coerce')
        chq_col = [c for c in df_l.columns if 'Cheque' in c and 'Date' in c][0]
        df_l['chq_date_clean'] = pd.to_datetime(df_l[chq_col], dayfirst=True, errors='coerce')
        t_date_col = 'Date' if 'Date' in df_t.columns else [c for c in df_t.columns if 'date' in c.lower()][0]
        df_t['trans_date_clean'] = pd.to_datetime(df_t[t_date_col], dayfirst=True, errors='coerce')

        # Selection
        staff_list = sorted(df_staff['Employee_Name'].unique().tolist())
        selected_staff = st.sidebar.selectbox("👤 Select Employee", staff_list)
        my_ddo_list = df_staff[df_staff['Employee_Name'] == selected_staff]['DDO'].tolist()

        months = pd.date_range(start=start_date, end=end_date, freq='MS').strftime('%Y-%m').tolist()
        final_rows = []

        for ddo in my_ddo_list:
            # Initial OB from file
            current_ob_amt = df_ob[df_ob['DDO'] == ddo]['ob_amount'].sum()
            current_ob_cnt = df_ob[df_ob['DDO'] == ddo]['ob_count'].sum()
            office_name = df_ob[df_ob['DDO'] == ddo]['Head Office'].iloc[0] if not df_ob[df_ob['DDO'] == ddo].empty else "Unknown"

            for month in months:
                # 1. New Transactions (Amt & Cnt)
                t_filt = df_t[(df_t['DDO'] == ddo) & (df_t['trans_date_clean'].dt.strftime('%Y-%m') == month)]
                m_raised_amt = t_filt['Amount'].sum()
                m_raised_cnt = t_filt.shape[0]

                # 2. Linked Logic (Current)
                l_curr = df_l[(df_l['DDO'] == ddo) & (df_l['Scroll Date'].dt.strftime('%Y-%m') == month) & (df_l['chq_date_clean'].dt.strftime('%Y-%m') == month)]
                curr_l_amt = l_curr['Transaction Amount'].sum()
                curr_l_cnt = l_curr.shape[0]

                # 3. Linked Logic (Previous)
                l_prev = df_l[(df_l['DDO'] == ddo) & (df_l['Scroll Date'].dt.strftime('%Y-%m') == month) & (df_l['chq_date_clean'].dt.strftime('%Y-%m') < month)]
                prev_l_amt = l_prev['Transaction Amount'].sum()
                prev_l_cnt = l_prev.shape[0]

                # 4. Math
                unlinked_amt = (current_ob_amt + m_raised_amt) - curr_l_amt
                unlinked_cnt = (current_ob_cnt + m_raised_cnt) - curr_l_cnt
                
                closing_amt = unlinked_amt - prev_l_amt
                closing_cnt = unlinked_cnt - prev_l_cnt

                final_rows.append({
                    'Month': datetime.strptime(month, '%Y-%m').strftime('%B %Y'),
                    'DDO': ddo,
                    'Office': office_name,
                    'Opening_Cnt': current_ob_cnt,
                    'Opening_Amt': current_ob_amt,
                    'New_Raised_Cnt': m_raised_cnt,
                    'New_Raised_Amt': m_raised_amt,
                    'Curr_Linked_Cnt': curr_l_cnt,
                    'Curr_Linked_Amt': curr_l_amt,
                    'Unlinked_Cnt': unlinked_cnt,
                    'Unlinked_Amt': unlinked_amt,
                    'Prev_Linked_Cnt': prev_l_cnt,
                    'Prev_Linked_Amt': prev_l_amt,
                    'Closing_Cnt': closing_cnt,
                    'Closing_Amt': closing_amt
                })
                current_ob_amt = closing_amt
                current_ob_cnt = closing_cnt

        report_df = pd.DataFrame(final_rows)
        
        # Summary with Count before Amount
        summary_df = report_df.groupby('DDO').last().reset_index()[['DDO', 'Office', 'Closing_Cnt', 'Closing_Amt']]

        # --- DYNAMIC COLOR LOGIC ---
        def apply_heatmap(val, series):
            if val <= series.quantile(0.4): return 'background-color: #d4edda;'
            elif val <= series.quantile(0.8): return 'background-color: #fff3cd;'
            else: return 'background-color: #f8d7da; font-weight: bold;'

        # --- DISPLAY ---
        st.subheader(f"📊 Report for {selected_staff}")
        t1, t2 = st.tabs(["📑 Details (Count First)", "🎯 Final Summary"])
        
        with t1:
            st.dataframe(report_df, use_container_width=True)
        
        with t2:
            styled_summary = summary_df.style.apply(
                lambda x: [apply_heatmap(v, summary_df['Closing_Amt']) for v in x], 
                subset=['Closing_Amt']
            ).format(precision=2)
            st.dataframe(styled_summary, use_container_width=True)

        # --- EXPORT ---
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            report_df.to_excel(writer, index=False, sheet_name='Monthly_Breakup')
            summary_df.to_excel(writer, index=False, sheet_name='DDO_Summary')
        
        st.download_button("📥 Download Finalized Report", buffer.getvalue(), f"SWR_{selected_staff}.xlsx")
else:
    st.info("Please upload files to proceed.")