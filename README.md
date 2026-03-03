This automated tool is designed for staff to prepare SWR (Statement of Wise Reconciliation) reports at a stretch for multiple months. It calculates opening balances, new transactions, and linked (cleared) items while providing a visual "Heatmap" to identify high-risk unlinked amounts.
🚀 How to Use the App

    Access the Tool: Open the Streamlit link provided by the administrator.

    Upload Files: Upload the 4 required Excel files (see formatting below).

    Select Settings:

        Choose your name from the Select Employee dropdown.

        Select the Date Range (e.g., July 1st to Sept 30th).

    Review Results:

        Detailed View: Month-by-month breakup of every DDO.

        Summary Sheet: Final closing balances with Color Coding (🔴 High, 🟠 Medium, 🟢 Low).

    Download: Export the results to a professional, multi-sheet Excel file.

📂 Required File Formatting

To ensure the system works correctly, your Excel/CSV files must contain these specific column headers:
1. OB Master (ob.xlsx)
Column Name	Description
DDO	The unique Office Code.
ob_count	Number of pending items at the start date.
ob_amount	Total value of pending items at the start date.
Head Office	Name of the office.
2. Staff Mapping (staff mapping.xlsx)
Column Name	Description
Employee_Name	The name that will appear in the dropdown.
DDO	The Office Code assigned to that staff member.
3. Transaction Report (transaction report.xlsx)
Column Name	Description
DDO	The Office Code.
Date	Date of the transaction.
Amount	The value of the transaction.
4. Linked Report (linked report.xlsx)
Column Name	Description
DDO	The Office Code.
Scroll Date	The date the item was cleared/scrolled.
Cheque/Trans Date	The original date of the cheque.
Transaction Amount	The cleared amount.
⚖️ Calculation Logic

The system follows standard accounting principles for the "stretch" report:

    Unlinked Amount = (Opening + New Raised) - Current Month Linked.

    Closing Balance = Unlinked - Previous Month Linked (Old items cleared).

    Carry Forward: The Closing Balance of Month 1 automatically becomes the Opening Balance of Month 2.

🚩 Risk Heatmap

The summary table uses Relative Percentiles to help you prioritize your work:

    🔴 RED (Top 20%): High unlinked amounts. Requires immediate reconciliation.

    🟠 ORANGE (Middle 40%): Moderate unlinked amounts.

    🟢 GREEN (Bottom 40%): Well-managed or low-value unlinked amounts.
