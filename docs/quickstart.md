# Quickstart

## Installation

Install dbver from pypi.

```shell
$ pip install dbver
```

## Pythonic sqlite

A **connection factory** is a zero-args function that creates a new database connection.

```python
def connection_factory():
    # isolation_level=None is STRONGLY recommended with pysqlite3
    conn = sqlite3.Connection("/path/to/my.db", isolation_level=None)
    # set any other connection parameters
    cur = conn.cursor()
    cur.execute("PRAGMA busy_timeout = 5000")
    return conn
```

A **connection pool** is a zero-args function returning a context manager of connections.

Connections are "checked out" of the pool when entering the context manager, and "checked in" on exit.

!!! note
    As of v0.4, dbver only offers `null_pool`, which creates a new connection every time.

    A "real" connection pool that reuses connections is coming soon!

```python
from dbver import null_pool

connection_pool = null_pool(connection_factory)

with connection_pool() as conn:
    conn.cursor().execute("INSERT INTO t (c) VALUES (...)")
```

The `begin()` function is a useful context manager for transactions.

```python
from dbver import begin, LockMode

with connection_pool() as conn:
    with begin(conn, LockMode.IMMEDIATE):
        cur = conn.cursor()
        rows = cur.execute("SELECT * FROM t1").fetchall()
        cur.execute("INSERT INTO t2 (c) VALUES (?)", (some_func(rows),))
```

`begin_pool()` checks out a connection and begins a transaction in a single step.

```python
from dbver import begin_pool

with begin_pool(connection_pool, LockMode.IMMEDIATE) as conn:
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM t1").fetchall()
    cur.execute("INSERT INTO t2 (c) VALUES (?)", (some_func(rows)))
```

## Schema management

dbver is meant to help you **manage** compatibility of your database schema.

The first step is **decide what you want**. There are many considerations with database schema compatibility, some unique to SQLite. Check the [compatibility guide](compatibility.md) for more information.

## Semver migrations: first version

The most robust schema management system is `SemverMigrations`.

In this scheme,

* We will set and check `PRAGMA application_id`
* We will set and check `PRAGMA user_version`, treated as the schema version
* `PRAGMA user_version` will use [semantic versioning](https://semver.org/) to define schema compatibility
* `PRAGMA user_version` uses a coding like sqlite's internal version numbers: decimal `XXXYYYZZZ` translates to semantic version `X.Y.Z`, so `1000000` indicates version `1.0.0`.

```python
from dbver import SemverMigrations

# our database uses "PRAGMA application_id = 0xdeadbeef"
_MIGRATIONS = SemverMigrations(application_id=0xdeadbeef)

# "migrates" a new, empty database (version 0) to version 1.0.0 (1000000)
@_MIGRATIONS.migrates(0, 1_000_000)
def _init_db(conn, schema):
    conn.cursor().execute("CREATE TABLE t (x INT PRIMARY KEY)")
```

Now you can work with the protections of a **versioned schema**.

Reading data:

```python
from dbver import semver_check_breaking

def read_data_set(conn):
    # will raise an exception if application_id doesn't match
    version = _MIGRATIONS.get_format(conn)

    # version 0 means a new, empty database with no tables;
    # instead of raising an error, we can just return empty set
    if version == 0:
        return {}

    # check the database is 1.x compatible
    semver_check_breaking(1_000_000, version)

    # the database is (compatible with) version 1.0! it's safe to read!
    cur = conn.cursor().execute("SELECT x FROM t")
    return {x for x, in cur}
```

And writing data:

```python
def write_data_set(conn, data_set):
    # upgrade the database to the newest format, WITHOUT breaking existing clients
    # will raise an error if:
    # - the application_id doesn't match
    # - the database can't be upgraded without breaking its version
    # - the database is already upgraded to a newer version which breaks
    #   compatibility with the newest-known version
    _MIGRATIONS.upgrade(conn)

    # the database is (compatible with) version 1.0! it's safe to write!
    conn.cursor().executemany("INSERT INTO t (x) VALUES (?)", [(x,) for x in data_set])
```

## Semver migrations: backward-compatible changes

Later, you want to add a new nullable column.

Since it defaults to `NULL`, this change won't break any existing usage. It's backward-compatible.

**Keep your existing migration code**. Add the code to **migrate** to the new version.

```python
@_MIGRATIONS.migrates(1_000_000, 1_001_000)
def _migrate_db(conn, schema):
    conn.cursor().execute("ALTER TABLE t ADD COLUMN (y INT)")
```

You can make a reader compatible with both 1.0 **and** 1.1.

It should understand that if the version is 1.0, then column `y` doesn't exist and can't be selected. It should fill in `NULL` values, at the python level.

```python hl_lines="1 13 14 15 19 20"
def read_data_map_1dot1(conn):
    # will raise an exception if application_id doesn't match
    version = _MIGRATIONS.get_format(conn)

    # version 0 means a new, empty database with no tables;
    # instead of raising an error, we can just return empty set
    if version == 0:
        return {}

    # check the database is 1.x compatible
    semver_check_breaking(1_000_000, version)

    if version >= 1_001_000:
        cur = conn.cursor().execute("SELECT x, y FROM t")
        return dict(cur)

    # otherwise, we're at version 1_000_000
    cur = conn.cursor().execute("SELECT x FROM t")
    # behave as if column y exists and is always NULL
    return {x: None for x, in cur}
```

The `upgrade()` function will now migrate to 1.1. **This won't break existing apps**.

Your writer only needs to understand 1.1.

```python hl_lines="1 10 11"
def write_data_map_1dot1(conn, data_map):
    # upgrade the database to the newest format, WITHOUT breaking existing clients
    # will raise an error if:
    # - the application_id doesn't match
    # - the database can't be upgraded without breaking its version
    # - the database is already upgraded to a newer version which breaks
    #   compatibility with the newest-known version
    _MIGRATIONS.upgrade(conn)

    # the database is (compatible with) version 1.1! it's safe to write!
    conn.cursor().executemany("INSERT INTO t (x, y) VALUES (?, ?)", data_map.items())
```

## Semver migrations: breaking changes

Now, you want to change your data **fundamentally**.

Let's suppose you want to store strings instead of separate numeric columns. This will **break** compatibility with existing readers and writers. The new version will be 2.0.

Again, **keep the existing code to migrate from 1.0 to 1.1**. Write a migration from version 1.1 to 2.0.

```python
@_MIGRATIONS.migrates(1_001_000, 2_000_000)
def _migrate_to_2dot0(conn, schema):
    conn.cursor().execute("CREATE TABLE t2 (x TEXT PRIMARY KEY)")
    conn.cursor().execute("INSERT INTO t2 SELECT x || ':' || COALESCE(y, '') FROM t")
    conn.cursor().execute("DROP TABLE t")
```

Now, you must choose when and how to do **breaking upgrades**.

Breaking upgrades are simpler:

```python hl_lines="9 10"
def write_str_set(conn, set_of_str):
    # upgrade the database to the newest format, WILL BREAK existing clients
    # will raise an error if:
    # - the application_id doesn't match
    # - the database is already upgraded to a newer version which breaks
    #   compatibility with the newest-known version
    _MIGRATIONS.upgrade(conn, breaking=True)

    # the database is (compatible with) version 2.0! it's safe to write!
    conn.cursor().executemany("INSERT INTO t2 (x) VALUES (?)", ((x,) for x in set_of_str))
```

Non-breaking upgrades are more complex:

```python hl_lines="9 10 11 12 13 14"
def write_str_set(conn, set_of_str):
    # upgrade the database to the newest format, WITHOUT breaking existing clients
    # will raise an error if:
    # - the application_id doesn't match
    # - the database is already upgraded to a newer version which breaks
    #   compatibility with the newest-known version
    version = _MIGRATIONS.upgrade(conn)

    if version < 2_000_000:
        # note that we'll have upgraded to at least version 1.1
        conn.cursor().executemany("INSERT INTO t (x, y) VALUES (?, ?)", [x.split(":") for x in set_of_str])
    else:
        # database is version 2.0
        conn.cursor().executemany("INSERT INTO t2 (x) VALUES (?)", [(x,) for x in set_of_str])
```

The choice of **when** to do breaking upgrades is up to you.

You might **never do breaking upgrades**. Your app could stay compatible with all database versions that have ever existed, or it could **drop support** for some old versions. Note that **dropping support for a database version is a breaking change of your app**.

You might do **implicit breaking upgrades** when writing data. Note that this means merely installing and running your app breaks other users of your database, so **this is a breaking change of your app**.

You can also do **explicit breaking upgrades** at the user's request. This is generally **not** considered a breaking change.
