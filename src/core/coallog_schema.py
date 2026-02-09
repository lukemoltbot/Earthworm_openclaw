"""
CoalLog v3.1 - 37-Column Table Schema
Industry standard geological logging format for coal exploration
"""

COALLOG_V31_SCHEMA = {
    # Column definitions for CoalLog v3.1 standard export
    "columns": [
        # 1-3: Depth Information
        {"name": "HOLE_ID", "type": "str", "description": "Borehole identification", "required": True},
        {"name": "FROM", "type": "float", "description": "Depth from (meters)", "required": True, "precision": 3},
        {"name": "TO", "type": "float", "description": "Depth to (meters)", "required": True, "precision": 3},
        
        # 4-6: Lithology Core
        {"name": "LITHOLOGY", "type": "str", "description": "Primary lithology code", "required": True},
        {"name": "QUALIFIER", "type": "str", "description": "Lithology qualifier", "required": False},
        {"name": "SECONDARY", "type": "str", "description": "Secondary lithology", "required": False},
        
        # 7-9: Color Attributes
        {"name": "SHADE", "type": "str", "description": "Color shade", "required": False},
        {"name": "HUE", "type": "str", "description": "Color hue", "required": False},
        {"name": "COLOUR", "type": "str", "description": "Color description", "required": False},
        
        # 10-12: Weathering & Strength
        {"name": "WEATHERING", "type": "str", "description": "Weathering grade", "required": False},
        {"name": "STRENGTH", "type": "str", "description": "Estimated strength", "required": False},
        {"name": "FRACTURE_INT", "type": "str", "description": "Fracture intensity", "required": False},
        
        # 13-15: Grain Size & Shape
        {"name": "GRAIN_SIZE", "type": "str", "description": "Grain size", "required": False},
        {"name": "GRAIN_SHAPE", "type": "str", "description": "Grain shape", "required": False},
        {"name": "SORTING", "type": "str", "description": "Sorting grade", "required": False},
        
        # 16-18: Coal Quality (Basic)
        {"name": "COAL_RANK", "type": "str", "description": "Coal rank", "required": False},
        {"name": "BANDING", "type": "str", "description": "Banding type", "required": False},
        {"name": "BRIGHTNESS", "type": "str", "description": "Coal brightness", "required": False},
        
        # 19-21: Structural Geology
        {"name": "DIP", "type": "float", "description": "Dip angle (degrees)", "required": False, "precision": 1},
        {"name": "DIP_DIR", "type": "float", "description": "Dip direction (degrees)", "required": False, "precision": 0},
        {"name": "JOINT_SPACING", "type": "str", "description": "Joint spacing", "required": False},
        
        # 22-24: Geotechnical
        {"name": "RQD", "type": "float", "description": "Rock Quality Designation (%)", "required": False, "precision": 1},
        {"name": "GSI", "type": "int", "description": "Geological Strength Index", "required": False},
        {"name": "UCS", "type": "float", "description": "Uniaxial Compressive Strength (MPa)", "required": False, "precision": 1},
        
        # 25-27: Core Recovery
        {"name": "CORE_REC", "type": "float", "description": "Core recovery (%)", "required": False, "precision": 1},
        {"name": "SOLID_CORE", "type": "float", "description": "Solid core recovery (%)", "required": False, "precision": 1},
        {"name": "FRACT_CORE", "type": "float", "description": "Fractured core recovery (%)", "required": False, "precision": 1},
        
        # 28-30: Hydrogeology
        {"name": "WATER_INFLOW", "type": "str", "description": "Water inflow description", "required": False},
        {"name": "PERMEABILITY", "type": "str", "description": "Permeability rating", "required": False},
        {"name": "AQUIFER", "type": "str", "description": "Aquifer indicator", "required": False},
        
        # 31-33: Geophysics
        {"name": "GAMMA", "type": "float", "description": "Gamma ray (API)", "required": False, "precision": 1},
        {"name": "RESISTIVITY", "type": "float", "description": "Resistivity (ohm-m)", "required": False, "precision": 2},
        {"name": "DENSITY", "type": "float", "description": "Density (g/cc)", "required": False, "precision": 3},
        
        # 34-36: Sample & Testing
        {"name": "SAMPLE_NO", "type": "str", "description": "Sample number", "required": False},
        {"name": "TEST_TYPE", "type": "str", "description": "Test type", "required": False},
        {"name": "LAB_NO", "type": "str", "description": "Laboratory number", "required": False},
        
        # 37: Comments
        {"name": "COMMENTS", "type": "str", "description": "General comments", "required": False}
    ],
    
    # Dictionary mappings for coded fields
    "dictionaries": {
        "LITHOLOGY": "Litho_Type",
        "QUALIFIER": "Litho_Qual", 
        "SHADE": "Shade",
        "HUE": "Hue",
        "COLOUR": "Colour",
        "WEATHERING": "Weathering",
        "STRENGTH": "Est_Strength",
        "FRACTURE_INT": ["Very Low", "Low", "Moderate", "High", "Very High"],
        "GRAIN_SIZE": ["Clay", "Silt", "Very Fine Sand", "Fine Sand", "Medium Sand", "Coarse Sand", "Very Coarse Sand", "Gravel"],
        "COAL_RANK": ["Peat", "Lignite", "Sub-bituminous", "Bituminous", "Anthracite"],
        "BANDING": ["Bright", "Dull", "Banded", "Interbanded"],
        "JOINT_SPACING": ["Very Close", "Close", "Moderate", "Wide", "Very Wide"],
        "WATER_INFLOW": ["Dry", "Damp", "Wet", "Dripping", "Flowing"],
        "PERMEABILITY": ["Very Low", "Low", "Moderate", "High", "Very High"]
    },
    
    # Validation rules
    "validation": {
        "FROM": {"min": 0, "max": 5000},
        "TO": {"min": 0, "max": 5000},
        "DIP": {"min": 0, "max": 90},
        "DIP_DIR": {"min": 0, "max": 360},
        "RQD": {"min": 0, "max": 100},
        "CORE_REC": {"min": 0, "max": 100},
        "GAMMA": {"min": 0, "max": 1000}
    }
}

def get_coallog_schema():
    """Return the complete CoalLog v3.1 schema"""
    return COALLOG_V31_SCHEMA

def get_column_names():
    """Return list of all 37 column names"""
    return [col["name"] for col in COALLOG_V31_SCHEMA["columns"]]

def get_required_columns():
    """Return list of required column names"""
    return [col["name"] for col in COALLOG_V31_SCHEMA["columns"] if col.get("required", False)]

def get_dictionary_columns():
    """Return columns that use dictionary lookups"""
    return list(COALLOG_V31_SCHEMA["dictionaries"].keys())

def create_empty_dataframe():
    """Create an empty pandas DataFrame with CoalLog schema"""
    import pandas as pd
    
    columns = []
    dtypes = {}
    
    for col_def in COALLOG_V31_SCHEMA["columns"]:
        columns.append(col_def["name"])
        
        # Map type strings to pandas dtypes
        if col_def["type"] == "float":
            dtypes[col_def["name"]] = "float64"
        elif col_def["type"] == "int":
            dtypes[col_def["name"]] = "int64"
        else:
            dtypes[col_def["name"]] = "object"
    
    df = pd.DataFrame(columns=columns)
    
    # Set dtypes
    for col, dtype in dtypes.items():
        df[col] = df[col].astype(dtype)
    
    return df

def validate_dataframe(df):
    """Validate a DataFrame against CoalLog schema"""
    errors = []
    
    # Check all required columns exist
    required = get_required_columns()
    missing = [col for col in required if col not in df.columns]
    if missing:
        errors.append(f"Missing required columns: {missing}")
    
    # Check data types
    for col_def in COALLOG_V31_SCHEMA["columns"]:
        col_name = col_def["name"]
        if col_name in df.columns:
            # Check for nulls in required columns
            if col_def.get("required", False) and df[col_name].isnull().any():
                errors.append(f"Required column '{col_name}' contains null values")
    
    return errors

if __name__ == "__main__":
    print("CoalLog v3.1 - 37-Column Schema")
    print("=" * 60)
    
    print(f"Total columns: {len(get_column_names())}")
    print(f"Required columns: {len(get_required_columns())}")
    print(f"Dictionary columns: {len(get_dictionary_columns())}")
    
    print("\nColumn List:")
    for i, col in enumerate(get_column_names(), 1):
        print(f"{i:2d}. {col}")