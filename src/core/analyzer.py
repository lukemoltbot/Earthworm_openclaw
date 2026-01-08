import pandas as pd
import numpy as np
import openpyxl
import os
import shutil
import logging

from .config import DEPTH_COLUMN, LITHOLOGY_COLUMN, ANALYSIS_COLUMNS, RESEARCHED_LITHOLOGY_DEFAULTS, INVALID_DATA_VALUE, DEFAULT_MERGE_THRESHOLD

# Set up logging
logger = logging.getLogger(__name__)

class Analyzer:
    def __init__(self):
        pass

    def classify_rows(self, dataframe, lithology_rules, mnemonic_map, use_researched_defaults=True):
        """
        Classifies rows in the DataFrame based on lithology rules, using specified mnemonics.

        Args:
            dataframe (pandas.DataFrame): The preprocessed DataFrame.
            lithology_rules (list): A list of dictionaries, each defining a lithology rule.
            mnemonic_map (dict): A dictionary mapping standardized names to original mnemonics
                                 (e.g., {'gamma': 'GR', 'density': 'RHOB', 'short_space_density': 'DENS', 'long_space_density': 'LSD'}).

        Returns:
            pandas.DataFrame: The DataFrame with a new 'LITHOLOGY_CODE' column.
        """
        classified_df = dataframe.copy()
        classified_df[LITHOLOGY_COLUMN] = 'NL'

        # Determine which columns to use for gamma and density based on mnemonic_map
        gamma_col_name = 'gamma' # Standardized name for gamma
        
        # Prioritize 'density', then 'short_space_density', then 'long_space_density'
        density_col_name = None
        if 'density' in mnemonic_map and mnemonic_map['density'] in classified_df.columns:
            density_col_name = 'density'
        elif 'short_space_density' in mnemonic_map and mnemonic_map['short_space_density'] in classified_df.columns:
            density_col_name = 'short_space_density'
        elif 'long_space_density' in mnemonic_map and mnemonic_map['long_space_density'] in classified_df.columns:
            density_col_name = 'long_space_density'
        
        if gamma_col_name not in classified_df.columns:
            logger.warning(f"Gamma column '{gamma_col_name}' not found in DataFrame. Classification may be inaccurate.")
            return classified_df # Cannot classify without gamma
        
        if density_col_name is None:
            logger.warning("No suitable density column found in DataFrame for classification. Classification may be inaccurate.")
            return classified_df # Cannot classify without density

        for rule in lithology_rules:
            name = rule.get('name')
            code = rule.get('code')
            
            # Get current rule values
            gamma_min = rule.get('gamma_min')
            gamma_max = rule.get('gamma_max')
            density_min = rule.get('density_min')
            density_max = rule.get('density_max')

            # Skip rule if it's for 'Not Logged' as it's a default classification
            if code == 'NL':
                continue

            # Determine if parameters are marked as "don't care" (both min and max are INVALID_DATA_VALUE)
            gamma_ignore = (gamma_min == INVALID_DATA_VALUE and gamma_max == INVALID_DATA_VALUE)
            density_ignore = (density_min == INVALID_DATA_VALUE and density_max == INVALID_DATA_VALUE)

            # Handle gamma and density ranges based on user preference for researched defaults
            if code in RESEARCHED_LITHOLOGY_DEFAULTS:
                researched_defaults = RESEARCHED_LITHOLOGY_DEFAULTS[code]

                if use_researched_defaults:
                    # Apply gamma defaults if current rule's gamma range is don't care OR zero
                    gamma_missing = gamma_ignore or (gamma_min == 0.0 and gamma_max == 0.0)
                    if gamma_missing and 'gamma_min' in researched_defaults and 'gamma_max' in researched_defaults:
                        gamma_min = researched_defaults['gamma_min']
                        gamma_max = researched_defaults['gamma_max']
                        gamma_ignore = False  # No longer ignore this parameter
                        logger.debug(f"Applying researched gamma defaults for {code}: {gamma_min}-{gamma_max}")

                    # Apply density defaults if current rule's density range is don't care OR zero
                    density_missing = density_ignore or (density_min == 0.0 and density_max == 0.0)
                    if density_missing and 'density_min' in researched_defaults and 'density_max' in researched_defaults:
                        density_min = researched_defaults['density_min']
                        density_max = researched_defaults['density_max']
                        density_ignore = False  # No longer ignore this parameter
                        logger.debug(f"Applying researched density defaults for {code}: {density_min}-{density_max}")

            # Create a boolean mask for rows that are not yet classified
            unclassified_mask = (classified_df[LITHOLOGY_COLUMN] == 'NL')

            # Create conditions for gamma and density, handling "don't care" markers
            gamma_condition = ((classified_df[gamma_col_name] >= gamma_min) & (classified_df[gamma_col_name] <= gamma_max)) if not gamma_ignore else True
            density_condition = ((classified_df[density_col_name] >= density_min) & (classified_df[density_col_name] <= density_max)) if not density_ignore else True

            # Create a boolean mask for the current rule
            rule_mask = gamma_condition & density_condition

            # Apply the rule only to unclassified rows that match the rule criteria
            classified_df.loc[unclassified_mask & rule_mask, LITHOLOGY_COLUMN] = code

        return classified_df

    def classify_rows_simple(self, dataframe, lithology_rules, mnemonic_map):
        """
        Classifies rows using the Simple method: first by density only, then by gamma only.
        
        Args:
            dataframe (pandas.DataFrame): The preprocessed DataFrame.
            lithology_rules (list): A list of dictionaries, each defining a lithology rule.
            mnemonic_map (dict): A dictionary mapping standardized names to original mnemonics.

        Returns:
            pandas.DataFrame: The DataFrame with a new 'LITHOLOGY_CODE' column.
        """
        classified_df = dataframe.copy()
        classified_df[LITHOLOGY_COLUMN] = 'NL'

        # Determine which columns to use for gamma and density based on mnemonic_map
        gamma_col_name = 'gamma' # Standardized name for gamma
        
        # Prioritize 'density', then 'short_space_density', then 'long_space_density'
        density_col_name = None
        if 'density' in mnemonic_map and mnemonic_map['density'] in classified_df.columns:
            density_col_name = 'density'
        elif 'short_space_density' in mnemonic_map and mnemonic_map['short_space_density'] in classified_df.columns:
            density_col_name = 'short_space_density'
        elif 'long_space_density' in mnemonic_map and mnemonic_map['long_space_density'] in classified_df.columns:
            density_col_name = 'long_space_density'
        
        if gamma_col_name not in classified_df.columns:
            logger.warning(f"Gamma column '{gamma_col_name}' not found in DataFrame. Classification may be inaccurate.")
            return classified_df # Cannot classify without gamma
        
        if density_col_name is None:
            logger.warning("No suitable density column found in DataFrame for classification. Classification may be inaccurate.")
            return classified_df # Cannot classify without density

        # First pass: classify by density only (ignore gamma)
        for rule in lithology_rules:
            name = rule.get('name')
            code = rule.get('code')
            
            # Skip rule if it's for 'Not Logged' as it's a default classification
            if code == 'NL':
                continue

            # Get current rule values
            density_min = rule.get('density_min')
            density_max = rule.get('density_max')

            # Skip rules with invalid density ranges
            if density_min == INVALID_DATA_VALUE and density_max == INVALID_DATA_VALUE:
                continue

            # Create a boolean mask for rows that are not yet classified
            unclassified_mask = (classified_df[LITHOLOGY_COLUMN] == 'NL')

            # Create condition for density only
            density_condition = ((classified_df[density_col_name] >= density_min) & 
                               (classified_df[density_col_name] <= density_max))

            # Apply the rule only to unclassified rows that match the density criteria
            classified_df.loc[unclassified_mask & density_condition, LITHOLOGY_COLUMN] = code

        # Second pass: classify by gamma only (overwrite previous classifications)
        for rule in lithology_rules:
            name = rule.get('name')
            code = rule.get('code')
            
            # Skip rule if it's for 'Not Logged' as it's a default classification
            if code == 'NL':
                continue

            # Get current rule values
            gamma_min = rule.get('gamma_min')
            gamma_max = rule.get('gamma_max')

            # Skip rules with invalid gamma ranges (ignore -999.25 values)
            if gamma_min == INVALID_DATA_VALUE and gamma_max == INVALID_DATA_VALUE:
                continue

            # Create condition for gamma only
            gamma_condition = ((classified_df[gamma_col_name] >= gamma_min) & 
                             (classified_df[gamma_col_name] <= gamma_max))

            # Apply the rule to ALL rows that match the gamma criteria (overwrites previous classifications)
            classified_df.loc[gamma_condition, LITHOLOGY_COLUMN] = code

        return classified_df

    def group_into_units(self, dataframe, lithology_rules):
        """
        Groups contiguous blocks of rows with the same LITHOLOGY_CODE into lithological units.

        Args:
            dataframe (pandas.DataFrame): The classified DataFrame.
            lithology_rules (list): A list of dictionaries, each defining a lithology rule.

        Returns:
            pandas.DataFrame: A DataFrame summarizing the lithological units.
        """
        logger.debug(f"group_into_units: DataFrame columns: {dataframe.columns.tolist()}")
        logger.debug(f"group_into_units: DataFrame index: {dataframe.index.tolist()}")

        if LITHOLOGY_COLUMN not in dataframe.columns:
            raise ValueError(f"DataFrame must contain a '{LITHOLOGY_COLUMN}' column.")
        if DEPTH_COLUMN not in dataframe.columns:
            raise ValueError(f"Depth column '{DEPTH_COLUMN}' not found in DataFrame.")

        units = []
        current_unit = None

        # Create a mapping from lithology code to rule details
        rules_map = {rule['code']: rule for rule in lithology_rules}

        # Ensure the DataFrame is sorted by depth for correct grouping
        sorted_df = dataframe.sort_values(by=DEPTH_COLUMN).reset_index(drop=True)

        for i, row in sorted_df.iterrows():
            lithology_code = row[LITHOLOGY_COLUMN]
            current_depth = row[DEPTH_COLUMN]
            rule = rules_map.get(lithology_code, {})

            if current_unit is None:
                # Start a new unit
                current_unit = {
                    'from_depth': current_depth,
                    'to_depth': current_depth,
                    LITHOLOGY_COLUMN: lithology_code,
                    'lithology_qualifier': rule.get('qualifier', ''), # Add lithology_qualifier
                    'shade': rule.get('shade', ''),
                    'hue': rule.get('hue', ''),
                    'colour': rule.get('colour', ''),
                    'weathering': rule.get('weathering', ''),
                    'estimated_strength': rule.get('strength', ''),
                    'background_color': rule.get('background_color', '#FFFFFF'),
                    'svg_path': rule.get('svg_path'),
                    'start_index': i
                }
            elif lithology_code == current_unit[LITHOLOGY_COLUMN]:
                # Continue the current unit
                current_unit['to_depth'] = current_depth
            else:
                # End the previous unit and start a new one
                # The 'to_depth' of the completed unit is the 'from_depth' of the new unit, ensuring continuity.
                current_unit['to_depth'] = current_depth
                units.append(current_unit)

                # Start a new unit
                current_unit = {
                    'from_depth': current_depth,
                    'to_depth': current_depth,
                    LITHOLOGY_COLUMN: lithology_code,
                    'lithology_qualifier': rule.get('qualifier', ''), # Add lithology_qualifier
                    'shade': rule.get('shade', ''),
                    'hue': rule.get('hue', ''),
                    'colour': rule.get('colour', ''),
                    'weathering': rule.get('weathering', ''),
                    'estimated_strength': rule.get('strength', ''),
                    'background_color': rule.get('background_color', '#FFFFFF'),
                    'svg_path': rule.get('svg_path'),
                    'start_index': i
                }

        # Add the last unit after the loop finishes
        if current_unit is not None:
            # The to_depth of the last unit is the depth of the last row in the dataframe
            current_unit['to_depth'] = sorted_df.iloc[-1][DEPTH_COLUMN]
            units.append(current_unit)

        # Convert list of dictionaries to DataFrame
        units_df = pd.DataFrame(units)

        # Calculate thickness
        if not units_df.empty:
            units_df['thickness'] = units_df['to_depth'] - units_df['from_depth']

            # Add new editable columns with default empty values
            # Reorder columns as specified
            units_df = units_df[[
                'from_depth', 'to_depth', 'thickness', LITHOLOGY_COLUMN,
                'lithology_qualifier', 'shade', 'hue', 'colour',
                'weathering', 'estimated_strength', 'background_color', 'svg_path'
            ]]
        else:
            # Return an empty DataFrame with correct columns if no units were found
            units_df = pd.DataFrame(columns=[
                'from_depth', 'to_depth', 'thickness', LITHOLOGY_COLUMN,
                'lithology_qualifier', 'shade', 'hue', 'colour',
                'weathering', 'estimated_strength', 'background_color', 'svg_path'
            ])

        return units_df

    def merge_thin_units(self, units_df, threshold=DEFAULT_MERGE_THRESHOLD):
        """
        Merges lithological units that are thinner than the specified threshold and have the same lithology.

        Args:
            units_df (pandas.DataFrame): DataFrame of lithological units from group_into_units.
            threshold (float): Thickness threshold below which units are considered "thin" (default 0.05 meters = 5cm).

        Returns:
            pandas.DataFrame: DataFrame with thin adjacent units of same lithology merged.
        """
        if units_df.empty or len(units_df) <= 1:
            return units_df

        # Ensure units are sorted by depth
        merged_units = units_df.sort_values('from_depth').reset_index(drop=True)

        # List to hold final merged units
        final_units = []
        i = 0

        while i < len(merged_units):
            current_unit = merged_units.iloc[i].copy()

            # Check if this unit is thin and if there are more units to potentially merge
            while (current_unit['thickness'] < threshold and
                   i + 1 < len(merged_units)):

                next_unit = merged_units.iloc[i + 1]

                # Check if next unit has same lithology (code and qualifier)
                same_lithology = (current_unit[LITHOLOGY_COLUMN] == next_unit[LITHOLOGY_COLUMN] and
                                current_unit.get('lithology_qualifier', '') == next_unit.get('lithology_qualifier', ''))

                if same_lithology:
                    # Merge: extend current unit to include next unit
                    current_unit['to_depth'] = next_unit['to_depth']
                    current_unit['thickness'] = current_unit['to_depth'] - current_unit['from_depth']
                    i += 1  # Skip the merged unit
                else:
                    # Cannot merge, break the inner loop
                    break

            # Add the (potentially merged) unit to final list
            final_units.append(current_unit)
            i += 1

        # Convert back to DataFrame
        result_df = pd.DataFrame(final_units)

        # Ensure proper column ordering
        if not result_df.empty:
            result_df = result_df[[
                'from_depth', 'to_depth', 'thickness', LITHOLOGY_COLUMN,
                'lithology_qualifier', 'shade', 'hue', 'colour',
                'weathering', 'estimated_strength', 'background_color', 'svg_path'
            ]]

        return result_df

    def save_to_template(self, classified_data, template_path, output_path, callback=None, units=None):
        """
        Save classified lithology data to the 'Lithology' sheet in the TEMPLATE.xlsx file.
        
        Args:
            classified_data (pd.DataFrame): The dataframe with classified lithology
            template_path (str): Path to the template Excel file
            output_path (str): Path where the output file should be saved
            callback (function, optional): Callback function for progress updates
            units (pd.DataFrame, optional): Lithology units with from/to depths and properties
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Update progress
            if callback:
                callback(f"Loading template file: {template_path}")
                
            # Check if the template file exists
            if not os.path.exists(template_path):
                error_msg = f"Template file not found: {template_path}"
                logger.error(error_msg)
                if callback:
                    callback(error_msg)
                return False
            
            # Check if template and output paths are the same
            if os.path.abspath(template_path) != os.path.abspath(output_path):
                # If not the same, make a copy of the template file to avoid modifying the original
                if callback:
                    callback(f"Creating a copy of the template file at: {output_path}")
                
                # Ensure output directory exists
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # Copy the template to the output path
                shutil.copy2(template_path, output_path)
                
                # Load the copied workbook
                workbook = openpyxl.load_workbook(output_path)
            else:
                # If template and output paths are the same, load the workbook directly
                if callback:
                    callback(f"Writing directly to template file: {output_path}")
                workbook = openpyxl.load_workbook(output_path)
            
            # Try to get the 'Lithology' sheet
            if 'Lithology' in workbook.sheetnames:
                sheet = workbook['Lithology']
                if callback:
                    callback("Using 'Lithology' sheet in template")
            else:
                # If Lithology sheet doesn't exist, create it
                sheet = workbook.create_sheet('Lithology')
                if callback:
                    callback("Created new 'Lithology' sheet in template")
            
            # Update progress
            if callback:
                callback("Preparing data for template...")
            
            # Define starting row for data insertion (row 5 as specified)
            start_row = 5
            
            # Column mapping as specified
            column_mapping = {
                'from_depth': 'A',
                'to_depth': 'B',
                'thickness': 'D',
                LITHOLOGY_COLUMN: 'L',
                'lithology_qualifier': 'M', # Add lithology_qualifier to column mapping
                'shade': 'N',
                'hue': 'O',
                'colour': 'P',
                'weathering': 'Q',
                'estimated_strength': 'R'
            }
            
            # Function to safely write to a cell, handling merged cells
            def safe_write_cell(sheet, cell_coord, value):
                # Check if the cell coordinate is valid
                try:
                    cell = sheet[cell_coord]
                    
                    # Check if it's a merged cell
                    for merged_range in sheet.merged_cells.ranges:
                        if cell.coordinate in merged_range:
                            # Skip this cell - don't try to write to merged cells
                            return False
                    
                    # If not a merged cell, write the value
                    cell.value = value
                    return True
                except Exception as e:
                    logger.warning(f"Couldn't write to cell {cell_coord}: {str(e)}")
                    return False
            
            # If we have units data, use it for the template
            if units is not None and not units.empty:
                if callback:
                    callback(f"Writing {len(units)} lithology units to Lithology sheet starting at row {start_row}...")

                # Debug: Log first 5 units being written
                if callback and len(units) > 0:
                     callback("DEBUG (save_to_template): First 5 units to be written:")
                     for idx, unit_debug in units.head(5).iterrows():
                         callback(f"  Index {idx}: {unit_debug.to_dict()}")

                # Write units to the template
                for i, unit in units.iterrows():
                    row_num = start_row + i

                    # Write from depth in column A
                    safe_write_cell(sheet, f'{column_mapping["from_depth"]}{row_num}', unit['from_depth'])
                    
                    # Write to depth in column B
                    safe_write_cell(sheet, f'{column_mapping["to_depth"]}{row_num}', unit['to_depth'])
                    
                    # Write thickness in column D
                    safe_write_cell(sheet, f'{column_mapping["thickness"]}{row_num}', unit['thickness'])
                    
                    # Write lithology code in column L
                    safe_write_cell(sheet, f'{column_mapping[LITHOLOGY_COLUMN]}{row_num}', unit[LITHOLOGY_COLUMN])
                    
                    # Write lithology qualifier in column M if available
                    if 'lithology_qualifier' in unit and unit['lithology_qualifier']:
                        safe_write_cell(sheet, f'{column_mapping["lithology_qualifier"]}{row_num}', unit['lithology_qualifier'])

                    # Write shade in column N if available in the units dataframe
                    if 'shade' in unit and unit['shade']:
                        safe_write_cell(sheet, f'{column_mapping["shade"]}{row_num}', unit['shade'])
                    
                    # Write hue in column O if available
                    if 'hue' in unit and unit['hue']:
                        safe_write_cell(sheet, f'{column_mapping["hue"]}{row_num}', unit['hue'])
                    
                    # Write colour in column P if available
                    if 'colour' in unit and unit['colour']:
                        safe_write_cell(sheet, f'{column_mapping["colour"]}{row_num}', unit['colour'])

                    # Write weathering in column Q if available
                    if 'weathering' in unit and unit['weathering']:
                        safe_write_cell(sheet, f'{column_mapping["weathering"]}{row_num}', unit['weathering'])

                    # Write estimated strength in column R if available
                    if 'estimated_strength' in unit and unit['estimated_strength']:
                        safe_write_cell(sheet, f'{column_mapping["estimated_strength"]}{row_num}', unit['estimated_strength'])
                    
                    # Update progress every 100 units
                    if i % 100 == 0 and callback and i > 0:
                        callback(f"Writing unit {i+1} of {len(units)}...")

                # Debug: Log last 5 units being written
                if callback and len(units) > 5:
                     callback("DEBUG (save_to_template): Last 5 units to be written:")
                     for idx, unit_debug in units.tail(5).iterrows():
                         callback(f"  Index {idx}: {unit_debug.to_dict()}")

            # Update progress
            if callback:
                callback(f"Saving results to: {output_path}")
                
            # Save the workbook to the output path
            workbook.save(output_path)
            
            # Log success
            logger.info(f"Successfully saved results to {output_path} (Lithology sheet)")
            
            # Update progress
            if callback:
                callback(f"Results saved to Lithology sheet in: {output_path}")
                
            return True

        except PermissionError as pe:
            error_msg = f"PermissionError saving to template '{output_path}': {str(pe)}. Is the file open or write-protected?"
            logger.error(error_msg, exc_info=True) # Log traceback for permission errors
            if callback:
                callback(error_msg)
            return False
        except Exception as e:
            # Log the full traceback for unexpected errors
            error_msg = f"Unexpected error saving to template '{output_path}': {str(e)}"
            logger.error(error_msg, exc_info=True) # Log traceback for other errors
            if callback:
                callback(error_msg)
            return False
