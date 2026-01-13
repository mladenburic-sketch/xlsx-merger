# CSV/XLSX Merger

A Streamlit application for merging sheets from CSV or XLSX files based on common columns.

## Features

- 📤 Upload CSV or XLSX files
- 📊 Analyze file structure (sheets and columns)
- 🔗 Merge two sheets using one or more common columns
- 🔄 Support for different merge types (Inner, Left, Right, Outer Join)
- 💾 Download merged data as CSV or XLSX

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the Streamlit app:
```bash
streamlit run app.py
```

2. Upload a CSV or XLSX file
3. Review the file structure (sheets and columns)
4. Select two sheets to merge
5. Choose the column(s) to merge on
6. Select the merge type
7. Perform the merge and download the result

## Requirements

- Python 3.8+
- Streamlit
- Pandas
- openpyxl (for XLSX support)
