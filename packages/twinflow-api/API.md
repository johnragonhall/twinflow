---
title: twinflow-api API
description: Every public symbol twinflow-api owns, which boundary rule A1.4 requires each package to list.
topic_type: reference
audience: contributors
---

# twinflow-api API

Boundary rule A1.4 gives every public symbol exactly one owning package. These
are the names this package owns. Gate `IMPORT-3` fails when `__all__` and this
package's declared ownership disagree.

## The application

| Symbol              | Kind     | What it is                                                        |
| ------------------- | -------- | ----------------------------------------------------------------- |
| `create_api`        | function | Build the ASGI app over one set of recorded runs and one clock    |
| `openapi_document`  | function | The OpenAPI 3.1 document as a dictionary, with no server running  |
| `API_PREFIX`        | constant | `/api/v1`, the URL major of the REST contract                     |
| `UNVERSIONED_PATHS` | constant | The three paths section 5.13 puts outside the versioned prefix    |
| `NOT_INSTALLED`     | constant | Declared routes this release does not build, each with its reason |
| `ConfigProposal`    | class    | The body `POST /api/v1/config` accepts                            |
| `APPLY_TIER`        | constant | The autonomy tier at which `config:apply` is grantable at all     |
| `CONFIG_APPLY_TOOL` | constant | The tool name an autonomy grant would have to name in its scope   |

`create_api` rather than `create_app`, because `twinflow.dashboard` already owns
`create_app`. One public name has one owning package, and two of them would give
a consumer writing a star import whichever one it imported last.

## Pagination

| Symbol              | Kind     | What it is                                                         |
| ------------------- | -------- | ------------------------------------------------------------------ |
| `Cursor`            | class    | One position in the canonical replay order of one log              |
| `CursorError`       | class    | A cursor this server did not mint, or can no longer read           |
| `encode_cursor`     | function | The opaque base64url encoding a client receives                    |
| `decode_cursor`     | function | Read one back, or refuse it                                        |
| `EventPage`         | class    | One page plus the position a client resumes from                   |
| `page_of`           | function | One page of a log, in the canonical order, strictly after a cursor |
| `DEFAULT_PAGE_SIZE` | constant | 100                                                                |
| `MAX_PAGE_SIZE`     | constant | 10000, the page-size ceiling                                       |

## Metrics

| Symbol                   | Kind     | What it is                                                 |
| ------------------------ | -------- | ---------------------------------------------------------- |
| `MetricDefinition`       | class    | One registered metric, whose expression is null until E26b |
| `MetricRegistry`         | class    | The registered metrics, addressed by id                    |
| `EXPRESSION_REQUIREMENT` | constant | `E26b`, named in the 501 so a client can find the plan     |

## Errors

| Symbol                     | Kind     | What it is                                                   |
| -------------------------- | -------- | ------------------------------------------------------------ |
| `Problem`                  | class    | One refusal: its `TF-Axxx` code, status, and title           |
| `ProblemError`             | class    | A refusal on its way to the client as a problem document     |
| `problem_document`         | function | The RFC 9457 body, with the code in both places 5.13 puts it |
| `PROBLEMS`                 | constant | Every code this surface can answer with, sorted              |
| `PROBLEM_MEDIA_TYPE`       | constant | `application/problem+json`                                   |
| `DEFAULT_PROBLEM_BASE_URL` | constant | Where the published explanation of each code lives           |

## Packaging

| Symbol        | Kind     | What it is                                                             |
| ------------- | -------- | ---------------------------------------------------------------------- |
| `__version__` | constant | The distribution version, read by the build so the two cannot disagree |

## Behavior worth knowing

`page_of` orders before it cuts and cuts by comparing keys rather than by
counting rows. Both are load-bearing. Sorting a page rather than the log gives a
body that looks ordered and a walk that is not, and an offset into a filtered
list is a different row every time the filter changes.

`next_cursor` is `None` exactly when the log is exhausted, and never merely
because the page came back short. A short page carrying a cursor loops a client
forever; a full page with no cursor truncates the walk with nothing failing.

`/api/v1/metrics/{id}` answers `404` and `501` for two different facts. A `404`
says the metric does not exist and to stop asking. A `501` says the metric is
registered, its id is stable, and E26b owns the expression language that would
evaluate it.

`POST /api/v1/config` delegates its tier decision to
`AutonomySession.authorize`. It does not compare tiers itself, and the tier it
records is read from the session rather than from the caller.

Every `ETag` is the hash of the exact bytes the response carries. The body is
serialized once, canonically, and both the hash and the response read that one
buffer, so an `ETag` can never describe a body nobody received.

## Re-exports

None declared. `AutonomyTier` is imported from `twinflow.agent` at the call site
in `app.py` and is deliberately absent from `__all__`: that name has one owning
package, and re-exporting it here would give a consumer two.

## Names this package does not export

`Historian`, `Envelope`, and `Clock` reach this package as parameter types and
are owned by `twinflow-storage`, `twinflow-schemas`, and `twinflow-kernel`.
