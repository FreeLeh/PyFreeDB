# pyfreedb

![Unit Test](https://github.com/FreeLeh/pyfreedb/actions/workflows/unit_test.yml/badge.svg)

<div>
    <h2 align="center">
        Excited to start your personal project, but too lazy to setup your server, database, KV store, etc.?
        <br>
        <br>
        <i>We feel you!</i>
    </h2>
</div>

`pyfreedb` is a Python library providing common and familiar interfaces on top of common free services we have access to.

## Why do you need this library?

Our main goal is to make developers who want to **just start their small personal projects so much easier without thinking too much about the setup required to get started**. We can leverage a bunch of well known free services available to us like Google Sheets and Telegram. We want to use these services as our **easy-to-setup and "managed" database or even a message queue**.

`pyfreedb` is just the beginning. It is very likely we will explore other languages (e.g. Java, Kotlin, Swift, etc.) to support in the future.

> Check out [GoFreeLeh](https://github.com/FreeLeh/GoFreeLeh/) for the Go version!

## What kind of interfaces/abstractions can this library provide?

Here are a few things we have developed so far:

1. A simple key-value store on top of Google Sheets.
2. A simple row based database on top of Google Sheets.

There are other ideas we have in our backlog:

1. A simple message queue on top of Google Sheets.
2. A simple message queue on top of Telegram Channels.

We are quite open to knowing any other free services we can leverage on.<br>
Please suggest your ideas in the [issues](https://github.com/FreeLeh/pyfreedb/issues) page!

## What can I do with these interfaces/abstractions?

The primary target for this library is **small personal projects with low QPS and no high performance requirement**. A project that is not too complex, only doing simple queries, and only used by the project owner is usually a good candidate.

Here are a few ideas we thought of:

1. **A simple personalised expenses tracker.**

   - A simple mobile app is sufficient. The app is specifically configured and set up just for the author.
   - Mobile app is not distributed via Google Play Store or Apple App Store.
   - The expenses can be **tracked using the simple row based database on top of Google Sheets**.
   - The data can be further manipulated through Google Sheets manually (e.g. summarise it using pivot table).

2. **A simple home automation controller.**
   - You may want to build a simple mobile app controlling your Raspberry Pi.
   - However, you cannot connect to your Raspberry Pi easily (there are tools for it, but it's usually not free).
   - You can make the mobile app publish an event to Google Sheets and let the Raspberry Pi listen to such events and act accordingly.

# Table of Contents

- [Installation](#installation)
- [Key Value Store](#key-value-store)
  - [Google Sheets Key Value Store](#google-sheets-key-value-store)
    - [Key Value Store Interface](#key-value-store-interface)
    - [Key Value Store Modes](#key-value-store-modes)
      - [Default Mode](#default-mode)
      - [Append Only Mode](#append-only-mode)
- [Row Store](#row-store)
  - [Google Sheets Row Store](#google-sheets-row-store)
    - [Row Store Interface](#row-store-interface)
- [Google Credentials](#google-credentials)
  - [OAuth2 Flow](#oauth2-flow)
  - [Service Account Flow](#service-account-flow)
  - [Custom HTTP Client](#custom-http-client)
- [Limitations](#limitations)
- [Disclaimer](#disclaimer)
- [License](#license)

# Installation

```
pip install pyfreedb
```

# Key Value Store

## Google Sheets Key Value Store

```py
from pyfreedb.providers.google import auth

scopes = ["https://www.googleapis.com/auth/spreadsheets"]

# If using Google Service Account.
auth_client = auth.ServiceAccountGoogleAuthClient.from_service_account_file("<path_to_service_account_json>", scopes=scopes)

# If using Google OAuth2 Flow.
auth_client = auth.OAuth2GoogleAuthClient.from_authorized_user_file(
    "<path_to_cached_credentials_json>",
    client_secret_filename="<path_to_client_secret_json>",
    scopes=scopes,
)

# Below are the same regardless of the auth client chosen above.
from pyfreedb.kv import GoogleSheetKVStore
kv = GoogleSheetKVStore(
    auth_client,
    spreadsheet_id="<spreadsheet_id>",
    sheet_name="<sheet_name>",
    mode=GoogleSheetKVStore.APPEND_ONLY_MODE,
)

kv.set("k1", b"some value")
print(kv.get("k1")) # b"some value"
kv.delete("k1")

# It's recommended to call kv.close() after you done to clean up things.
kv.close()
```

Getting started is very simple (error handling ignored for brevity).
You only need 3 information to get started:

1. A Google credentials (the `auth` variable). Read below for more details how to get this.
2. The Google Sheets `spreadsheet_id` to use as your database.
3. The Google Sheets `sheet_name` to use as your database.

If you want to compare the above concept with a Redis server, the `spreadsheet_id` is the Redis host and port,
while a `sheet_name` is the Redis database that you can select using the [Redis `SELECT` command](https://redis.io/commands/select/).

### Key Value Store Interface

#### `get(key: str) -> bytes`

- `get` tries to retrieve the value associated to the given key.
- If the key exists, this method will return the value.
- Otherwise, `pyfreedb.kv.KeyNotFoundError` will be returned.

#### `set(key: str, value: bytes) -> None`

- `set' performs an upsert operation on the key.
- If the key exists, this method will update the value for that key.
- Otherwise, it will create a new entry and sets the value accordingly.

#### `delete(key: str) -> None`

- `delete` removes the key from the database.
- If the key exists, this method will remove the key from the database.
- Otherwise, this method will do nothing.

> ### ⚠️ ⚠️ Warning
>
> Please note that only `bytes` values are supported at the moment.

### Key Value Store Modes

There are 2 different modes supported:

1. Default mode.
2. Append only mode.

```go
// Default mode
kv = GoogleSheetKVStore(auth_client, spreadsheet_id="<spreadsheet_id>", sheet_name="<sheet_name>", mode=GoogleSheetKVStore.DEFAULT_MODE)

// Append only mode
kv = GoogleSheetKVStore(auth_client, spreadsheet_id="<spreadsheet_id>", sheet_name="<sheet_name>", mode=GoogleSheetKVStore.APPEND_ONLY_MODE)
```

#### Default Mode

The default mode works just like a normal key value store. The behaviours are as follows.

##### `get(key: str) -> bytes`

- Returns `pyfreedb.kv.KeyNotFoundError` if the key is not in the store.
- Use a simple `VLOOKUP` formula on top of the data table.
- Does not support concurrent operations.

##### `set(key: str, value: bytes) -> None`

- If the key is not in the store, `set` will create a new row and store the key value pair there.
- If the key is in the store, `set` will update the previous row with the new value and timestamp.
- There are exactly 2 API calls behind the scene: getting the row for the key and creating/updating with the given key value data.
- Does not support concurrent operations.

##### `delete(key: str) -> None`

- If the key is not in the store, `delete` will not do anything.
- If the key is in the store, `delete` will remove that row.
- There are up to 2 API calls behind the scene: getting the row for the key and remove the row (if the key exists).
- Does not support concurrent operations.

![Default Mode Screenshot](docs/img/default_mode.png?raw=true)

You can see that each key (the first column) only appears at most once.

Some additional notes to understand the default mode better:

1. Default mode is easier to manage as the concept is very similar to common key value store out there. You can think of it like a normal `dict` in python.
2. Default mode is slower for most operations as its `set` and `delete` operation need up to 2 API calls.
3. Default mode uses less rows as it updates in place.
4. Default mode does not support concurrent operations.

#### Append Only Mode

The append only mode works by only appending changes to the end of the sheet. The behaviours are as follows.

##### `get(key: str) -> bytes`

- Returns `pyfreedb.kv.KeyNotFoundError` if the key is not in the store.
- Use a simple `VLOOKUP` with `SORT` (sort the 3rd column, the timestamp) formula on top of the data table.
- Support concurrent operations as long as the `GoogleSheetKVStore` instance is not shared between threads/coroutines.

##### `set(key: str, value: bytes) -> None`

- `set` always creates a new row at the bottom of the sheet with the latest value and timestamp.
- There is only 1 API call behind the scene.
- Support concurrent operations as long as the `GoogleSheetKVStore` instance is not shared between goroutines.

##### `delete(key: str) -> None`

- `delete` also creates a new row at the bottom of the sheet with a tombstone value and timestamp.
- `get` will recognise the tombstone value and decide that the key has been deleted.
- There is only 1 API call behind the scene.
- Support concurrent operations as long as the `GoogleSheetKVStore` instance is not shared between goroutines.

![Append Only Mode Screenshot](docs/img/append_only_mode.png?raw=true)

You can see that a specific key can have multiple rows. The row with the latest timestamp would be seen as the latest value for that specific key.

Some additional notes to understand the append only mode better:

1. Append only mode is faster for most operations as all methods are only calling the API once.
2. Append only mode may use more rows as it does not do any compaction of the old rows (unlike SSTable concept).
3. Append only mode support concurrent operations as long as the `GoogleSheetKVStore` instance is not shared between goroutines.

# Row Store

## Google Sheets Row Store

```py
from pyfreedb.providers.google import auth

scopes = ["https://www.googleapis.com/auth/spreadsheets"]

# If using Google Service Account.
auth_client = auth.ServiceAccountGoogleAuthClient.from_service_account_file("<path_to_service_account_json>", scopes=scopes)

# If using Google OAuth2 Flow.
auth_client = auth.OAuth2GoogleAuthClient.from_authorized_user_file(
    "<path_to_cached_credentials_json>",
    client_secret_filename="<path_to_client_secret_json>",
    scopes=scopes,
)


# Below are the same regardless of the auth client chosen above.
from pyfreedb.row import GoogleSheetRowStore
store = GoogleSheetRowStore(
    auth_client,
    spreadsheet_id="<spreadsheet_id>",
    sheet_name="<sheet_name>",
    columns=["name", "age"],
)

# Inserts a bunch of rows.
_ = store.insert([
    {"name": "name1", "age": 10},
    {"name": "name2", "age": 11},
    {"name": "name3", "age": 12}
]).execute()

# Updates the name column for rows with age = 10
store.update({"name": "name4"}).where("age = ?", 10).execute()

# Delete name=name2
store.delete().where("age = ?", 11).execute()

# Filter results
print(store.select("name").where("name = ? OR age = ?", "name4", 12).execute()) # [{"name": "name4"}, {"name": "name3"}]

# It's recommended to call kv.close() after you done to clean up things.
kv.close()
```

Getting started is very simple (error handling ignored for brevity).
You only need 3 information to get started:

1. A Google credentials (the `auth` variable). Read below for more details how to get this.
2. The Google Sheets `spreadsheet_id` to use as your database.
3. The Google Sheets `sheet_name` to use as your database.
4. A list of strings to define the columns in your database (note that the ordering matters!).

## Row Store Interface

For all the examples in this section, we assume we have a table of 2 columns: name (column A) and age (column B).

> ### ⚠️ ⚠️ Warning
>
> Please note that the row store implementation does not support any ACID guarantee.
> Concurrency is not a primary consideration and there is no such thing as a "transaction" concept anywhere.
> Each statement may trigger multiple APIs and those API executions are not atomic in nature.

### `select(*columns: str) -> pyfreedb.row.gsheet.SelectStmt`

- `select` returns a statement to perform the actual select operation. You can think of this operation like the normal SQL select statement (with limitations).
- If `columns` is an empty list, all columns will be returned.
- If a column is not found in the provided list of columns that you pass to the initializer, that column will be ignored.

#### `pyfreedb.row.gsheet.SelectStmt`

##### `where(condition: str, *args: Any) -> pyfreedb.row.gsheet.SelectStmt`

- The values in `condition` string must be replaced using a placeholder denoted by `?`.
- The actual values used for each placeholder (ordering matters) are provided via the `args` parameter.
- The purpose of doing this is because we need to replace each column name into the column name in Google Sheet (i.e. `A` for the first column, `B` for the second column, and so on).
- All conditions supported by Google Sheet `QUERY` function are supported by this library. You can read the full information in this [Google Sheets Query docs](https://developers.google.com/chart/interactive/docs/querylanguage#where).
- This function returns a reference to the statement for chaining.

Examples:

```py
# SELECT * WHERE A = "bob" AND B = 12
store.select().where("name = ? AND age = ?", "bob", 12)

# SELECT * WHERE A like "b%" OR B >= 10
store.select().where("name like ? OR age >= ?", "b%", 10)
```

##### `order_by(**ordering: pyfreedb.row.Ordering) -> pyfreedb.row.gsheet.SelectStmt`

- The `ordering` kwargs decides which column should have what kind of ordering.
- The library provides 2 ordering constants: `pyfreedb.row.Ordering.ASC` and `pyfreedb.row.Ordering.DESC`.
- And empty `ordering` kwargs will result in no operation.
- This function will translate into the `ORDER BY` clause as stated in this [Google Sheets Query docs](https://developers.google.com/chart/interactive/docs/querylanguage#order-by).
- This function returns a reference to the statement for chaining.
- Keyword ordering matters.

Examples:

```py
# SELECT * WHERE A = "bob" AND B = 12 ORDER BY A ASC, B DESC
store.select().where("name = ? AND age = ?", "bob", 12).order_by(name=Ordering.ASC, age=Ordering.DESC)

# SELECT * ORDER BY A ASC
store.select().order_by(name=Ordering.ASC)
```

##### `limit(limit: int) -> pyfreedb.row.gsheet.SelectStmt`

- This function limits the number of returned rows.
- This function will translate into the `LIMIT` clause as stated in this [Google Sheets Query docs](https://developers.google.com/chart/interactive/docs/querylanguage#limit).
- This function returns a reference to the statement for chaining.

Examples:

```py
# SELECT * WHERE A = "bob" AND B = 12 LIMIT 10
store.select().where("name = ? AND age = ?", "bob", 12).limit(10)
```

##### `offset(offset: int) -> pyfreedb.row.gsheet.SelectStmt`

- This function skips a given number of first rows.
- This function will translate into the `OFFSET` clause as stated in this [Google Sheets Query docs](https://developers.google.com/chart/interactive/docs/querylanguage#offset).
- This function returns a reference to the statement for chaining.

Examples:

```py
# SELECT * WHERE A = "bob" AND B = 12 OFFSET 10
store.select().where("name = ? AND age = ?", "bob", 12).offset(10)
```

##### `execute() -> List[Dict[str, str]]`

- This function will actually execute the `SELECT` statement and return the result.
- There is only one API call involved in this function.

Examples:

```py
print(store.select().where("name = ? AND age = ?", "bob", 12).excute)
```

### `insert(rows: List[Dict[str, str]]) -> pyfreedb.row.gsheet.InsertStmt`

- `insert` returns a statement to perform the actual insert operation.

#### `pyfreedb.row.gsheet.InsertStmt`

##### `execute() -> None`

- This function will actually execute the `INSERT` statement.
- This works by appending new rows into Google Sheets.
- There is only one API call involved in this function.

### `update(updated_value: Dict[str, str]) -> pyfreedb.row.gsheet.UpdateStmt`

- `Update` returns a statement to perform the actual update operation.
- The `updated_value` dict tells the library which column should be updated to what value.
- Note that the column in `updated_value` must exist in columns that you've passed during initialisation.

#### `pyfreedb.row.gsheet.UpdateStmt`

##### `where(condition: str, *args: Any) -> pyfreedb.row.gsheet.UpdateStmt`

This works exactly the same as the `pyfreedb.row.gsheet.SelectStmt.where` function. You can refer to the above section for more details.

##### `execute() -> int`

- This function will actually execute the `UPDATE` statement.
- There are two API calls involved: one for figuring out which rows are affected and another for actually updating the values.
- Returns number of affected rows by the update.

### `delete() -> pyfreedb.row.gsheet.DeleteStmt`

- `delete` returns a statement to perform the actual delete operation.

#### `pyfreedb.row.gsheet.DeleteStmt`

##### `where(condition: str, *args: Any) -> pyfreedb.row.gsheet.DeleteStmt`

This works exactly the same as the `pyfreedb.row.gsheet.SelectStmt.where` function. You can refer to the above section for more details.

##### `execute() -> int`

- This function will actually execute the `DELETE` statement.
- There are two API calls involved: one for figuring out which rows are affected and another for actually deleting the rows.
- Returns number of affected rows by the delete.

# Google Credentials

There are 2 modes of authentication that we support:

1. OAuth2 flow.
2. Service account flow.

## OAuth2 Flow

```py
auth_client = auth.OAuth2GoogleAuthClient.from_authorized_user_file(
    "<path_to_cached_credentials_json>",
    client_secret_filename="<path_to_client_secret_json>",
    scopes=scopes,
)
```

**Explanations:**

1. The `client_secret_json` can be obtained by creating a new OAuth2 credentials in [Google Developers Console](https://console.cloud.google.com/apis/credentials). You can put any link for the redirection URL field.
2. The `cached_credentials_json` will be created automatically once you have authenticated your Google Account via the normal OAuth2 flow. This file will contain the access token and refresh token.
3. The `scopes` tells Google what your application can do to your spreadsheets (`auth.GoogleSheetsReadOnly`, `auth.GoogleSheetsWriteOnly`, or `auth.GoogleSheetsReadWrite`).

During the OAuth2 flow, you will be asked to click a generated URL in the terminal.

1. Click the link and authenticate your Google Account.
2. You will eventually be redirected to another link which contains the authentication code (not the access token yet).
3. Copy and paste that final redirected URL into the terminal to finish the flow.

If you want to understand the details, you can start from this [Google OAuth2 page](https://developers.google.com/identity/protocols/oauth2/web-server).

## Service Account Flow

```py
auth_client = auth.ServiceAccountGoogleAuthClient.from_service_account_file("<path_to_service_account_json>", scopes=scopes)
```

**Explanations:**

1. The `service_account_json` can be obtained by following the steps in this [Google OAuth2 page](https://developers.google.com/identity/protocols/oauth2/service-account#creatinganaccount). The JSON file of interest is **the downloaded file after creating a new service account key**.
2. The `scopes` tells Google what your application can do to your spreadsheets (`auth.GoogleSheetsReadOnly`, `auth.GoogleSheetsWriteOnly`, or `auth.GoogleSheetsReadWrite`).

If you want to understand the details, you can start from this [Google Service Account page](https://developers.google.com/identity/protocols/oauth2/service-account).

> ### ⚠️ ⚠️ Warning
>
> Note that a service account is just like an account. The email in the `service_account_json` must be allowed to read/write into the Google Sheet itself just like a normal email address.
> If you don't do this, you will get an authorization error.

# Limitations

1. If you want to manually edit the Google Sheet, you can do it, but you need to understand the value encoding scheme.
2. It is not easy to support concurrent operations. Only few modes or abstractions allow concurrent operations.
3. Performance is not a high priority for this project.
4. `pyfreedb` does not support OAuth2 flow that spans across frontend and backend yet.

### (Google Sheets Key Value) Exclamation Mark `!` Prefix

1. We prepend an exclamation mark `!` in front of the value automatically.
2. This is to differentiate a client provided value of `#N/A` from the `#N/A` returned by the Google Sheet formula.
3. Hence, if you are manually updating the values via Google Sheets directly, you need to ensure there is an exclamation mark `!` prefix.

### (Google Sheets Row) Value Type in Cell

1. Note that we do not do any type conversion when inserting values into Google cells.
2. Values are marshalled using JSON internally by the Google Sheets library.
3. Values are interpreted automatically by the Google Sheet itself (unless you have changed the cell value type intentionally and manually). Let's take a look at some examples.
   - The literal string value of `"hello"` will automatically resolve into a `string` type for that cell.
   - The literal integer value of `1` will automatically resolve into a `number` type for that cell.
   - The literal string value of `"2000-1-1"`, however, will automatically resolve into a `date` type for that cell.
   - Note that this conversion is automatically done by Google Sheet.
   - Querying such column will have to consider the automatic type inference for proper querying. You can read here for [more details](https://developers.google.com/chart/interactive/docs/querylanguage#language-elements).
4. It may be possible to build a more type safe system in the future.
   - For example, we can store the column value type and store everything as strings instead.
   - During the data retrieval, we can read the column value type and perform explicit conversion.

# Disclaimer

- Please note that this library is in its early work.
- The interfaces provided are still unstable and we may change them at any point in time before it reaches v1.
- In addition, since the purpose of this library is for personal projects, we are going to keep it simple.
- Please use it at your own risk.

# License

This project is [MIT licensed](https://github.com/FreeLeh/GoFreeLeh/blob/main/LICENSE).
