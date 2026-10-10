import asyncio
import sys
import os
import asyncio

import aiohttp
from qasync import QEventLoop, asyncSlot
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QMainWindow,
    QVBoxLayout,
    QLineEdit,
    QGraphicsBlurEffect,
    QStackedWidget,
    QLabel,
    QPushButton,
)
from pyqtspinner.spinner import WaitingSpinner
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt

class AuthContext:
    def __init__(self):
        self.id = None
        self.username = ""
        self.email = ""
        self.first_name = ""
        self.last_name = ""
        self.access = ""
        self.refresh = ""
        self.csrf = ""

    def add_tokens(self, data, session):
        self.access = data["access"]
        self.refresh = data["refresh"]
        self.csrf = data["csrf"]

        self.update_headers(session)

    @asyncSlot()
    async def login_handler(self, username_or_email, password, session, window):
        window.show_loader()
        try:
            async with session.post("users/login/", json={
                "username_or_email": username_or_email,
                "password": password

            }) as resp:
                resp.raise_for_status()
                data = await resp.json()
                self.add_tokens(data["data"], session)
        except aiohttp.ClientResponseError as e:
            print(e.status, e)

        finally:
            print(data)
            window.hide_loader()

    @asyncSlot()
    async def refresh_tokens(self, session):
        try:
            async with session.post("users/refresh/", json={"refresh": self.refresh}) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except aiohttp.ClientResponseError as e:
            print(e)
        finally:
            self.access = data["access"]
            self.refresh = data["refresh"]

            self.update_headers(session)
            print(data)

    def logout(self):
        self.access = ""
        self.refresh = ""
        self.csrf = ""

    def get_user(self):
        if not self.id:
            return None
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
        }

    def update_headers(self, session):
        session.headers.update({
            "Authorization": f"Bearer {self.access}" if self.access else "",
            "X-CSRFToken": self.csrf,
        })


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.auth = AuthContext()
        self.session = None
        self.BASE_URL = "http://localhost:8000/api/"
        self.CHECK_USER_URL = f"{self.BASE_URL}/users/check/"
        self.PRODUCT_NAME = "FaceCall"

        self.setGeometry(0, 0, 1280, 720)
        self.setWindowTitle("Collect Faces")

        self.initUi()

        self.center()

    def initUi(self):
        container = QWidget()
        self.setCentralWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        self.overlay = QWidget(container)
        self.overlay.setObjectName("overlay")
        self.overlay.setAttribute(Qt.WA_StyledBackground, True)
        self.overlay.setStyleSheet("#overlay { background: rgba(255, 255, 255, 120); }")
        self.overlay.hide()

        self.spinner = WaitingSpinner(
            self.overlay,
            roundness=100.0, fade=80.0, radius=20, lines=20,
            line_length=10, line_width=4, speed=1.0,
            color=QColor(191, 0, 255),
        )

        home_page = QWidget()
        page_layout = QVBoxLayout(home_page)
        self.username_or_email_line_edit = QLineEdit()
        self.password_line_edit = QLineEdit()
        welcome_label = QLabel(f"Welcome to {self.PRODUCT_NAME}")
        page_layout.addWidget(welcome_label)
        page_layout.addWidget(self.username_or_email_line_edit)
        page_layout.addWidget(self.password_line_edit)
        login_btn = QPushButton("Load")
        login_btn.clicked.connect(
            lambda: self.auth.login_handler(
                        self.username_or_email_line_edit.text(),
                        self.password_line_edit.text(),
                        self.session,
                        self,
                    )
            )
        page_layout.addWidget(login_btn)
        self.stack.addWidget(home_page)


    def center(self):
        geo = self.frameGeometry()
        geo.moveCenter(QApplication.primaryScreen().availableGeometry().center())
        self.move(geo.topLeft())

    def show_loader(self):
        blur = QGraphicsBlurEffect()
        blur.setBlurRadius(2)

        self.stack.setGraphicsEffect(blur)
        self.stack.setEnabled(False)

        self.overlay.setGeometry(self.centralWidget().rect())
        self.overlay.show()
        self.overlay.raise_()
        self.spinner.start()

    def hide_loader(self):
        self.spinner.stop()
        self.overlay.hide()
        self.stack.setGraphicsEffect(None)
        self.stack.setEnabled(True)


    @asyncSlot()
    async def start_spinner(self):
        self.show_loader()
        try:
            await asyncio.sleep(4)
        finally:
            self.hide_loader()

async def main(window):
    app_close = asyncio.Event()
    app.aboutToQuit.connect(app_close.set)

    window.session = aiohttp.ClientSession(
        base_url=window.BASE_URL,
        headers={
            "Authorization": "",
            "X-CSRFToken": "",
        },)

    await app_close.wait()          # wait until the app quits
    await window.session.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow()
    window.show()

    with loop:
        loop.run_until_complete(main(window))
    sys.exit(app.exec_())