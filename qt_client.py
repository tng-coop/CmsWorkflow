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

        main_layout = QHBoxLayout(central)

        self.type_list = QListWidget()
        self.item_list = QListWidget()
        self.output = QTextEdit()
        self.output.setReadOnly(True)

        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Content Types"))
        left_layout.addWidget(self.type_list)

        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Items"))
        right_layout.addWidget(self.item_list)
        right_layout.addWidget(QLabel("API Responses"))
        right_layout.addWidget(self.output)

        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)

        self.type_list.itemClicked.connect(self._load_items)
        self.item_list.itemClicked.connect(self._show_item)

    def _append_response(self, request_desc: str, data):
        self.output.append(request_desc)
        self.output.append(json.dumps(data, indent=2))
        self.output.append("")

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
        data = self.api.get_content(uuid)
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
