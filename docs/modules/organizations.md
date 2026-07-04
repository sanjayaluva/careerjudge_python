# Organizations Module — v1.0.0 (Frozen)

> **Frozen since**: 2026-07-02
> **Version**: v1.0.0
> **Phase**: 2 (complete)
> **Test coverage**: 82%

## Overview

The organizations module provides multi-tenancy for CareerJudge. It supports three organization types (corporate, corp_exclusive, channel_partner) with hierarchical grouping via Groups and membership management via OrganizationMember.

## Public API (contractually stable)

### Organization endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/organizations/` | List organizations (filtered by user's access) |
| POST | `/api/organizations/` | Create organization (cj_admin, corp_admin) |
| GET | `/api/organizations/:id/` | Retrieve organization detail |
| PATCH | `/api/organizations/:id/` | Update organization |
| DELETE | `/api/organizations/:id/` | Delete organization (cj_admin only) |

### Group endpoints (nested under organization)

| Method | Path | Description |
|---|---|---|
| GET | `/api/organizations/:id/groups/` | List groups in an organization |
| POST | `/api/organizations/:id/groups/` | Create group |
| PATCH | `/api/organizations/:id/groups/:gid/` | Update group |
| DELETE | `/api/organizations/:id/groups/:gid/` | Delete group |

### Member endpoints (nested under organization)

| Method | Path | Description |
|---|---|---|
| GET | `/api/organizations/:id/members/` | List members |
| POST | `/api/organizations/:id/members/` | Add member |
| PATCH | `/api/organizations/:id/members/:mid/` | Update member (e.g. toggle admin) |
| DELETE | `/api/organizations/:id/members/:mid/` | Remove member |

## Models

- **Organization**: name, type (corporate/corp_exclusive/channel_partner), description, is_active
- **Group**: name, organization (FK), description — sub-grouping within an org
- **OrganizationMember**: user (FK), organization (FK), group (FK, optional), is_admin — membership link

## Frontend

- **OrganizationsPage** (`/organizations`): list page with cards + create modal
- **OrganizationDetailPage** (`/organizations/:id`): detail with tabs (overview, groups, members)
- Embedded in sidebar nav for cj_admin, corp_admin, corp_exclusive

## Permissions

| Role | View | Create | Edit | Delete |
|---|---|---|---|---|
| cj_admin | ✅ all | ✅ | ✅ all | ✅ all |
| corp_admin | ✅ own | ✅ | ✅ own | ❌ |
| corp_exclusive | ✅ own | ❌ | ✅ own | ❌ |
| individual | ❌ | ❌ | ❌ | ❌ |

## Frozen contract

This module is frozen at v1.0.0. Changes are additive only — no breaking changes to existing API endpoints, model fields, or permissions. See [MODULE_FREEZE.md](../MODULE_FREEZE.md) for the freeze policy.
