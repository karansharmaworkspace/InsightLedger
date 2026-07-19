import torch # MUST IMPORT BEFORE PYQT6 TO AVOID DLL CONFLICT (WinError 1114)
import os
import sys
import traceback

# Ensure the root directory is in the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gui.dashboard import DPIDDashboard
from PyQt6.QtWidgets import QApplication

def main():
    try:
        print("Launching DPID AI Master Dashboard [Instrumentation Active]...")
        app = QApplication(sys.argv)
        window = DPIDDashboard()
        window.show()
        sys.exit(app.exec())
    except Exception:
        with open("CRITICAL_FAULT.log", "w") as f:
            f.write(traceback.format_exc())
        print("!!! CRITICAL FAULT DETECTED. See CRITICAL_FAULT.log !!!")

if __name__ == "__main__":
    main()
