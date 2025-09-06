#!/usr/bin/env python3
"""
Launcher for Web Form RPA Sender that opens only one browser tab
"""

import os
import sys
import webbrowser
import time
import threading
import socket
import requests
import subprocess
from pathlib import Path


def is_port_available(port):
    """Check if a port is available."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) != 0


def wait_for_streamlit(address, port, timeout=30):
    """Wait for Streamlit to be ready."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"http://{address}:{port}", timeout=2)
            if response.status_code == 200:
                return True
        except:
            pass
        time.sleep(1)
    return False


def main():
    print("Starting Web Form RPA Sender...")
    print()
    
    # Check if streamlit_app.py exists
    if not os.path.exists("streamlit_app.py"):
        print("ERROR: streamlit_app.py not found")
        print("Please ensure this file is in the same directory as this script.")
        input("Press Enter to exit...")
        return
    
    # Check if form_rpa directory exists
    if not os.path.exists("form_rpa"):
        print("ERROR: form_rpa directory not found")
        print("Please ensure this directory is in the same directory as this script.")
        input("Press Enter to exit...")
        return
    
    # Find an available port
    port = 8506
    for i in range(10):
        test_port = 8506 + i
        if is_port_available(test_port):
            port = test_port
            break
    
    address = "127.0.0.1"
    print(f"Using port: {port}")
    print()
    
    # Check if virtual environment exists
    venv_path = Path("..") / ".venv" / "Scripts" / "python.exe"
    if not venv_path.exists():
        print("ERROR: Virtual environment not found")
        print("Please run the build script first to create the virtual environment.")
        input("Press Enter to exit...")
        return
    
    print("Starting Streamlit server...")
    
    # Start Streamlit with browser disabled
    cmd = [
        str(venv_path),
        "-m", "streamlit", "run", "streamlit_app.py",
        "--server.port", str(port),
        "--server.address", address,
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--server.runOnSave", "false"
    ]
    
    # Start Streamlit in background
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    print("Waiting for Streamlit to start...")
    
    # Wait for Streamlit to be ready
    if wait_for_streamlit(address, port, timeout=30):
        print(f"Streamlit is ready! Opening browser at http://{address}:{port}")
        try:
            webbrowser.open(f"http://{address}:{port}")
        except Exception as e:
            print(f"Failed to open browser: {e}")
            print(f"Please manually open: http://{address}:{port}")
        
        print()
        print("Web Form RPA Sender is now running!")
        print("To stop the application, press Ctrl+C")
        print()
        
        # Keep the main thread alive
        try:
            process.wait()
        except KeyboardInterrupt:
            print("\nStopping...")
            process.terminate()
            process.wait()
    else:
        print("ERROR: Streamlit failed to start within 30 seconds")
        process.terminate()
        process.wait()
        input("Press Enter to exit...")
        return


if __name__ == "__main__":
    main()
