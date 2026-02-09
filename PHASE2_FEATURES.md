# Phase 2 Features: 37-Column CoalLog Schema & Tabbed Settings

## Overview

Phase 2 of Earthworm Development Plan V2.1 implements two major features:
1. **37-Column CoalLog Table Schema** - Industry-standard geological logging format
2. **Modal Tabbed Settings Dialog** - Comprehensive application configuration

## 1. 37-Column CoalLog Table Schema

### What is CoalLog v3.1?
CoalLog v3.1 is an industry-standard format for geological logging in coal exploration. It provides a comprehensive 37-column schema that captures all essential geological, geotechnical, and hydrogeological data.

### Column Categories

The 37 columns are organized into 13 logical categories:

#### 1. Depth Information (3 columns)
- `HOLE_ID` - Borehole identification
- `FROM` - Depth from (meters)
- `TO` - Depth to (meters)

#### 2. Lithology Core (3 columns)
- `LITHOLOGY` - Primary lithology code
- `QUALIFIER` - Lithology qualifier
- `SECONDARY` - Secondary lithology

#### 3. Color Attributes (3 columns)
- `SHADE` - Color shade
- `HUE` - Color hue
- `COLOUR` - Color description

#### 4. Weathering & Strength (3 columns)
- `WEATHERING` - Weathering grade
- `STRENGTH` - Estimated strength
- `FRACTURE_INT` - Fracture intensity

#### 5. Grain Size & Shape (3 columns)
- `GRAIN_SIZE` - Grain size
- `GRAIN_SHAPE` - Grain shape
- `SORTING` - Sorting grade

#### 6. Coal Quality (3 columns)
- `COAL_RANK` - Coal rank
- `BANDING` - Banding type
- `BRIGHTNESS` - Coal brightness

#### 7. Structural Geology (3 columns)
- `DIP` - Dip angle (degrees)
- `DIP_DIR` - Dip direction (degrees)
- `JOINT_SPACING` - Joint spacing

#### 8. Geotechnical (3 columns)
- `RQD` - Rock Quality Designation (%)
- `GSI` - Geological Strength Index
- `UCS` - Uniaxial Compressive Strength (MPa)

#### 9. Core Recovery (3 columns)
- `CORE_REC` - Core recovery (%)
- `SOLID_CORE` - Solid core recovery (%)
- `FRACT_CORE` - Fractured core recovery (%)

#### 10. Hydrogeology (3 columns)
- `WATER_INFLOW` - Water inflow description
- `PERMEABILITY` - Permeability rating
- `AQUIFER` - Aquifer indicator

#### 11. Geophysics (3 columns)
- `GAMMA` - Gamma ray (API)
- `RESISTIVITY` - Resistivity (ohm-m)
- `DENSITY` - Density (g/cc)

#### 12. Sample & Testing (3 columns)
- `SAMPLE_NO` - Sample number
- `TEST_TYPE` - Test type
- `LAB_NO` - Laboratory number

#### 13. Comments (1 column)
- `COMMENTS` - General comments

### Key Features

#### Dictionary-Based Dropdowns
- Coded fields use CoalLog dictionary lookups
- Displays: "Description (Code)"
- Saves: Just the code
- Searchable comboboxes with type-ahead

#### Auto-Calculation
- Thickness automatically calculated from FROM/TO
- Real-time validation of numeric fields
- Error highlighting for invalid entries

#### Data Validation
- Type checking (float, int, string)
- Range validation for numeric fields
- Required field validation
- Real-time error feedback

#### Backward Compatibility
- Works with existing 13-column data
- Automatic column mapping
- Graceful handling of missing columns
- Settings flag: `use_coallog_table`

### Usage

```python
# Import the table widget
from src.ui.widgets.coallog_table_widget import CoalLogTableWidget

# Create table with dictionary data
table = CoalLogTableWidget(coallog_data=dictionary_data)

# Load data from pandas DataFrame
table.load_data(dataframe)

# Get data as DataFrame
df = table.get_dataframe()
```

## 2. Modal Tabbed Settings Dialog

### Overview
A comprehensive settings dialog with 5 tabs for managing all application preferences. Settings are persisted to JSON and loaded on startup.

### Tab Structure

#### 1. General Tab
- **Application Theme**: Light/Dark/System
- **Unit System**: Metric (meters) / Imperial (feet)
- **File Paths**: Default project and export directories
- **Auto-save**: Enable/disable with configurable interval

#### 2. Lithology Tab
- **Default Lithology Codes**: Editable table of codes, names, and colors
- **Qualifier Preferences**: Auto-application and separator settings
- **Dictionary Files**: Path to lithology dictionary files
- **Color Mappings**: Custom color schemes for lithologies

#### 3. Geotechnical Tab
- **Strength Classification**: ISRM/BSI/Custom systems
- **Weathering Grades**: System selection and thresholds
- **Fracture Intensity**: Default values and units
- **RQD Calculation**: Threshold and method settings

#### 4. Export Tab
- **CoalLog Format**: 37-Column/Extended/Custom options
- **File Format**: CSV/Excel/LAS/JSON selection
- **Column Selection**: Choose which columns to export
- **Header/Footer Options**: Include metadata in exports

#### 5. Advanced Tab
- **Performance Settings**: Cache size and optimization
- **Debug Options**: Enable logging and diagnostics
- **Experimental Features**: AI suggestions and new features
- **Reset to Defaults**: Restore factory settings

### Settings Persistence
- Settings saved to `~/.earthworm_settings.json`
- Automatic loading on application startup
- JSON format for easy manual editing
- Backup and restore functionality

### Usage

```python
# Import the settings dialog
from src.ui.dialogs.tabbed_settings_dialog import TabbedSettingsDialog

# Create and show dialog
dialog = TabbedSettingsDialog(parent=self)
if dialog.exec():
    # Settings were saved
    print("Settings applied")
```

## Integration with Main Application

### Backward Compatibility
- Settings flag: `use_coallog_table` controls which table widget to use
- When `True`: Uses 37-column `CoalLogTableWidget`
- When `False`: Uses 13-column `LithologyTableWidget`
- Automatic migration of existing data

### Menu Integration
- Settings dialog accessible via `Edit → Settings` menu
- Keyboard shortcut: `Ctrl+,` (Cmd+, on macOS)
- Status bar indicator for settings status

### Signal Handling
- Table data changes trigger graphics updates
- Validation errors displayed in status bar
- Settings changes applied immediately or on restart

## Migration Guide

### From 13-Column to 37-Column

#### Automatic Migration
1. Existing data automatically mapped to new schema
2. Missing columns filled with empty values
3. Dictionary codes preserved where possible

#### Manual Adjustments
1. Review auto-mapped data for accuracy
2. Fill in additional columns as needed
3. Configure dictionary paths for dropdowns

#### Testing Migration
1. Backup existing data first
2. Test with sample dataset
3. Verify all functionality works

## Troubleshooting

### Common Issues

#### 1. Missing Dictionary Files
- **Symptom**: Dropdowns show empty or text entry only
- **Solution**: Configure dictionary file path in Lithology tab
- **Workaround**: Manual text entry still works

#### 2. Performance with Large Datasets
- **Symptom**: Slow scrolling or editing
- **Solution**: Adjust cache size in Advanced tab
- **Workaround**: Use virtual scrolling for very large datasets

#### 3. Import/Export Format Issues
- **Symptom**: Data loss or formatting errors
- **Solution**: Check column selection in Export tab
- **Workaround**: Export to CSV and review manually

#### 4. Settings Not Persisting
- **Symptom**: Settings revert on restart
- **Solution**: Check file permissions for settings file
- **Workaround**: Manual edit of JSON settings file

### Error Messages

#### "Required field is empty"
- **Cause**: Required column (HOLE_ID, FROM, TO, LITHOLOGY) has no value
- **Fix**: Enter value in highlighted cell

#### "Value must be a number"
- **Cause**: Non-numeric value in numeric column
- **Fix**: Enter valid number

#### "Value out of range"
- **Cause**: Number outside valid range (e.g., negative depth)
- **Fix**: Enter value within valid range

## Technical Details

### File Structure
```
src/core/coallog_schema.py          # 37-column schema definition
src/ui/widgets/coallog_table_widget.py  # Table widget implementation
src/ui/dialogs/tabbed_settings_dialog.py # Settings dialog
src/ui/main_window.py               # Main application integration
```

### Dependencies
- PyQt6 (or PyQt5) for GUI
- pandas for data handling
- numpy for numerical operations
- Standard Python libraries

### Performance Considerations
- Virtual scrolling for large datasets
- Lazy loading of dictionary data
- Efficient signal/slot connections
- Background saving of settings

## Next Steps

### Phase 3 Planning
- Enhanced visualization tools
- Real-time data synchronization
- Advanced editing features

### User Testing
- Test with real geological data
- Verify all 37 columns work correctly
- Test settings persistence
- Performance testing with large datasets

### Documentation Updates
- Update user manual with new features
- Create video tutorials
- Add tooltips and help text

---

**Status**: Phase 2 implementation complete  
**Ready for**: User testing and Phase 3 development  
**Support**: See `README.md` and `test_coallog_37columns.py` for testing