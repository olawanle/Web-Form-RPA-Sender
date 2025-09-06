#!/usr/bin/env python3
"""
Simple launcher for Web Form RPA Sender
This script runs the Streamlit app directly without PyInstaller complications.
"""

import os
import sys
import webbrowser
import time
import threading
import socket
import requests
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


def run_streamlit():
    """Run Streamlit in the current process."""
    try:
        # Import and run streamlit
        import streamlit.web.cli as stcli
        
        # Set up the environment
        os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
        os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
        os.environ["STREAMLIT_SERVER_ENABLE_CORS"] = "false"
        os.environ["STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION"] = "false"
        
        # Set up sys.argv for streamlit
        original_argv = sys.argv.copy()
        sys.argv = ["streamlit", "run", "streamlit_app.py"]
        
        try:
            stcli.main()
        finally:
            sys.argv = original_argv
            
    except Exception as e:
        print(f"ERROR: Failed to run Streamlit: {e}")
        raise


def main():
    print("Starting Web Form RPA Sender...")
    print()
    
    # Check if streamlit_app.py exists
    if not os.path.exists("streamlit_app.py"):
        print("ERROR: streamlit_app.py not found")
        print("Please ensure this file is in the same directory as this script.")
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
    
    # Set the port environment variable
    os.environ["STREAMLIT_SERVER_PORT"] = str(port)
    os.environ["STREAMLIT_SERVER_ADDRESS"] = address
    
    print("Starting Streamlit server...")
    
    # Start Streamlit in a separate thread
    streamlit_thread = threading.Thread(target=run_streamlit, daemon=True)
    streamlit_thread.start()
    
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
            while streamlit_thread.is_alive():
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping...")
            sys.exit(0)
    else:
        print("ERROR: Streamlit failed to start within 30 seconds")
        input("Press Enter to exit...")
        return


if __name__ == "__main__":
    main()
