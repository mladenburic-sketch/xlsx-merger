"""
File analyzer module for detecting file structure, sheets, and columns.
"""
import pandas as pd
import io
from typing import Dict, List, Any


class FileAnalyzer:
    """Analyzes uploaded files to detect structure, sheets, and columns."""
    
    def analyze_file(self, uploaded_file) -> Dict[str, Any]:
        """
        Analyze an uploaded file to extract structure information.
        
        Args:
            uploaded_file: Streamlit uploaded file object
            
        Returns:
            Dictionary containing file type, sheets, columns, and row counts
        """
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        # Reset file pointer
        uploaded_file.seek(0)
        
        if file_extension == 'csv':
            return self._analyze_csv(uploaded_file)
        elif file_extension == 'xlsx':
            return self._analyze_xlsx(uploaded_file)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
    
    def _analyze_csv(self, uploaded_file) -> Dict[str, Any]:
        """Analyze CSV file structure."""
        uploaded_file.seek(0)
        
        # Read CSV to get columns
        df = pd.read_csv(uploaded_file)
        columns = df.columns.tolist()
        row_count = len(df)
        
        return {
            'type': 'csv',
            'sheets': {
                'Sheet1': columns
            },
            'row_counts': {
                'Sheet1': row_count
            }
        }
    
    def _analyze_xlsx(self, uploaded_file) -> Dict[str, Any]:
        """Analyze XLSX file structure."""
        uploaded_file.seek(0)
        
        # Read all sheets
        excel_file = pd.ExcelFile(uploaded_file, engine='openpyxl')
        sheet_names = excel_file.sheet_names
        
        sheets_info = {}
        row_counts = {}
        
        for sheet_name in sheet_names:
            df = pd.read_excel(excel_file, sheet_name=sheet_name, engine='openpyxl')
            columns = df.columns.tolist()
            row_count = len(df)
            
            sheets_info[sheet_name] = columns
            row_counts[sheet_name] = row_count
        
        return {
            'type': 'xlsx',
            'sheets': sheets_info,
            'row_counts': row_counts
        }
