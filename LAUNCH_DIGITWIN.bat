@echo off
TITLE DigiTwin P&ID Digitization Suite - Industrial Neural Interface
echo [SYSTEM] Initializing Digitwin Neural Engine...
echo [SYSTEM] Calibrating Titan-Glance Scales (3072px - 4096px)...

:: Set Python Path for module resolution
set PYTHONPATH=.

:: Launch the Dashboard
python launch_ui.py

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] System crash detected. Please check your .env and Python environment.
    pause
)
