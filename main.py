import subprocess
import os
import sys

def main():
    print("Starting E2M Backend Server...")
    backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
    
    try:
        # Run the backend's main.py using the current python executable
        subprocess.run([sys.executable, "main.py"], cwd=backend_dir, check=True)
    except KeyboardInterrupt:
        print("\nServer stopped by user.")
    except Exception as e:
        print(f"Error starting server: {e}")

if __name__ == "__main__":
    main()
