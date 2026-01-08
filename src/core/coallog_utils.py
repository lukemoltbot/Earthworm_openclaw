import pandas as pd
import os

def load_coallog_dictionaries(file_path):
    """
    Loads dictionaries from the CoalLog Excel file.

    Args:
        file_path (str): The path to the CoalLog Excel file.

    Returns:
        dict: A dictionary containing the loaded data, with sheet names as keys.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"CoalLog dictionaries file not found: {file_path}")

    xls = pd.ExcelFile(file_path)
    
    # Litho_Type
    litho_type_sheet = xls.parse('Litho_Type', header=None)
    df1 = litho_type_sheet.iloc[2:127, [0, 1]]
    df1.columns = ['Code', 'Description']
    df2 = litho_type_sheet.iloc[2:127, [3, 2]]
    df2.columns = ['Code', 'Description']
    df3 = litho_type_sheet.iloc[2:129, [5, 4]]
    df3.columns = ['Code', 'Description']
    litho_type_df = pd.concat([df1, df2, df3]).dropna()

    # Shade
    shade_sheet = xls.parse('Shade', header=None)
    df1 = shade_sheet.iloc[2:12, [0, 1]]
    df1.columns = ['Shade', 'Description'] # Corrected column name
    df2 = shade_sheet.iloc[2:12, [3, 2]]
    df2.columns = ['Shade', 'Description'] # Corrected column name
    df3 = shade_sheet.iloc[2:12, [5, 4]]
    df3.columns = ['Shade', 'Description'] # Corrected column name
    shade_df = pd.concat([df1, df2, df3]).dropna()

    # Hue
    hue_sheet = xls.parse('Hue', header=None)
    df1 = hue_sheet.iloc[2:16, [0, 1]]
    df1.columns = ['Hue', 'Description'] # Corrected column name
    df2 = hue_sheet.iloc[2:16, [3, 2]]
    df2.columns = ['Hue', 'Description'] # Corrected column name
    hue_df = pd.concat([df1, df2]).dropna()

    # Colour
    colour_sheet = xls.parse('Colour', header=None)
    df1 = colour_sheet.iloc[2:17, [0, 1]]
    df1.columns = ['Colour', 'Description'] # Corrected column name
    df2 = colour_sheet.iloc[2:17, [3, 2]]
    df2.columns = ['Colour', 'Description'] # Corrected column name
    colour_df = pd.concat([df1, df2]).dropna()

    # Weathering
    weathering_sheet = xls.parse('Weathering', header=None)
    df1 = weathering_sheet.iloc[2:10, [0, 1]]
    df1.columns = ['Weathering', 'Description'] # Corrected column name
    df2 = weathering_sheet.iloc[2:10, [3, 2]]
    df2.columns = ['Weathering', 'Description'] # Corrected column name
    df3 = weathering_sheet.iloc[2:10, [5, 4]]
    df3.columns = ['Weathering', 'Description'] # Corrected column name
    weathering_df = pd.concat([df1, df2, df3]).dropna()

    # Est_Strength
    strength_sheet = xls.parse('Est_Strength', header=None)
    df1 = strength_sheet.iloc[2:25, [0, 1]]
    df1.columns = ['Estimated Strength', 'Description'] # Corrected column name
    df2 = strength_sheet.iloc[2:28, [3, 2]]
    df2.columns = ['Estimated Strength', 'Description'] # Corrected column name
    strength_df = pd.concat([df1, df2]).dropna()

    # Litho_Qual
    litho_qual_sheet = xls.parse('Litho_Qual', header=None)
    df1 = litho_qual_sheet.iloc[2:129, [0, 1]]
    df1.columns = ['Code', 'Description']
    df2 = litho_qual_sheet.iloc[2:129, [3, 2]]
    df2.columns = ['Code', 'Description']
    df3 = litho_qual_sheet.iloc[2:129, [5, 4]]
    df3.columns = ['Code', 'Description']
    litho_qual_df = pd.concat([df1, df2, df3]).dropna()

    dictionaries = {
        'Litho_Type': litho_type_df,
        'Litho_Qual': litho_qual_df,
        'Shade': shade_df,
        'Hue': hue_df,
        'Colour': colour_df,
        'Weathering': weathering_df,
        'Est_Strength': strength_df
    }
    
    return dictionaries
