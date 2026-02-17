import sys
import os

# Add project root to path
sys.path.insert(0, os.getcwd())

print("Attempting to import modules...")

try:
    from src.ecos_loader import fetch_ecos_data
    print("✅ src.ecos_loader imported successfully")
except ImportError as e:
    print(f"❌ Failed to import src.ecos_loader: {e}")

try:
    from src.taylor_rule import calculate_taylor_rule
    print("✅ src.taylor_rule imported successfully")
except ImportError as e:
    print(f"❌ Failed to import src.taylor_rule: {e}")

try:
    from src.views.taylor_view import render_taylor_view
    print("✅ src.views.taylor_view imported successfully")
except ImportError as e:
    print(f"❌ Failed to import src.views.taylor_view: {e}")

try:
    import app
    print("✅ app imported successfully (syntax check passed)")
except ImportError as e:
    # app.py runs main() on import if not careful, but it has if __name__ == "__main__":
    # However, streamlit commands in top level might fail if not run via streamlit.
    # We just want to check syntax.
    print(f"⚠️ App import might fail due to streamlit context, but checking for syntax errors: {e}")
except Exception as e:
    print(f"❌ Error importing app: {e}")

print("Verification complete.")
