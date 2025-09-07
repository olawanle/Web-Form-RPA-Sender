# Web Form RPA Sender - Client Instructions

## Quick Start

### Option 1: Automatic Installation (Recommended)
1. **Double-click `install_and_run.bat`**
   - This will automatically install all required packages
   - Then start the application

### Option 2: Manual Installation
1. **Install Python** (if not already installed)
   - Download from https://python.org
   - Make sure to check "Add Python to PATH" during installation

2. **Install packages**
   - Open Command Prompt in this folder
   - Run: `pip install -r requirements_client.txt`

3. **Start the application**
   - Double-click `start_app_standalone.bat`

## How to Use

1. **Start the application** using one of the methods above
2. **Upload your leads file** (CSV/Excel) with these columns:
   - `company_name` (required)
   - `inquiry_url` (required)
   - `contact_name` (optional)
   - `email` (optional)
   - `phone` (optional)
   - `subject` (optional)

3. **Upload or create a message template**
4. **Configure your settings** (daily cap, start time, etc.)
5. **Click "Run"** to start the RPA process

## Troubleshooting

### "Python is not installed" Error
- Download and install Python from https://python.org
- Make sure to check "Add Python to PATH" during installation

### "Failed to install packages" Error
- Check your internet connection
- Try running Command Prompt as Administrator
- Run: `pip install --upgrade pip` first

### Multiple Browser Tabs Opening
- Use `start_app_standalone.bat` instead of any `.exe` files
- This prevents the multiple tabs issue

## Files Included
- `start_app_standalone.bat` - Main application launcher
- `install_and_run.bat` - Automatic installation and launcher
- `requirements_client.txt` - Required Python packages
- `sample_leads.csv` - Example data format
- `templates/` - Message templates
- `form_rpa/` - RPA modules

## Support
If you encounter any issues, please contact the developer with:
- The error message you see
- Your operating system (Windows version)
- Whether you have Python installed
