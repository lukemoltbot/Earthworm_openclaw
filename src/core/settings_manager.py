import json
import os
from .config import DEFAULT_LITHOLOGY_RULES, DEFAULT_SEPARATOR_THICKNESS, DRAW_SEPARATOR_LINES, CURVE_INVERSION_DEFAULTS, DEFAULT_CURVE_THICKNESS, DEFAULT_MERGE_THIN_UNITS, DEFAULT_MERGE_THRESHOLD

USE_RESEARCHED_DEFAULTS_DEFAULT = True  # Default to maintaining backward compatibility

DEFAULT_SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".earthworm_settings.json")

def load_settings(file_path=None):
    """Loads application settings from a JSON file, or returns defaults if not found/invalid."""
    if file_path is None:
        file_path = DEFAULT_SETTINGS_FILE

    settings = {
        "lithology_rules": DEFAULT_LITHOLOGY_RULES,
        "separator_thickness": DEFAULT_SEPARATOR_THICKNESS,
        "draw_separator_lines": DRAW_SEPARATOR_LINES,
        "curve_inversion_settings": CURVE_INVERSION_DEFAULTS,
        "curve_thickness": DEFAULT_CURVE_THICKNESS,  # Add new setting
        "use_researched_defaults": USE_RESEARCHED_DEFAULTS_DEFAULT,
        "analysis_method": "standard",  # Default analysis method
        "merge_thin_units": DEFAULT_MERGE_THIN_UNITS,
        "merge_threshold": DEFAULT_MERGE_THRESHOLD
    }
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                loaded_settings = json.load(f)
                # Update default settings with loaded ones, ensuring all keys are present
                # For nested dictionaries like curve_inversion_settings, update them individually
                if "curve_inversion_settings" in loaded_settings and isinstance(loaded_settings["curve_inversion_settings"], dict):
                    settings["curve_inversion_settings"].update(loaded_settings["curve_inversion_settings"])
                    del loaded_settings["curve_inversion_settings"] # Remove to avoid overwriting the updated dict
                settings.update(loaded_settings)
        except json.JSONDecodeError:
            print(f"Warning: Could not decode JSON from {file_path}. Using default settings.")
        except Exception as e:
            print(f"Warning: Error loading settings from {file_path}: {e}. Using default settings.")
    return settings

def save_settings(lithology_rules, separator_thickness, draw_separator_lines, curve_inversion_settings, curve_thickness, use_researched_defaults, analysis_method="standard", merge_thin_units=False, merge_threshold=0.05, file_path=None):
    """Saves application settings to a JSON file."""
    if file_path is None:
        file_path = DEFAULT_SETTINGS_FILE

    settings = {
        "lithology_rules": lithology_rules,
        "separator_thickness": separator_thickness,
        "draw_separator_lines": draw_separator_lines,
        "curve_inversion_settings": curve_inversion_settings,
        "curve_thickness": curve_thickness,  # Save new setting
        "use_researched_defaults": use_researched_defaults,
        "analysis_method": analysis_method,  # Save analysis method
        "merge_thin_units": merge_thin_units,
        "merge_threshold": merge_threshold
    }
    try:
        # Ensure the directory exists before writing
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        print(f"Error: Could not save settings to {file_path}: {e}")
