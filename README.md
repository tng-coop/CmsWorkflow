# CMS Workflow Example

This repository contains a minimal content management workflow implemented in Python. The package lives in the `cms` directory and includes:

- A small HTTP CRUD API (`cms/api.py`).
- Helper functions for managing draft/approval workflow (`cms/workflow.py`).
- Simple data factories in `cms/data.py`.
- Unit tests under `tests/` using `pytest`.

The code only relies on the Python standard library and `pytest` for tests.

## Running the Tests

Install `pytest` if it is not already available:

```bash
pip install pytest
```

Then execute the test suite from the repository root:

```bash
pytest
```

All tests should pass and exercise the workflow helpers as well as the CRUD API.

## Running the Example API Server

`cms.api` exposes a helper `start_test_server` used by the tests. You can run the same HTTP server manually using a short Python snippet:

```bash
python - <<'PY'
from cms.api import start_test_server
server, thread = start_test_server(8000)
print(f"Server running on http://localhost:{server.server_port}")
try:
    thread.join()
except KeyboardInterrupt:
    server.shutdown()
PY
```

The server listens for JSON requests on endpoints such as:

- `POST /content` – create a new content item.
- `GET /content/<uuid>` – retrieve a stored item.
- `PUT /content/<uuid>` – update an item.
- `DELETE /content/<uuid>` – remove an item.

## Using the Workflow Helpers

The functions in `cms.workflow` manage draft state and approval metadata. Example usage:

```python
from cms.data import seed_users, sample_content
from cms.workflow import start_draft, request_approval

users = seed_users()
content = sample_content(users)
content = start_draft(content, users["editor"], "2025-06-09T10:00:00")
content = request_approval(content, users["editor"], "2025-06-09T10:15:00")
```

See the tests in the `tests` directory for more examples.
