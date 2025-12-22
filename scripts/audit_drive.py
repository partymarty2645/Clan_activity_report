
import os
import sys

# Add root to sys.path
sys.path.append(os.getcwd())
from core.config import Config

def audit():
    drive_path = Config.LOCAL_DRIVE_PATH
    print(f"--- DRIVE AUDIT ---")
    print(f"Configured Path: {drive_path}")
    
    if not drive_path:
        print("ERROR: LOCAL_DRIVE_PATH is not set.")
        return
        
    if not os.path.exists(drive_path):
        print(f"ERROR: Path does not exist!")
        return
        
    print("Contents:")
    try:
        items = os.listdir(drive_path)
        for item in items:
            print(f" - {item}")
            if item == 'assets':
                assets_path = os.path.join(drive_path, 'assets')
                if os.path.isdir(assets_path):
                    count = len(os.listdir(assets_path))
                    print(f"   (Contains {count} files)")
    except Exception as e:
        print(f"Error listing directory: {e}")

if __name__ == "__main__":
    audit()
