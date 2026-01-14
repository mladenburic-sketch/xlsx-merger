import streamlit as st
import pandas as pd
from pathlib import Path
import io
from src.file_analyzer import FileAnalyzer
from src.merger import DataMerger

st.set_page_config(
    page_title="CSV/XLSX Merger",
    page_icon="🔀",
    layout="wide"
)

st.title("🔀 CSV/XLSX Merger")
st.markdown("Upload a CSV or XLSX file, analyze its structure, and merge two sheets using common columns.")

# Initialize session state
if 'uploaded_file' not in st.session_state:
    st.session_state.uploaded_file = None
if 'file_info' not in st.session_state:
    st.session_state.file_info = None
if 'merged_data' not in st.session_state:
    st.session_state.merged_data = None

# File upload section
st.header("📤 Step 1: Upload File")
uploaded_file = st.file_uploader(
    "Choose a CSV or XLSX file",
    type=['csv', 'xlsx'],
    help="Upload a CSV file or an XLSX file with multiple sheets"
)

if uploaded_file is not None:
    st.session_state.uploaded_file = uploaded_file
    
    # Analyze the file
    analyzer = FileAnalyzer()
    
    with st.spinner("Analyzing file structure..."):
        file_info = analyzer.analyze_file(uploaded_file)
        st.session_state.file_info = file_info
    
    # Display file information
    st.header("📊 Step 2: File Structure")
    
    if file_info['type'] == 'xlsx':
        st.success(f"✅ XLSX file detected with {len(file_info['sheets'])} sheet(s)")
        
        # Display sheets and their columns
        for sheet_name, columns in file_info['sheets'].items():
            with st.expander(f"📄 Sheet: **{sheet_name}** ({len(columns)} columns)"):
                st.write("**Columns:**", ", ".join(columns))
                st.write(f"**Number of rows:** {file_info['row_counts'][sheet_name]}")
    else:
        st.success(f"✅ CSV file detected")
        with st.expander("📄 CSV File Details"):
            st.write("**Columns:**", ", ".join(file_info['sheets']['Sheet1']))
            st.write(f"**Number of rows:** {file_info['row_counts']['Sheet1']}")
    
    # Merge configuration
    st.header("🔗 Step 3: Configure Merge")
    
    if file_info['type'] == 'xlsx' and len(file_info['sheets']) < 2:
        st.warning("⚠️ XLSX file must contain at least 2 sheets to merge. Please upload a file with multiple sheets.")
    elif file_info['type'] == 'csv':
        st.warning("⚠️ CSV files contain only one sheet. Please upload an XLSX file with multiple sheets to merge.")
    else:
        # Sheet selection
        sheet_names = list(file_info['sheets'].keys())
        
        col1, col2 = st.columns(2)
        
        with col1:
            left_sheet = st.selectbox(
                "Select first sheet (left):",
                sheet_names,
                key="left_sheet"
            )
        
        with col2:
            # Filter out the selected left sheet
            right_sheet_options = [s for s in sheet_names if s != left_sheet]
            right_sheet = st.selectbox(
                "Select second sheet (right):",
                right_sheet_options,
                key="right_sheet"
            )
        
        # Get columns from both sheets
        left_columns = file_info['sheets'][left_sheet]
        right_columns = file_info['sheets'][right_sheet]
        common_columns = [col for col in left_columns if col in right_columns]
        
        # Show common columns info
        if common_columns:
            st.info(f"ℹ️ Found {len(common_columns)} common column(s): {', '.join(common_columns)}")
        
        # Column selection for merge
        st.subheader("Select Merge Columns")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Columns from '{left_sheet}':**")
            left_merge_columns = st.multiselect(
                "Select column(s) from left sheet:",
                left_columns,
                default=common_columns[0] if common_columns else None,
                help="Select one or more columns from the left sheet to use for merging.",
                key="left_merge_cols"
            )
        
        with col2:
            st.write(f"**Columns from '{right_sheet}':**")
            right_merge_columns = st.multiselect(
                "Select column(s) from right sheet:",
                right_columns,
                default=common_columns[0] if common_columns else None,
                help="Select one or more columns from the right sheet to use for merging.",
                key="right_merge_cols"
            )
        
        # Validate column selection
        if left_merge_columns and right_merge_columns:
            if len(left_merge_columns) != len(right_merge_columns):
                st.warning("⚠️ Number of selected columns must match between left and right sheets.")
            else:
                # Show column mapping
                st.write("**Column mapping:**")
                mapping_text = " | ".join([f"{left} ↔ {right}" for left, right in zip(left_merge_columns, right_merge_columns)])
                st.code(mapping_text)
        
        # Prepare merge columns for the merger
        merge_columns = {
            'left': left_merge_columns,
            'right': right_merge_columns
        }
        
        # Matching mode selection
        st.subheader("Matching Options")
        matching_mode = st.radio(
            "Matching mode:",
            ["Exact Match", "Substring Match"],
            help="Exact Match: values must match exactly. Substring Match: one value contains the other as a substring.",
            horizontal=True
        )
        
        substring_direction = None
        if matching_mode == "Substring Match":
            substring_direction = st.radio(
                "Substring direction:",
                ["Left contains Right", "Right contains Left"],
                help="Left contains Right: left column value contains right column value. Right contains Left: right column value contains left column value.",
                horizontal=True
            )
        
        # Merge type selection
        merge_type = st.radio(
            "Merge type:",
            ["Inner Join", "Left Join", "Right Join", "Outer Join"],
            help="Inner: only matching rows, Left: all rows from left sheet, Right: all rows from right sheet, Outer: all rows from both sheets"
        )
        
        # Perform merge
        if st.button("🔄 Perform Merge", type="primary"):
            if not left_merge_columns or not right_merge_columns:
                st.error("❌ Please select at least one column from each sheet to merge on.")
            elif len(left_merge_columns) != len(right_merge_columns):
                st.error("❌ Number of selected columns must match between left and right sheets.")
            else:
                merger = DataMerger()
                
                # Convert matching mode to internal format
                matching_mode_internal = 'substring' if matching_mode == "Substring Match" else 'exact'
                substring_direction_internal = None
                if matching_mode_internal == 'substring':
                    substring_direction_internal = 'left_contains_right' if substring_direction == "Left contains Right" else 'right_contains_left'
                
                with st.spinner("Merging sheets..."):
                    try:
                        # Show progress for substring matching
                        progress_bar = None
                        status_text = None
                        if matching_mode_internal == 'substring':
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            status_text.text("Preparing data...")
                            
                            def update_progress(percent):
                                if progress_bar:
                                    progress_bar.progress(percent)
                                    if percent < 50:
                                        status_text.text(f"Finding exact matches... {percent}%")
                                    else:
                                        status_text.text(f"Finding substring matches... {percent}%")
                        else:
                            def update_progress(percent):
                                pass
                        
                        merged_df = merger.merge_sheets(
                            uploaded_file,
                            left_sheet,
                            right_sheet,
                            merge_columns,
                            merge_type,
                            file_info['type'],
                            matching_mode=matching_mode_internal,
                            substring_direction=substring_direction_internal,
                            progress_callback=update_progress if matching_mode_internal == 'substring' else None
                        )
                        
                        if matching_mode_internal == 'substring' and progress_bar:
                            progress_bar.progress(100)
                            status_text.text("Merge completed!")
                        st.session_state.merged_data = merged_df
                        if len(merged_df) == 0:
                            st.warning("⚠️ No rows matched! Please check:")
                            st.write("- **Substring direction**: Try switching between 'Left contains Right' and 'Right contains Left'")
                            st.write("- **Column selection**: Verify the selected columns contain the values you want to match")
                            st.write("- **Data format**: Ensure one column value is actually a substring of the other")
                            if matching_mode == "Substring Match":
                                st.write("- **Sample values**: Check if values like 'ABC123' appear within values like 'ABC123XYZ' (or vice versa)")
                        else:
                            st.success(f"✅ Merge completed! Result has {len(merged_df)} rows and {len(merged_df.columns)} columns.")
                    except Exception as e:
                        st.error(f"❌ Error during merge: {str(e)}")
        
        # Display merged data
        if st.session_state.merged_data is not None:
            st.header("📋 Step 4: Merged Data Preview")
            
            st.dataframe(st.session_state.merged_data, use_container_width=True)
            
            # Download section
            st.header("💾 Step 5: Download Merged Data")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # CSV download
                csv_buffer = io.StringIO()
                st.session_state.merged_data.to_csv(csv_buffer, index=False)
                st.download_button(
                    label="📥 Download as CSV",
                    data=csv_buffer.getvalue(),
                    file_name="merged_data.csv",
                    mime="text/csv"
                )
            
            with col2:
                # XLSX download
                xlsx_buffer = io.BytesIO()
                with pd.ExcelWriter(xlsx_buffer, engine='openpyxl') as writer:
                    st.session_state.merged_data.to_excel(writer, index=False, sheet_name='Merged')
                st.download_button(
                    label="📥 Download as XLSX",
                    data=xlsx_buffer.getvalue(),
                    file_name="merged_data.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

else:
    st.info("👆 Please upload a CSV or XLSX file to get started.")
