"""
Data merger module for merging sheets from CSV/XLSX files.
"""
import pandas as pd
import io
import re
from typing import List, Optional


class DataMerger:
    """Handles merging of data from different sheets."""
    
    def merge_sheets(
        self,
        uploaded_file,
        left_sheet: str,
        right_sheet: str,
        merge_columns: dict,
        merge_type: str,
        file_type: str,
        matching_mode: str = 'exact',
        substring_direction: str = 'left_contains_right'
    ) -> pd.DataFrame:
        """
        Merge two sheets based on specified columns.
        
        Args:
            uploaded_file: Streamlit uploaded file object
            left_sheet: Name of the left sheet
            right_sheet: Name of the right sheet
            merge_columns: Dictionary with 'left' and 'right' keys containing lists of column names
            merge_type: Type of merge (Inner Join, Left Join, Right Join, Outer Join)
            file_type: Type of file ('csv' or 'xlsx')
            matching_mode: 'exact' for exact matching, 'substring' for substring matching
            substring_direction: 'left_contains_right' or 'right_contains_left' (only used for substring mode)
            
        Returns:
            Merged DataFrame
        """
        uploaded_file.seek(0)
        
        if file_type == 'csv':
            # For CSV, both sheets are actually the same file
            # This shouldn't happen in normal flow, but handle it gracefully
            df_left = pd.read_csv(uploaded_file)
            uploaded_file.seek(0)
            df_right = pd.read_csv(uploaded_file)
        else:
            # Read XLSX sheets
            df_left = pd.read_excel(
                uploaded_file,
                sheet_name=left_sheet,
                engine='openpyxl'
            )
            uploaded_file.seek(0)
            df_right = pd.read_excel(
                uploaded_file,
                sheet_name=right_sheet,
                engine='openpyxl'
            )
        
        # Map merge type to pandas how parameter
        merge_type_map = {
            'Inner Join': 'inner',
            'Left Join': 'left',
            'Right Join': 'right',
            'Outer Join': 'outer'
        }
        
        how = merge_type_map.get(merge_type, 'inner')
        
        left_cols = merge_columns['left']
        right_cols = merge_columns['right']
        
        # Handle substring matching
        if matching_mode == 'substring':
            merged_df = self._merge_with_substring(
                df_left, df_right, left_cols, right_cols, 
                how, substring_direction
            )
        else:
            # Exact matching - original logic
            # If columns have the same names, use 'on' parameter
            # Otherwise, use 'left_on' and 'right_on'
            if left_cols == right_cols:
                # Same column names - simple merge
                merged_df = pd.merge(
                    df_left,
                    df_right,
                    on=left_cols,
                    how=how,
                    suffixes=('_left', '_right')
                )
            else:
                # Different column names - use left_on and right_on
                merged_df = pd.merge(
                    df_left,
                    df_right,
                    left_on=left_cols,
                    right_on=right_cols,
                    how=how,
                    suffixes=('_left', '_right')
                )
        
        return merged_df
    
    def _merge_with_substring(
        self,
        df_left: pd.DataFrame,
        df_right: pd.DataFrame,
        left_cols: List[str],
        right_cols: List[str],
        how: str,
        substring_direction: str
    ) -> pd.DataFrame:
        """
        Merge dataframes using substring matching.
        
        Args:
            df_left: Left dataframe
            df_right: Right dataframe
            left_cols: List of column names from left dataframe
            right_cols: List of column names from right dataframe
            how: Merge type ('inner', 'left', 'right', 'outer')
            substring_direction: 'left_contains_right' or 'right_contains_left'
            
        Returns:
            Merged DataFrame
        """
        # Convert all merge columns to string for comparison
        df_left = df_left.copy()
        df_right = df_right.copy()
        
        # Create composite keys by concatenating multiple columns if needed
        # Handle NaN values and convert to string, then strip whitespace
        def clean_key(value):
            """Clean and normalize key values for comparison."""
            if pd.isna(value):
                return ''
            s = str(value).strip()
            # Handle pandas NaN string representation
            if s.lower() in ['nan', 'none', '']:
                return ''
            return s
        
        def extract_numeric_part(value_str):
            """Extract numeric part from a string (e.g., 'OE00012345' -> '12345')."""
            # Find all sequences of digits
            numbers = re.findall(r'\d+', value_str)
            if numbers:
                # Return the longest numeric sequence (most likely the main number)
                return max(numbers, key=len)
            return ''
        
        def normalize_for_matching(value):
            """Normalize value for matching - extract numeric part if it's a string with numbers."""
            cleaned = clean_key(value)
            if not cleaned:
                return ''
            # If it's already a pure number (after cleaning), return as is
            if cleaned.isdigit():
                return cleaned
            # Otherwise, try to extract numeric part
            numeric_part = extract_numeric_part(cleaned)
            # If we found a numeric part, use it; otherwise use the full string
            return numeric_part if numeric_part else cleaned
        
        if len(left_cols) == 1:
            df_left['_merge_key_left'] = df_left[left_cols[0]].apply(normalize_for_matching)
        else:
            df_left['_merge_key_left'] = df_left[left_cols].apply(
                lambda row: '|'.join([normalize_for_matching(val) for val in row]), axis=1
            )
        
        if len(right_cols) == 1:
            df_right['_merge_key_right'] = df_right[right_cols[0]].apply(normalize_for_matching)
        else:
            df_right['_merge_key_right'] = df_right[right_cols].apply(
                lambda row: '|'.join([normalize_for_matching(val) for val in row]), axis=1
            )
        
        # Reset index to ensure we have sequential indices
        df_left = df_left.reset_index(drop=True)
        df_right = df_right.reset_index(drop=True)
        
        # Also store original cleaned values for substring matching
        if len(left_cols) == 1:
            df_left['_original_left'] = df_left[left_cols[0]].apply(clean_key)
        else:
            df_left['_original_left'] = df_left[left_cols].apply(
                lambda row: '|'.join([clean_key(val) for val in row]), axis=1
            )
        
        if len(right_cols) == 1:
            df_right['_original_right'] = df_right[right_cols[0]].apply(clean_key)
        else:
            df_right['_original_right'] = df_right[right_cols].apply(
                lambda row: '|'.join([clean_key(val) for val in row]), axis=1
            )
        
        # Create a mapping based on substring matching
        matches = []
        
        if substring_direction == 'left_contains_right':
            # Left column contains right column value
            for idx_left, left_key in enumerate(df_left['_merge_key_left']):
                if not left_key:  # Skip empty keys
                    continue
                left_key_lower = left_key.lower()
                left_original = df_left.loc[idx_left, '_original_left'].lower()
                
                for idx_right, right_key in enumerate(df_right['_merge_key_right']):
                    if not right_key:  # Skip empty keys
                        continue
                    right_key_lower = right_key.lower()
                    right_original = df_right.loc[idx_right, '_original_right'].lower()
                    
                    # Check multiple matching strategies:
                    # 1. Normalized keys match exactly (handles number extraction)
                    # 2. Normalized right_key is substring of normalized left_key
                    # 3. Original right_original is substring of original left_original
                    if (left_key == right_key or  # Exact match after normalization
                        right_key_lower in left_key_lower or  # Normalized substring
                        right_original in left_original):  # Original substring
                        matches.append({
                            'left_idx': idx_left,
                            'right_idx': idx_right
                        })
        else:  # right_contains_left
            # Right column contains left column value
            for idx_left, left_key in enumerate(df_left['_merge_key_left']):
                if not left_key:  # Skip empty keys
                    continue
                left_key_lower = left_key.lower()
                left_original = df_left.loc[idx_left, '_original_left'].lower()
                
                for idx_right, right_key in enumerate(df_right['_merge_key_right']):
                    if not right_key:  # Skip empty keys
                        continue
                    right_key_lower = right_key.lower()
                    right_original = df_right.loc[idx_right, '_original_right'].lower()
                    
                    # Check multiple matching strategies:
                    # 1. Normalized keys match exactly (handles number extraction)
                    # 2. Normalized left_key is substring of normalized right_key
                    # 3. Original left_original is substring of original right_original
                    if (left_key == right_key or  # Exact match after normalization
                        left_key_lower in right_key_lower or  # Normalized substring
                        left_original in right_original):  # Original substring
                        matches.append({
                            'left_idx': idx_left,
                            'right_idx': idx_right
                        })
        
        if not matches:
            # No matches found
            if how == 'outer':
                # Return all rows from both dataframes with NaN for missing values
                df_left['_merge_key'] = df_left['_merge_key_left']
                df_right['_merge_key'] = df_right['_merge_key_right']
                merged_df = pd.merge(
                    df_left.drop(columns=['_merge_key_left']),
                    df_right.drop(columns=['_merge_key_right']),
                    left_on='_merge_key',
                    right_on='_merge_key',
                    how='outer',
                    suffixes=('_left', '_right')
                )
                merged_df = merged_df.drop(columns=['_merge_key'])
            else:
                # Return empty dataframe with combined columns
                all_cols = list(df_left.columns) + [col for col in df_right.columns if col not in df_left.columns]
                all_cols = [col for col in all_cols if not col.startswith('_merge_key')]
                merged_df = pd.DataFrame(columns=all_cols)
            return merged_df
        
        # Create a mapping dataframe
        matches_df = pd.DataFrame(matches)
        
        # Remove duplicates - if multiple matches, take the first one
        # For left join, keep all left rows; for right join, keep all right rows
        if how in ['left', 'outer']:
            # Keep first match for each left row
            matches_df = matches_df.drop_duplicates(subset=['left_idx'], keep='first')
        elif how in ['right', 'outer']:
            # Keep first match for each right row
            matches_df = matches_df.drop_duplicates(subset=['right_idx'], keep='first')
        else:  # inner
            # Keep first match for each left row (can be modified if needed)
            matches_df = matches_df.drop_duplicates(subset=['left_idx'], keep='first')
        
        # Perform the merge based on the matches
        if how == 'inner':
            # Only matched rows
            merged_df = df_left.merge(
                matches_df, left_index=True, right_on='left_idx', how='inner'
            ).merge(
                df_right, left_on='right_idx', right_index=True, how='inner', suffixes=('_left', '_right')
            )
        elif how == 'left':
            # All left rows, matched right rows
            merged_df = df_left.merge(
                matches_df, left_index=True, right_on='left_idx', how='left'
            ).merge(
                df_right, left_on='right_idx', right_index=True, how='left', suffixes=('_left', '_right')
            )
        elif how == 'right':
            # All right rows, matched left rows
            merged_df = df_right.merge(
                matches_df, left_index=True, right_on='right_idx', how='left'
            ).merge(
                df_left, left_on='left_idx', right_index=True, how='left', suffixes=('_right', '_left')
            )
        else:  # outer
            # All rows from both
            # First merge left with matches
            left_merged = df_left.merge(
                matches_df, left_index=True, right_on='left_idx', how='left'
            )
            # Then merge with right
            merged_df = left_merged.merge(
                df_right, left_on='right_idx', right_index=True, how='outer', suffixes=('_left', '_right')
            )
        
        # Clean up temporary columns
        cols_to_drop = ['_merge_key_left', '_merge_key_right', '_original_left', '_original_right', 'left_idx', 'right_idx']
        cols_to_drop = [col for col in cols_to_drop if col in merged_df.columns]
        merged_df = merged_df.drop(columns=cols_to_drop)
        
        # Reset index
        merged_df = merged_df.reset_index(drop=True)
        
        return merged_df
