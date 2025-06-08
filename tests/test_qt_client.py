import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

PyQt5 = pytest.importorskip("PyQt5")
from PyQt5.QtWidgets import QApplication
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt

from cms.api import start_test_server
from cms.client_api import ApiClient, seed_server
from qt_client import CmsWindow


@pytest.fixture()
def qt_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    yield app
    app.quit()


@pytest.fixture()
def cms_window(qt_app):
    server, thread = start_test_server(0)
    base_url = f"http://localhost:{server.server_port}"
    api = ApiClient(base_url)
    seed_server(api)
    window = CmsWindow(api)
    yield window
    server.shutdown()
    thread.join()


def test_load_content_and_show_item(qt_app, cms_window):
    # initially content types are loaded
    num_types = cms_window.type_list.count()
    assert num_types > 0

    # click the first content type to load items
    first_type = cms_window.type_list.item(0)
    rect = cms_window.type_list.visualItemRect(first_type)
    QTest.mouseClick(cms_window.type_list.viewport(), Qt.LeftButton, pos=rect.center())
    qt_app.processEvents()
    assert cms_window.item_list.count() > 0

    # click first item to load details
    first_item = cms_window.item_list.item(0)
    rect = cms_window.item_list.visualItemRect(first_item)
    QTest.mouseClick(cms_window.item_list.viewport(), Qt.LeftButton, pos=rect.center())
    qt_app.processEvents()

    assert "GET /content/" in cms_window.output.toPlainText()
