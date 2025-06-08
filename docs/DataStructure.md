# Data Structure

This document describes the JSON schema used for content items stored by the CMS workflow API.

```mermaid
classDiagram
    class Content {
        uuid: str
        title: str
        type: ContentType
        metadata: Metadata
        revisions: Revision[]
        published_revision: str
        draft_revision: str
        state: str
        archived: bool
        file: str
        pre_submission: bool
    }
    class Metadata {
        created_by: str
        created_at: str
        edited_by: str
        edited_at: str
        draft_requested_by: str
        draft_requested_at: str
        approved_by: str
        approved_at: str
        timestamps: str
    }
    class Revision {
        uuid: str
        last_updated: str
    }
    Content --> Metadata
    Content --> "1..*" Revision
```

## Fields

- **uuid** – unique identifier for the content item.
- **title** – human readable title.
- **type** – one of the values from `cms.types.ContentType`.
- **metadata** – object containing audit and workflow metadata. `created_by`, `created_at` and `timestamps` are required when creating new items.
- **revisions** – list of revision objects. Each revision includes a `uuid` and `last_updated` timestamp.
- **published_revision** – UUID of the currently published revision.
- **draft_revision** – UUID of the most recent draft revision.
- **state** – workflow state such as `Draft` or `AwaitingApproval`.
- **archived** – set to `true` if the item is no longer active.
- **file** – base64 encoded file contents (PDF only).
- **pre_submission** – boolean that indicates a newly created PDF has not yet been submitted for approval.

```mermaid
flowchart TD
    Draft -->|request approval| AwaitingApproval
    AwaitingApproval -->|approve| Published
    Draft -.->|archive| Archived
    Published -.->|archive| Archived
```

The API will automatically populate revision fields and enforce type validation as demonstrated in the tests.
