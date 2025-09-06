import os
import sys
import webbrowser
import time
import threading
import socket
import requests
from pathlib import Path

from dotenv import load_dotenv


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


def run_streamlit_directly(streamlit_app_path, port, address):
	"""Run Streamlit directly by importing and calling it."""
	try:
		# Import streamlit modules
		import streamlit.web.cli as stcli
		import streamlit.runtime.scriptrunner as scriptrunner
		import streamlit.runtime.state as state
		
		# Set up the environment
		os.environ["STREAMLIT_SERVER_PORT"] = str(port)
		os.environ["STREAMLIT_SERVER_ADDRESS"] = address
		os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
		os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
		os.environ["STREAMLIT_SERVER_ENABLE_CORS"] = "false"
		os.environ["STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION"] = "false"
		
		# Change to the directory containing the streamlit app
		app_dir = os.path.dirname(streamlit_app_path)
		app_file = os.path.basename(streamlit_app_path)
		original_cwd = os.getcwd()
		os.chdir(app_dir)
		
		try:
			# Run streamlit
			sys.argv = ["streamlit", "run", app_file, "--server.port", str(port), "--server.address", address]
			stcli.main()
		finally:
			os.chdir(original_cwd)
			
	except Exception as e:
		print(f"ERROR: Failed to run Streamlit directly: {e}")
		raise


def main() -> None:
	print("Starting Web Form RPA Sender...")
	
	# Ensure working directory is project root (handles PyInstaller onefile extraction)
	if getattr(sys, "frozen", False):
		# When running as PyInstaller executable
		base_dir = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else Path(os.path.dirname(sys.executable))
		# Set working directory to the executable's directory, not the temp extraction directory
		os.chdir(Path(os.path.dirname(sys.executable)))
		# Ensure streamlit_app.py is in the working directory
		streamlit_app_path = Path(os.path.dirname(sys.executable)) / "streamlit_app.py"
		if not streamlit_app_path.exists():
			# Copy from temp directory if needed
			temp_app_path = base_dir / "streamlit_app.py"
			if temp_app_path.exists():
				import shutil
				print(f"Copying streamlit_app.py from {temp_app_path} to {streamlit_app_path}")
				shutil.copy2(temp_app_path, streamlit_app_path)
	else:
		base_dir = Path(__file__).resolve().parent
		os.chdir(base_dir)
		streamlit_app_path = base_dir / "streamlit_app.py"

	print(f"Working directory: {os.getcwd()}")
	print(f"Streamlit app path: {streamlit_app_path}")
	print(f"Streamlit app exists: {streamlit_app_path.exists()}")

	# Load .env if present (OpenRouter key, remote URL, etc.)
	load_dotenv()

	# Find an available port
	port = 8506
	for i in range(10):
		test_port = 8506 + i
		if is_port_available(test_port):
			port = test_port
			break
	
	address = "127.0.0.1"
	print(f"Using port: {port}")

	# Check if streamlit_app.py exists
	if not streamlit_app_path.exists():
		print(f"ERROR: streamlit_app.py not found at {streamlit_app_path}")
		print("Please ensure the file is in the same directory as the executable.")
		input("Press Enter to exit...")
		return

	print("Starting Streamlit...")
	
	# Start Streamlit in a separate thread
	streamlit_thread = threading.Thread(
		target=run_streamlit_directly,
		args=(str(streamlit_app_path), port, address),
		daemon=True
	)
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
		
		# Keep the main thread alive
		try:
			print("Streamlit is running. Press Ctrl+C to stop.")
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
