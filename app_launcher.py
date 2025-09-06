import os
import sys
import subprocess
import webbrowser
from pathlib import Path

from dotenv import load_dotenv


def main() -> None:
	# Ensure working directory is project root (handles PyInstaller onefile extraction)
	if getattr(sys, "frozen", False):
		base_dir = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else Path(os.path.dirname(sys.executable))
		os.chdir(Path(os.path.dirname(sys.executable)))
	else:
		base_dir = Path(__file__).resolve().parent
		os.chdir(base_dir)

	# Load .env if present (OpenRouter key, remote URL, etc.)
	load_dotenv()

	# Prefer a consistent port for desktop
	port = os.environ.get("STREAMLIT_SERVER_PORT", "8506")
	address = os.environ.get("STREAMLIT_SERVER_ADDRESS", "127.0.0.1")

	cmd = [
		sys.executable,
		"-m",
		"streamlit",
		"run",
		"streamlit_app.py",
		"--server.port",
		str(port),
		"--server.address",
		str(address),
	]

	# Open browser proactively
	try:
		webbrowser.open(f"http://{address}:{port}")
	except Exception:
		pass

	subprocess.run(cmd, check=False)


if __name__ == "__main__":
	main()
