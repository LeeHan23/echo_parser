@echo off
echo Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller

echo Building Executable...
pyinstaller --noconsole --onefile --name "EchoReportParser" gui_app.py

echo Done! Check the dist/ folder.
pause
