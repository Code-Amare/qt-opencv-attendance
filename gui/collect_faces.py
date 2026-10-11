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
    QHBoxLayout,
    QLineEdit,
    QGraphicsBlurEffect,
    QStackedWidget,
    QLabel,
    QPushButton,
    QMessageBox,
    QAction,
    QShortcut,
)
from pyqtspinner.spinner import WaitingSpinner
from PyQt5.QtGui import QColor, QKeySequence
from PyQt5.QtCore import Qt, pyqtSignal, QAbstractTableModel, QModelIndex
from utils import TitleBar, icon_from_svg, get_image, default_avatar

# Helper Classes

# dashboard user table
class UserModel(QAbstractTableModel):
    HEADERS = ["Id", "First Name", "Last Name", "Face Status", "Actions"]
    def __init__(self, window):
        super().__init__()
        self.window_ = window
        self._users:list[dict] = []

    def set_users(self, users):
        self._users = users

    def rowCount(self, parent =QModelIndex()):
        return 0 if parent.isValid() else len(self._users)

    def columnCount(self, parent = QModelIndex()):
        return 0 if parent.isValid() else len(self.HEADERS)

    def headerData(self, section, orientation, role = Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.HEADERS

    async def load_users_data(self):
        self.window_.show_loader()
        try:
            async with self.window_.session.get(self.window_.USERS_DATA) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except ApiError as e:
            print(e)
        except aiohttp.ClientResponseError as e:
            print(e)
        finally:
            self.window_.hide_loader()




    def update_users(self, users):
        self.beginResetModel()
        self._users = users
        self.endResetModel()







class ApiError(Exception):
    pass

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
        self.isAuthenticated = False
        self.profile_pic_url = ""
        self.profile_pic = None


    async def get_profile_pic(self):
        pix = None
        if self.profile_pic_url:
            pix = await get_image(self.profile_pic_url)
        self.profile_pic = pix or default_avatar()

    def add_tokens(self, data, session):
        tokens = data["tokens"]
        self.access = tokens["access"]
        self.refresh = tokens["refresh"]
        self.csrf = tokens["csrf"]
        self.isAuthenticated = True

        user = data["user"]  # adjust to match your printout
        self.id = user["id"]
        self.username = user["username"]
        self.email = user["email"]
        self.first_name = user["first_name"]
        self.last_name = user["last_name"]
        self.profile_pic_url = user["profile_picture"]

        self.update_headers(session)

    async def login(self, username_or_email, password, session):
        try:
            async with session.post("users/login/", json={
                "username_or_email": username_or_email,
                "password": password,
            }) as resp:
                try:
                    data = await resp.json()
                except aiohttp.ContentTypeError:
                    data = {}
                if resp.status >= 400:
                    return False, data.get("error") or "Login failed"
        except aiohttp.ClientError:
            return False, "Server error"
        self.add_tokens(data, session)
        return True, ""

    async def refresh_tokens(self, session):
        try:
            async with session.post("users/refresh/", json={"refresh": self.refresh}) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except aiohttp.ClientError:
            self.logout()
            return False
        self.add_tokens(data, session)
        return True

    @asyncSlot()
    async def refresh_tokens(self, session):
        try:
            async with session.post("users/refresh/", json={"refresh": self.refresh}) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except aiohttp.ClientResponseError as e:
            print(e)
            self.logout()
        finally:
            self.add_tokens(data, session)
            print(data)

    def logout(self):
        self.access = ""
        self.refresh = ""
        self.csrf = ""
        self.isAuthenticated = False

    def get_user(self):
        if not self.isAuthenticated:
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

class LoginPage(QWidget):
    login_successful = pyqtSignal()

    def __init__(self, window):
        super().__init__()
        self.window_ = window
        layout = QVBoxLayout(self)

        self.welcome_text = QLabel(f"Welcome to {self.window_.PRODUCT_NAME}")
        self.welcome_text.setAlignment(Qt.AlignCenter)
        self.welcome_text.setStyleSheet("font-size: 40px; font-weight: 400")

        self.username_or_email = QLineEdit()
        self.username_or_email.setPlaceholderText("Username or Email")

        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")

        self.error_message = QLabel("")
        self.error_message.setStyleSheet("""
            color: #d20c0c;
            font-size: 18px;
        """)

        self.login_btn = QPushButton("Login")
        self.login_btn.clicked.connect(self.on_login_click)

        self.enter_shortcut = QShortcut(QKeySequence(Qt.Key_Return), self)
        self.enter_shortcut.activated.connect(self.on_login_click)
        # self.login_btn.
        form_widget = QWidget()
        form_widget.setMaximumWidth(560)
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(0, 0, 0, 0)

        self.username_or_email.setFixedWidth(360)
        self.password.setFixedWidth(360)
        self.login_btn.setFixedWidth(360)
        self.login_btn.setStyleSheet("margin: 0 0 100px 0")
        self.login_btn.setCursor(Qt.PointingHandCursor)

        for w in (self.username_or_email, self.password, self.error_message, self.login_btn):
            form_layout.addWidget(w)

        layout.addWidget(self.welcome_text)
        layout.addWidget(form_widget, alignment=Qt.AlignHCenter)

    @asyncSlot()
    async def on_login_click(self):
        self.window_.show_loader()
        try:
            ok, msg = await self.window_.auth.login(
                self.username_or_email.text(), self.password.text(), self.window_.session
            )
        finally:
            self.window_.hide_loader()
        if ok:
            self.login_successful.emit()
        else:
            self.error_message.setText(msg)

class DashboardPage(QWidget):

    def __init__(self, window):
        super().__init__()

        self.window_ = window

        self.initUi()

    def initUi(self):

        layout = QHBoxLayout(self)
        sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_widget)
        nav_widget = QWidget()
        nav_layout = QHBoxLayout(nav_widget)

        self.nav_welcome_label = QLabel("")
        self.avatar = QLabel()
        self.avatar.setFixedSize(48, 48)
        self.avatar.setScaledContents(True)

        self.sidebar_dashboard_btn = QPushButton("Dashboard")
        self.sidebar_enrolled_faces_btn = QPushButton("Enrolled Faces")

        sidebar_layout.addWidget(self.sidebar_dashboard_btn)
        sidebar_layout.addWidget(self.sidebar_enrolled_faces_btn)
        sidebar_layout.addStretch()

        nav_layout.addWidget(self.nav_welcome_label)
        nav_layout.addStretch()
        nav_layout.addWidget(self.avatar)

        layout.addWidget(sidebar_widget)
        layout.addWidget(nav_widget)
        layout.addStretch()  # the rest of the dashboard goes here

    async def refresh(self):
        auth = self.window_.auth
        await auth.get_profile_pic()

        self.nav_welcome_label.setText(f"Welcome, {auth.first_name}")
        self.avatar.setPixmap(auth.profile_pic)


# Main Window

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.TITLE_HEIGHT = 48
        self.closed = asyncio.Event()

        self.auth = AuthContext()
        self.session = None
        self.BASE_URL = "http://localhost:8000/api/"
        self.CHECK_USER_URL = f"{self.BASE_URL}users/check/"
        self.PRODUCT_NAME = "FaceCall"

        self.setGeometry(0, 0, 1280, 720)
        self.setWindowTitle(self.PRODUCT_NAME)
        self.setWindowIcon(icon_from_svg())

        self.initUi()
        self.center()

    def initUi(self):
        container = QWidget()
        container.setObjectName("central")
        self.setCentralWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Title bar on top, pages below
        layout.addWidget(TitleBar(self))
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # Loader overlay
        self.overlay = QWidget(container)
        self.overlay.setObjectName("overlay")
        self.overlay.setAttribute(Qt.WA_StyledBackground, True)
        self.overlay.setStyleSheet("#overlay { background: rgba(255, 255, 255, 10); }")
        self.overlay.hide()

        self.spinner = WaitingSpinner(
            self.overlay,
            roundness=100.0, fade=80.0, radius=20, lines=20,
            line_length=10, line_width=4, speed=1.0,
            color=QColor(191, 0, 255),
        )

        # Pages
        self.login_page = LoginPage(self)
        self.dashboard_page = DashboardPage(self)


        self.stack.addWidget(self.login_page)
        self.stack.addWidget(self.dashboard_page)

        self.login_page.login_successful.connect(self.on_login_successful)


        # Title bar styles live in TitleBar itself
        self.setStyleSheet("""
            QMainWindow, QWidget#central { background: #1d1b1e; }
            QLabel { color: #F8FAFC; font-size: 24px; font-family: poppins}
            QLineEdit { background: #2f2c31; color: #F8FAFC; border: 1px solid #363138; border-radius: 6px; padding: 8px 8px 8px 16px; font-size: 20px}
            QPushButton { background: #5d0b9a; color: #fff; border-radius: 6px; padding: 8px; font-size: 18px; font-family: poppins}
            QPushButton:hover { background: #3f114e; }
        """)

    @asyncSlot()
    async def on_login_successful(self):
        self.show_loader()
        try:
            await self.dashboard_page.refresh()
        finally:
            self.hide_loader()
        self.stack.setCurrentWidget(self.dashboard_page)

    def center(self):
        geo = self.frameGeometry()
        geo.moveCenter(QApplication.primaryScreen().availableGeometry().center())
        self.move(geo.topLeft())

    def _layout_overlay(self):
        rect = self.centralWidget().rect()
        self.overlay.setGeometry(0, self.TITLE_HEIGHT, rect.width(), rect.height() - self.TITLE_HEIGHT)
        self.spinner.move(
            (self.overlay.width() - self.spinner.width()) // 2,
            (self.overlay.height() - self.spinner.height()) // 2,
        )

    def show_loader(self):
        blur = QGraphicsBlurEffect()
        blur.setBlurRadius(2)

        self.stack.setGraphicsEffect(blur)
        self.stack.setEnabled(False)

        self._layout_overlay()
        self.overlay.show()
        self.overlay.raise_()
        self.spinner.start()

    def hide_loader(self):
        self.spinner.stop()
        self.overlay.hide()
        self.stack.setGraphicsEffect(None)
        self.stack.setEnabled(True)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.overlay.isVisible():
            self._layout_overlay()

    def closeEvent(self, event):
        self.closed.set()
        event.accept()

async def main(window):
    app_close = asyncio.Event()
    app.aboutToQuit.connect(app_close.set)

    window.session = aiohttp.ClientSession(
        base_url=window.BASE_URL,
        headers={
            "Authorization": "",
            "X-CSRFToken": "",
        },)

    await window.closed.wait()      # window was closed
    await window.session.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow()
    window.show()

    with loop:
        loop.run_until_complete(main(window))