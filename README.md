# CMS Workflow Example

This repository contains a minimal content management workflow implemented in Python. The package lives in the `cms` directory and includes:

- A small HTTP CRUD API (`cms/api.py`).
- Helper functions for managing draft/approval workflow (`cms/workflow.py`).
- Simple data factories in `cms/data.py`.
- Unit tests under `tests/` using `pytest`.

The code only relies on the Python standard library and `pytest` for tests.

## Content Structure

Each content item stored by the API contains:

1. A content `type` from `cms.types.ContentType`.
2. A unique `uuid` identifying the content.
3. A list of `revisions`. Each revision entry stores:
   - a `uuid` identifying that revision,
   - a `last_updated` timestamp,
   - and a dictionary of type-specific `attributes`.
4. References to the `published_revision` and `review_revision` by UUID. These
   fields are ``null`` when content is first created.

The helper `cms.data.sample_content` returns an example object with this
structure. When creating content, the API leaves the revision references
unset so new items begin in the ``Draft`` state. A full breakdown of all
fields can be found in
[docs/DataStructure.md](docs/DataStructure.md).

## Supported Content Types

The API works with four distinct content types defined in `cms.types.ContentType`.
All content types share the same metadata and revision structure:

1. `html`
2. `pdf`
3. `office address`
4. `event schedule`

Requests that create or update content must specify one of these values for the
`type` field.

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
- `DELETE /content/<uuid>` – archive an item without removing it.
- `POST /test-token` – obtain a test API token for a username.

All content endpoints require an `Authorization` header of the form `Bearer <token>`.
Tokens are retrieved via the `/test-token` endpoint and are only intended for testing.
For a complete list of endpoints and their payloads, see [docs/API.md](docs/API.md).

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

## PyQt Test Client

The repository includes a small PyQt5 GUI (`qt_client.py`) that demonstrates the
HTTP API. Running the script starts the test server, seeds it with example data
from `cms.data`, and lets you browse content items. Each user action shows the
underlying API request and JSON response in a log panel.

Run the client with:

```bash
python qt_client.py
```
