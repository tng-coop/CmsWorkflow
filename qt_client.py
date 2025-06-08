import sys
import json
import logging
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QTextEdit,
    QLabel,
    QPushButton,
    QMenu,
)
from PyQt5.QtCore import Qt

from cms.api import start_test_server
from cms.client_api import ApiClient, seed_server


class CmsWindow(QMainWindow):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self.setWindowTitle("CMS PyQt Test Client")
        self._setup_ui()
        self._load_content_types()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)

        toolbar = QHBoxLayout()
        self.status_label = QLabel()
        self.logout_btn = QPushButton("Logout")
        self.login_editor_btn = QPushButton("Login as Editor")
        self.login_admin_btn = QPushButton("Login as Admin")
        toolbar.addWidget(self.logout_btn)
        toolbar.addWidget(self.login_editor_btn)
        toolbar.addWidget(self.login_admin_btn)
        toolbar.addWidget(self.status_label)
        toolbar.addStretch()

        content_layout = QHBoxLayout()

        self.type_list = QListWidget()
        self.item_list = QListWidget()
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setContextMenuPolicy(Qt.CustomContextMenu)
        self.output.customContextMenuRequested.connect(self._show_output_context_menu)

        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Content Types"))
        left_layout.addWidget(self.type_list)

        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Items"))
        right_layout.addWidget(self.item_list)
        right_layout.addWidget(QLabel("API Responses"))
        right_layout.addWidget(self.output)

        content_layout.addLayout(left_layout)
        content_layout.addLayout(right_layout)

        main_layout.addLayout(toolbar)
        main_layout.addLayout(content_layout)

        self.type_list.itemClicked.connect(self._load_items)
        self.item_list.itemClicked.connect(self._show_item)
        self.logout_btn.clicked.connect(self._logout)
        self.login_editor_btn.clicked.connect(lambda: self._login("editor"))
        self.login_admin_btn.clicked.connect(lambda: self._login("admin"))

        self._update_status()

    def _append_response(self, request_desc: str, data):
        self.output.append(request_desc)
        self.output.append(json.dumps(data, indent=2))
        self.output.append("")

    def _clear_output(self):
        """Clear the API response panel."""
        self.output.clear()

    def _show_output_context_menu(self, position):
        menu = self.output.createStandardContextMenu()
        menu.addSeparator()
        clear_action = menu.addAction("Clear")
        clear_action.triggered.connect(self._clear_output)
        menu.exec_(self.output.mapToGlobal(position))

    def _update_status(self):
        if self.api.username:
            self.status_label.setText(f"Logged in as {self.api.username}")
        else:
            self.status_label.setText("Logged out")

    def _login(self, username: str):
        token = self.api.create_token(username)
        self._append_response("POST /test-token", {"token": token})
        self._update_status()

    def _logout(self):
        self.api.logout()
        self._append_response("LOGOUT", {"token": None})
        self._update_status()

    def _load_content_types(self):
        types = self.api.get_content_types()
        self._append_response("GET /content-types", types)
        self.type_list.clear()
        for ct in types:
            self.type_list.addItem(ct)

    def _load_items(self, item):
        ct = item.text()
        items = self.api.list_content_by_type(ct)
        self._append_response(f"GET /content-types/{ct}", items)
        self.item_list.clear()
        for obj in items:
            lw_item = f"{obj['uuid']} - {obj.get('title', '')}"
            self.item_list.addItem(lw_item)
            self.item_list.item(self.item_list.count() - 1).setData(Qt.UserRole, obj['uuid'])

    def _show_item(self, item):
        uuid = item.data(Qt.UserRole)
        try:
            data = self.api.get_content(uuid)
        except Exception as exc:
            self._append_response(f"GET /content/{uuid} ERROR", {"error": str(exc)})
        else:
            self._append_response(f"GET /content/{uuid}", data)


def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
    )
    server, _ = start_test_server(0)
    base_url = f"http://localhost:{server.server_port}"
    api = ApiClient(base_url)
    seed_server(api)

    app = QApplication(sys.argv)
    window = CmsWindow(api)
    window.resize(800, 600)
    window.show()
    app.exec_()
    server.shutdown()


if __name__ == "__main__":
    main()
