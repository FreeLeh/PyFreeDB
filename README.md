# GoFreeDB

<br />

<div align="center">
	<img width="200" src="docs/img/logo_light.png#gh-light-mode-only">
    <img width="200" src="docs/img/logo_dark.png#gh-dark-mode-only">
	<h3><i>Ship Faster with Google Sheets as a Database!</i></h3>
</div>

<p align="center">
	<code>PyFreeDB</code> is a Python library that provides common and simple database abstractions on top of Google Sheets.
</p>

<br />

<div align="center">

![Unit Test](https://github.com/FreeLeh/PyFreeDB/actions/workflows/unit_test.yml/badge.svg)
![Integration Test](https://github.com/FreeLeh/PyFreeDB/actions/workflows/integration_test.yml/badge.svg)

</div>

## Features

1. Provide a straightforward **key-value** and **row based database** interfaces on top of Google Sheets.
2. Serve your data **without any server setup** (by leveraging Google Sheets infrastructure).
3. Support **flexible enough query language** to perform various data queries.
4. **Manually manipulate data** via the familiar Google Sheets UI (no admin page required).

> For more details, please read [our analysis](https://github.com/FreeLeh/docs/blob/main/freedb/alternatives.md#why-should-you-choose-freedb)
> on other alternatives and how it compares with `FreeDB`.

## Table of Contents

- [Protocols](#protocols)
- [Getting Started](#getting-started)
  - [Installation](#installation)
  - [Pre-requisites](#pre-requisites)
- [Row Store](#row-store)
  - [Querying Rows](#querying-rows)
  - [Counting Rows](#counting-rows)
  - [Inserting Rows](#inserting-rows)
  - [Updating Rows](#updating-rows)
  - [Deleting Rows](#deleting-rows)
  - [Model Field to Column Mapping](#model-field-to-column-mapping)
- [KV Store](#kv-store)
  - [Get Value](#get-value)
  - [Set Key](#set-key)
  - [Delete Key](#delete-key)
  - [Supported Modes](#supported-modes)

## Protocols

Clients are strongly encouraged to read through the **[protocols document](https://github.com/FreeLeh/docs/blob/main/freedb/protocols.md)** to see how things work
under the hood and **the limitations**.

## Getting Started

### Installation

```
pip install pyfreedb
```

### Pre-requisites

1. Obtain a Google [OAuth2](https://github.com/FreeLeh/docs/blob/main/google/authentication.md#oauth2-flow) or [Service Account](https://github.com/FreeLeh/docs/blob/main/google/authentication.md#service-account-flow) credentials.
2. Prepare a Google Sheets spreadsheet where the data will be stored.

## Row Store

Let's assume each row in the table is represented by the `Person` object.

```py
from pyfreedb.row import models

class Person(models.Model):
    name = models.StringField()
    age = models.IntegerField()
```

```py
from pyfreedb.providers.google.auth import ServiceAccountGoogleAuthClient, OAuth2GoogleAuthClient, Scopes

# If using Google Service Account.
auth_client = ServiceAccountGoogleAuthClient.from_service_account_file(
    "<path_to_service_account_json>",
    scopes=Scopes.ROW_STORE,
)

# If using Google OAuth2 Flow.
auth_client = OAuth2GoogleAuthClient.from_authorized_user_file(
    "<path_to_cached_credentials_json>",
    client_secret_filename="<path_to_client_secret_json>",
    scopes=Scopes.ROW_STORE,
)

from pyfreedb.row import GoogleSheetRowStore

store = GoogleSheetRowStore(
    config.auth_client,
    spreadsheet_id="<spreadsheet_id>",
    sheet_name="<sheet_name>",
    object_cls=Person,
)
```

### Querying Rows

```py
# Select all columns of all rows.
rows = store.select().execute()

# Select a few columns for all rows (non-selected struct fields will have default value).
rows = store.select("name").execute()

# Select rows with conditions.
rows = store.select().where("name = ? OR age >= ?", "freedb", 10).execute()

# Select rows with sorting/order by.
from pyfreedb.row import Ordering

rows = store.select().order_by(Ordering.ASC("name"), Ordering.DESC("age")).execute()

# Select rows with offset and limit
rows = store.select().offset(10).limit(20).execute()
```

### Counting Rows

```py
# Count all rows.
count = store.count().execute()

# Count rows with conditions.
count = store.count().where("name = ? OR age >= ?", "freedb", 10).execute()
```

### Inserting Rows

```py
rows = [Person(name="no_pointer", age=10), Person(name="with_pointer", age=20)]
store.insert(rows).execute()
```

### Updating Rows

```py
# Update all rows.
store.update({"name": "new_name", "age": 100}).execute()

# Update rows with conditions.
store.update({"name": "new_name", "age": 100}).where("name = ? OR age >= ?", "freedb", 10).execute()
```

### Deleting Rows

```py
# Delete all rows.
store.delete().execute()

# Delete rows with conditions.
store.delete().where("name = ? OR age >= ?", "freedb", 10).execute()
```

### Model Field to Column Mapping

You can pass keyword argument `header_name` to the `Field` constructor when defining the models to change the column
name in the sheet. Without this keyword argument, the library will use the field name as the column name (case
sensitive).

```py
# This will map to the exact column name of "name" and "age".
class Person(models.Model):
    name = models.StringField()
    age = models.IntegerField()

# This will map to the exact column name of "Name" and "Age".
class Person(models.Model):
    name = models.StringField(header_name="Name")
    age = models.IntegerField(header_name="Age")
```

## KV Store

```py
from pyfreedb.providers.google.auth import ServiceAccountGoogleAuthClient, OAuth2GoogleAuthClient, Scopes

# If using Google Service Account.
auth_client = ServiceAccountGoogleAuthClient.from_service_account_file(
    "<path_to_service_account_json>",
    scopes=Scopes.KV_STORE,
)

# If using Google OAuth2 Flow.
auth_client = OAuth2GoogleAuthClient.from_authorized_user_file(
    "<path_to_cached_credentials_json>",
    client_secret_filename="<path_to_client_secret_json>",
    scopes=Scopes.KV_STORE,
)

store = GoogleSheetKVStore(
    auth_client,
	spreadsheet_id="<spreadsheet_id>",
    sheet_name="<sheet_name>",
    mode=GoogleSheetKVStore.APPEND_ONLY_MODE,
)
```

### Get Value

If the key is not found, `pyfreedb.kv.base.KeyNotFoundError` will be returned.

```go
store.get("k1")
```

### Set Key

```go
store.set("k1", b"some_value")
```

### Delete Key

```go
store.delete("k1")
```

### Supported Modes

> For more details on how the two modes are different, please read the [protocol document](https://github.com/FreeLeh/docs/blob/main/freedb/protocols.md).

There are 2 different modes supported:

1. Default mode.
2. Append only mode.

```go
// Default mode
store = GoogleSheetKVStore(
    auth_client,
	spreadsheet_id="<spreadsheet_id>",
    sheet_name="<sheet_name>",
    mode=GoogleSheetKVStore.DEFAULT_MODE,
)

// Append only mode
store = GoogleSheetKVStore(
    auth_client,
	spreadsheet_id="<spreadsheet_id>",
    sheet_name="<sheet_name>",
    mode=GoogleSheetKVStore.APPEND_ONLY_MODE,
)
```

## License

This project is [MIT licensed](https://github.com/FreeLeh/GoFreeDB/blob/main/LICENSE).
