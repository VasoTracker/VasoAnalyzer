# ===== Main Launcher =====
import sys
import os
from PyQt5.QtWidgets import QApplication, QSplashScreen
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt, QTimer

from vasoanalyzer.gui import VasoAnalyzerApp  # <-- updated import!

class VasoAnalyzerLauncher:
    def __init__(self):
        self.app = QApplication(sys.argv)

        # === Show Splash Screen ===
        splash_path = os.path.join(os.path.dirname(__file__), 'vasoanalyzer', 'VasoAnalyzer Splash Screen.png')
        splash_pix = QPixmap(splash_path).scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
        self.splash.setMask(splash_pix.mask())
        self.splash.show()

        # === Launch Main App ===
        QTimer.singleShot(2500, self.start_main_app)

    def start_main_app(self):
        self.splash.close()
        self.window = VasoAnalyzerApp()
        self.window.show()

    def run(self):
        sys.exit(self.app.exec_())

if __name__ == "__main__":
    launcher = VasoAnalyzerLauncher()
    launcher.run()
