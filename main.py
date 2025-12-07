# -*- coding: utf-8 -*-
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from views.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    # Set application name (affects window title on some systems)
    app.setApplicationName("LB Manager")
    app.setApplicationDisplayName("LB Manager")
    
    # Set application-wide icon
    # Note: Use absolute path or ensure icon.png is in the same directory
    try:
        app.setWindowIcon(QIcon("icon.png"))
    except:
        print("Icon file not found, using default icon")
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()