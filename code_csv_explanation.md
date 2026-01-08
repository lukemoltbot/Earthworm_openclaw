# Earthworm Lithology Analysis: Detailed Explanation

This document explains in high detail how the lithology analysis works within the Earthworm application and exactly how the results are written to the Excel template output file. It references the necessary files required for these functionalities to work successfully.

### 1. Overview of the Lithology Analysis Workflow

The overall workflow for lithology analysis can be summarized as follows:
1.  **Data Loading**: Raw geological data (from Excel or LAS files) is loaded into a pandas DataFrame.
2.  **Data Preprocessing**: The loaded data is cleaned, filtered (e.g., by casing depth), and prepared for analysis. This includes handling missing values and creating derived columns.
3.  **Lithology Classification**: Based on predefined ranges of geological parameters (like GRDE, SSD, DENCDL), the system classifies each data point into a specific lithology type.
4.  **Analysis and Summarization**: Various analyses are performed, such as summarizing lithology properties, getting distributions, and comparing original vs. classified lithologies.
5.  **Output Generation**: The classified and analyzed data, particularly the lithology units, are written to a structured Excel template file.

### 2. Key Files Involved

The core functionalities are distributed across these files:

*   **`config.py`**: This file defines all the configurable parameters and constants used throughout the application. It's crucial for understanding default column names, analysis parameters, and the initial lithology classification ranges.
    *   **Key variables**: `DEPTH_COLUMN`, `LITHOLOGY_COLUMN`, `LITHOQUAL_COLUMN`, `LITHOLOGY_QUAL_COLUMN`, `ANALYSIS_COLUMNS`, `DEFAULT_LITHOLOGY_RANGES`, `INVALID_DATA_VALUE`.
*   **`data_processor.py`**: This module is responsible for all data handling operations, including loading data from various formats (Excel, LAS), validating column names, and preprocessing the data to make it suitable for analysis.
    *   **Key functions**: `load_data`, `load_las_file`, `preprocess_data`, `validate_column_name`, `validate_required_columns`, `save_output_file`.
*   **`analyzer.py`**: This module contains the core logic for performing lithology analysis, including classification, summarization, distribution, and comparison. It also handles the specific task of writing the classified lithology units to the Excel template.
    *   **Key functions**: `summarize_lithology`, `classify_lithology`, `get_lithology_distribution`, `compare_lithology_classifications`, `analyze_lithology_ranges`, `save_to_template`.

### 3. Detailed Breakdown of Analysis

#### 3.1. Data Loading and Preprocessing (`data_processor.py`)

Before any analysis can occur, the raw data must be loaded and prepared.

*   **`load_data(file_path, sheet_name=None)`**:
    *   **Purpose**: Loads data from an Excel file (`.xlsx`).
    *   **Mechanism**: Uses `pandas.read_excel`. If `sheet_name` is not provided, it reads the first sheet.
    *   **Output**: A pandas DataFrame with cleaned column names (stripped of whitespace).
*   **`load_las_file(file_path, callback=None)`**:
    *   **Purpose**: Loads data from a LAS (Log ASCII Standard) file.
    *   **Mechanism**: Contains a basic custom parser that reads line by line, identifies header information (`~A` section for data, `~CURVE` for curve mnemonics), and then parses the data section. It attempts to convert values to floats and handles common delimiters (tabs, spaces). It also renames a depth-related column to `DEPTH_COLUMN` if found.
    *   **Output**: A pandas DataFrame.
*   **`preprocess_data(data, casing_depth, callback=None)`**:
    *   **Purpose**: Cleans and transforms the raw loaded data.
    *   **Mechanism**:
        1.  **Copies Data**: Works on a copy of the input DataFrame to avoid modifying the original.
        2.  **Invalid Value Replacement**: Replaces `INVALID_DATA_VALUE` (defined in `config.py`, e.g., -999.25) with `np.nan` (Not a Number).
        3.  **Depth Column Identification**: Ensures a `DEPTH_COLUMN` exists, attempting to rename a similar column if the exact name isn't found.
        4.  **Casing Depth Filtering**: Filters out data points where `DEPTH` is less than or equal to `casing_depth`.
        5.  **Column Type Identification**: Separates numerical and categorical columns.
        6.  **Derived Column Creation**: If both `LITHOLOGY_COLUMN` and `LITHOQUAL_COLUMN` exist, it creates a new `LITHOLOGY_QUAL_COLUMN` by concatenating their values (e.g., "SS_Good").
        7.  **Missing Value Handling**: Drops columns that are entirely empty (`dropna(axis=1, how='all')`) and converts categorical columns to string type, replacing 'nan' strings with `None`.
    *   **Output**: A preprocessed pandas DataFrame, along with lists of numerical and categorical column names.
*   **`validate_column_name` and `validate_required_columns`**: These helper functions ensure that expected columns exist in the DataFrame, handling variations in naming and raising errors if critical columns are missing.

#### 3.2. Lithology Classification (`analyzer.py`)

This is the core of the lithology analysis, assigning a lithology type based on parameter ranges.

*   **`classify_lithology(data, lithology_ranges, analysis_columns=None, callback=None)`**:
    *   **Purpose**: Assigns a `CLASSIFIED_LITHOLOGY` to each row in the DataFrame based on defined geological parameter ranges.
    *   **Mechanism**:
        1.  **Copies Data**: Works on a copy of the input DataFrame.
        2.  **Default Ranges**: Uses `ANALYSIS_COLUMNS` from `config.py` if not explicitly provided.
        3.  **Initialization**: Adds a new column `CLASSIFIED_LITHOLOGY` and initializes all values to 'Unknown'.
        4.  **Iterates through Lithology Ranges**: For each lithology type (e.g., "SS", "CO") defined in `lithology_ranges` (which typically comes from `DEFAULT_LITHOLOGY_RANGES` in `config.py` or user-defined settings from the GUI):
            *   It iterates through the parameters (e.g., "GRDE", "SSD") and their associated min/max ranges.
            *   It creates a boolean `mask` for each row, checking if the values in the `analysis_columns` fall within the specified range for that lithology.
            *   If a row satisfies all parameter ranges for a given lithology, its `CLASSIFIED_LITHOLOGY` is updated to that lithology.
            *   It handles `None` or 'Null' values in ranges by treating them as negative/positive infinity, and adjusts ranges to fit within overall data ranges.
    *   **Output**: The DataFrame with the new `CLASSIFIED_LITHOLOGY` column.

#### 3.3. Lithology Summarization and Comparison (`analyzer.py`)

These functions provide insights into the classified data.

*   **`summarize_lithology(data, analysis_columns=None, callback=None)`**:
    *   **Purpose**: Calculates statistical summaries (mean, std, min, max, count) for `ANALYSIS_COLUMNS` grouped by `LITHOLOGY_COLUMN` and `LITHOLOGY_QUAL_COLUMN`.
    *   **Mechanism**: Uses `groupby()` and `agg()` functions of pandas to perform aggregations.
    *   **Output**: Two DataFrames: `lithology_summary` and `lithology_qual_summary`.
*   **`get_lithology_distribution(data, column=None)`**:
    *   **Purpose**: Calculates the count and percentage distribution of lithology values.
    *   **Mechanism**: Uses `value_counts()` and calculates percentages.
    *   **Output**: A DataFrame showing lithology counts and percentages.
*   **`compare_lithology_classifications(data, callback=None)`**:
    *   **Purpose**: Compares the original `LITHOLOGY_COLUMN` with the `CLASSIFIED_LITHOLOGY` column to assess agreement.
    *   **Mechanism**: Uses `pd.crosstab` to create a contingency table, normalized by index to show percentages of classified lithologies for each original lithology. It also calculates an overall agreement percentage.
    *   **Output**: A comparison matrix DataFrame.
*   **`analyze_lithology_ranges(lithology_ranges, analysis_columns, overall_ranges, callback=None)`**:
    *   **Purpose**: Identifies gaps in the defined lithology ranges for specified analysis columns, relative to the overall data ranges.
    *   **Mechanism**: Iterates through each analysis column, collects all defined intervals from `lithology_ranges`, sorts them, and then finds the gaps between these intervals and the overall min/max range for that column.
    *   **Output**: A dictionary detailing gaps and defined intervals for each analysis column.

### 4. Writing to the Excel Template Output File (`analyzer.py`'s `save_to_template`)

The `save_to_template` function is designed to write classified lithology data into a specific sheet and format within an Excel template.

*   **`save_to_template(classified_data, template_path, output_path, callback=None, units=None)`**:
    *   **Purpose**: Saves the processed lithology units (contained in the `units` DataFrame) to the 'Lithology' sheet of an Excel template. This `units` DataFrame typically contains grouped lithology intervals with `from_depth`, `to_depth`, `thickness`, `lithology`, and associated properties like `shade`, `hue`, and `color`.
    *   **Mechanism**:
        1.  **Imports**: Utilizes `openpyxl` for direct Excel file manipulation and `shutil` for copying files.
        2.  **Template Handling**:
            *   Verifies the existence of the `template_path`.
            *   If the `output_path` differs from the `template_path`, it first creates a copy of the `TEMPLATE.xlsx` file to the specified `output_path`. This ensures the original template remains untouched.
            *   Loads the Excel workbook (either the original template or its newly created copy).
        3.  **Sheet Selection/Creation**: It attempts to access the sheet named 'Lithology'. If this sheet does not exist within the workbook, it is automatically created.
        4.  **Column Mapping**: A predefined `column_mapping` dictionary dictates precisely which columns from the input `units` DataFrame are written to specific columns in the Excel sheet. The mapping is as follows:
            ```python
            column_mapping = {
                'from_depth': 'A',  # Start depth of the lithology unit
                'to_depth': 'B',    # End depth of the lithology unit
                'thickness': 'D',   # Calculated thickness of the unit
                'lithology': 'L',   # Lithology code (e.g., "SS", "CO")
                'shade': 'N',       # Shade property of the lithology
                'hue': 'O',         # Hue property of the lithology
                'color': 'P'        # Color property of the lithology
            }
            ```
        5.  **Data Insertion**:
            *   Data insertion begins at `start_row = 5` in the Excel sheet.
            *   The function iterates through each lithology `unit` (row) in the `units` DataFrame.
            *   For each unit, it writes the corresponding values for `from_depth`, `to_depth`, `thickness`, `lithology`, `shade`, `hue`, and `color` to their respective mapped Excel cells.
            *   A crucial `safe_write_cell` helper function is employed to prevent writing to merged cells, which can lead to errors or data corruption in `openpyxl`.
        6.  **Saving**: Finally, the modified workbook, now containing the lithology analysis results, is saved to the designated `output_path`.
    *   **Required Files**:
        *   `TEMPLATE.xlsx`: This Excel template file serves as the base for the output. It must be accessible at the specified `template_path`.
        *   The input `units` DataFrame must contain all the columns defined in the `column_mapping` (`from_depth`, `to_depth`, `thickness`, `lithology`, `shade`, `hue`, `color`). These columns are generated during the earlier stages of the analysis workflow, specifically from the classification and grouping of raw data into distinct lithological units.

In summary, the lithology analysis pipeline is a robust system that loads and preprocesses data, classifies it based on configurable ranges, performs various analytical summaries, and then outputs the results into a structured Excel template, ready for further use or reporting. The `config.py` file acts as the central hub for all parameters, allowing for easy modification of analysis behavior without changing the core logic.
