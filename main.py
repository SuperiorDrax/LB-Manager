# -*- coding: utf-8 -*-
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from views.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    # Set application-wide icon (affects taskbar and window)
    app.setWindowIcon(QIcon("icon.png"))
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()