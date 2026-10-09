import sys
import os
import cv2
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QMainWindow, QVBoxLayout

from PyQt5.QtCore import QTimer


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.welcome_label = QLabel("Hello")
        self.setGeometry(0, 0, 1280, 720)
        self.setWindowTitle("Collect Faces")

        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.addWidget(self.welcome_label)
        self.setCentralWidget(central_widget)
        print(self.get_user_ids())

    def get_user_ids(self):
        folders = os.listdir("./train-pics")
        user_ids = [int(folder.split("=")[1]) for folder in folders]
        return user_ids

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
