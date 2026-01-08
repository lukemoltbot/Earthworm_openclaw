import lasio
import pandas as pd
import numpy as np
from .config import INVALID_DATA_VALUE

class DataProcessor:
    def __init__(self):
        pass

    def load_las_file(self, file_path):
        """
        Loads a .las file and extracts curve data and mnemonics.

        Args:
            file_path (str): The path to the .las file.

        Returns:
            tuple: A tuple containing:
                - pandas.DataFrame: DataFrame with all curve data.
                - list: List of string names of all curve mnemonics.
        """
        las = lasio.read(file_path)
        
        # Extract data and mnemonics to build DataFrame with correct column names
        data = {curve.mnemonic: curve.data for curve in las.curves}
        df = pd.DataFrame(data)

        # Set the depth curve as the index. Try to find a common depth mnemonic.
        depth_mnemonic = None
        common_depth_mnemonics = ['DEPT', 'DEPTH', 'MD'] # Common depth mnemonics
        for curve in las.curves:
            if curve.mnemonic.upper() in common_depth_mnemonics:
                depth_mnemonic = curve.mnemonic
                break
        if depth_mnemonic is None and las.curves:
            # Fallback: assume the first curve is depth if no common mnemonic found
            depth_mnemonic = las.curves[0].mnemonic

        if depth_mnemonic and depth_mnemonic in df.columns:
            df = df.set_index(depth_mnemonic)
            df.index.name = 'DEPT' # Standardize index name to DEPT as used in main_window.py
            df = df.reset_index() # Reset index to make DEPT a regular column for consistency
        else:
            print(f"Warning: Could not determine depth mnemonic. DataFrame index might not be depth.")
            df = df.reset_index() # Ensure index is reset even if depth not found

        mnemonics = [curve.mnemonic for curve in las.curves]
        return df, mnemonics

    def preprocess_data(self, dataframe, mnemonic_map): # Removed null_value parameter
        """
        Preprocesses the raw DataFrame by replacing null values and creating standardized columns.

        Args:
            dataframe (pandas.DataFrame): The raw DataFrame from load_las_file.
            mnemonic_map (dict): A dictionary mapping standardized names to original mnemonics
                                 (e.g., {'gamma': 'GR', 'density': 'RHOB'}).

        Returns:
            pandas.DataFrame: The processed DataFrame with standardized columns and np.nan for nulls.
        """
        # Replace specified null_value with NaN
        processed_df = dataframe.replace(INVALID_DATA_VALUE, np.nan) # Used INVALID_DATA_VALUE from config

        # Create standardized columns based on mnemonic_map
        for standard_name, original_mnemonic in mnemonic_map.items():
            if original_mnemonic in processed_df.columns:
                processed_df[standard_name] = processed_df[original_mnemonic]
            else:
                # If the original mnemonic is not found, create a column of NaNs
                processed_df[standard_name] = np.nan
                print(f"Warning: Mnemonic '{original_mnemonic}' not found in DataFrame for standard name '{standard_name}'.")

        return processed_df
