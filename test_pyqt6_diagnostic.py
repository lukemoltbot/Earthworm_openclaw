#!/usr/bin/env python3
"""
Diagnostic script for PyQt6 installation issues
"""

import sys
import traceback

print("=== PyQt6 Diagnostic Test ===")
print(f"Python: {sys.version}")
print(f"Python path: {sys.executable}")

# Test 1: Basic PyQt6 import
print("\n1. Testing PyQt6 import...")
try:
    import PyQt6
    print("   ✓ PyQt6 imported successfully")
    
    # Try different version attributes
    version = None
    if hasattr(PyQt6, '__version__'):
        version = PyQt6.__version__
    elif hasattr(PyQt6, 'QtCore'):
        import PyQt6.QtCore
        if hasattr(PyQt6.QtCore, '__version__'):
            version = PyQt6.QtCore.__version__
        elif hasattr(PyQt6.QtCore, 'QT_VERSION_STR'):
            version = PyQt6.QtCore.QT_VERSION_STR
    
    if version:
        print(f"   ✓ PyQt6 version: {version}")
    else:
        print("   ⚠️  Could not determine PyQt6 version (but import worked)")
        
except ImportError as e:
    print(f"   ✗ PyQt6 import failed: {e}")
    sys.exit(1)

# Test 2: QtCore import
print("\n2. Testing QtCore import...")
try:
    from PyQt6 import QtCore
    print("   ✓ QtCore imported successfully")
    
    # Check for QFileSystemModel
    if hasattr(QtCore, 'QFileSystemModel'):
        print("   ✓ QFileSystemModel found in QtCore")
    else:
        print("   ✗ QFileSystemModel NOT found in QtCore")
        print("   Available QtCore items (filtered):")
        items = [item for item in dir(QtCore) if 'File' in item or 'Model' in item]
        for item in items:
            print(f"     - {item}")
        if not items:
            print("     (No File/Model related items found)")
            
except ImportError as e:
    print(f"   ✗ QtCore import failed: {e}")
    traceback.print_exc()

# Test 3: QtWidgets import  
print("\n3. Testing QtWidgets import...")
try:
    from PyQt6 import QtWidgets
    print("   ✓ QtWidgets imported successfully")
    
    # Check for QFileSystemModel in QtWidgets (some versions)
    if hasattr(QtWidgets, 'QFileSystemModel'):
        print("   ✓ QFileSystemModel found in QtWidgets")
    else:
        print("   ⚠️  QFileSystemModel not in QtWidgets (expected for Qt6)")
        
except ImportError as e:
    print(f"   ✗ QtWidgets import failed: {e}")

# Test 4: Try to import QFileSystemModel directly
print("\n4. Testing direct QFileSystemModel import...")
try:
    from PyQt6.QtCore import QFileSystemModel
    print("   ✓ QFileSystemModel imported from QtCore successfully")
    print("   ✓ PyQt6 installation appears correct")
except ImportError as e:
    print(f"   ✗ QFileSystemModel import failed: {e}")
    print("\n   Trying alternative import locations...")
    
    # Try QtWidgets
    try:
        from PyQt6.QtWidgets import QFileSystemModel
        print("   ✓ QFileSystemModel found in QtWidgets (unexpected for Qt6)")
    except ImportError:
        print("   ✗ Not in QtWidgets either")
    
    # Try QtGui
    try:
        from PyQt6.QtGui import QFileSystemModel
        print("   ✓ QFileSystemModel found in QtGui (unexpected)")
    except ImportError:
        print("   ✗ Not in QtGui either")

# Test 5: Create minimal QApplication
print("\n5. Testing QApplication creation...")
try:
    from PyQt6.QtWidgets import QApplication
    app = QApplication([])
    print("   ✓ QApplication created successfully")
    # Don't actually run exec() to avoid blocking
    print("   ✓ PyQt6 functional test passed")
except Exception as e:
    print(f"   ✗ QApplication test failed: {e}")
    traceback.print_exc()

print("\n=== Diagnostic Complete ===")
print("\nRecommendations:")
print("1. If QFileSystemModel not found: PyQt6 installation may be incomplete")
print("2. Try: pip install --force-reinstall PyQt6==6.9.1 PyQt6-Qt6==6.9.1")
print("3. Or: Use system Python: /usr/bin/python3 main.py")
print("4. Check macOS architecture: python -c \"import platform; print(platform.machine())\"")