# API Documentation

This document describes the HTTP endpoints provided by the minimal CMS workflow server in `cms.api`.

## Authentication

Most endpoints require a bearer token. Obtain a token via `POST /test-token` with JSON:

```json
{"username": "tester"}
```

The response contains a `token` field. Provide it in the `Authorization` header:

```
Authorization: Bearer <token>
```

## Endpoints

### `GET /content-types`
Returns a list of supported content types.

### `GET /content-types/<type>`
List all content items for the given type. Without authentication only
published items are returned. If a valid bearer token is supplied, draft items
are included as well. The `<type>` parameter must match one of the values
returned by `GET /content-types`.

### `POST /content`
Create a new content item. The body must include a `type` field with one of the supported values as well as `created_by`, `created_at` and `timestamps`. Regardless of any provided value, newly created items start unpublished.

### `GET /content/<uuid>`
Retrieve a stored content item.

### `GET /content`
List content items across all types. Without authentication only published
items are returned. When authenticated, draft items are included.

### `PUT /content/<uuid>`
Update a content item. The `type` and all metadata fields are immutable via this endpoint.

### `DELETE /content/<uuid>`
Archive a content item. Items are not removed from the system.

### `POST /content/<uuid>/start-draft`
Begin editing an item. The request body should contain `user_uuid` and `timestamp`. A `403` is returned if another user already has the item in draft status.

### `POST /content/<uuid>/request-approval`
Mark an item as awaiting administrator approval. Requires `user_uuid` and `timestamp` in the body.

### `POST /content/<uuid>/approve`
Publish a piece of content. Requires `user_uuid` and `timestamp` in the body.

### `GET /pending-approvals`
List content items currently waiting for approval.

### `POST /check-metadata`
Validate that a content object contains the required metadata fields. Returns `{"ok": true}` on success.

### `POST /test-token`
Return a simple authentication token for the supplied username.

### `POST /categories`
Create a category. The body accepts `name` and optional `display_priority`.
Categories are flat and have no parent/child hierarchy.

### `GET /categories`
List all active categories sorted by display priority (1 is highest) then alphabetically.

### `GET /categories/<uuid>`
Retrieve a single category by UUID.

### `PUT /categories/<uuid>`
Update a category's `name` or `display_priority`.

### `DELETE /categories/<uuid>`
Archive a category without removing it from the system.

## Running the server

See `README.md` for instructions on starting the test server.
