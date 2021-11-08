# dbver

dbver is a set of utilities for schema compatibility in sqlite3.

## Features

* **sqlite-native**: use sqlite natively, not through an abstraction. *SQL isn't scary!*
* **Pythonic**: use sqlite pythonically *(context managers!)*
* **Schema versioning**: flexible version management, tailored for sqlite.
* **Lightweight**: no dependencies on frameworks or ORMs.
* **DB-API 2.0 compatibility**: use your favorite sqlite3 driver, including [pysqlite3](https://github.com/coleifer/pysqlite3) or [apsw](https://github.com/rogerbinns/apsw).

## When and why would you use this?

dbver is meant for cases where:
  1. Your app will only ever use sqlite3
  2. Your app doesn't need an ORM
  3. Your schema may still change over time

**Why only use sqlite3?** There are many reasons, but *implicit provisioning* is the best one. Most relational databases require a manual provisioning step (install the database; create a user and password; run a m


## Example

Schema management code:

```python
# Version control using "PRAGMA application_id" and "PRAGMA user_version"
_MIGRATIONS = dbver.SemverMigrations(application_id=0xdeadbeef)

# *THIS* app is compatible with schema version 1.0.0
MY_SCHEMA_VERSION = 1_000_000

# *THIS* app can initialize a database to version 1.0.0
@_MIGRATIONS.migrates(0, MY_SCHEMA_VERSION)
def _init_schema(conn, schema):
    conn.cursor().execute(f"create table {schema}.t (x int primary key)")
```

Using the database:

```python
def use_the_database(conn):
    # Initialize the database to our latest compatible version,
    # AND raise an exception if the database version isn't compatible
    _MIGRATIONS.upgrade(conn)
    # Use the database as normal
    conn.cursor().execute("insert into t values (...)")
```

dbver is minimalist. It doesn't provide an ORM, or natively integrate with any.
You provide your own schema migration code, and dbver helps you manage it.

dbver only supports sqlite3. It doesn't provide any abstraction to work with
other databases.

dbver is meant to support implicit provisioning, where the database is created
or upgraded implicitly by merely using an app. Explicit provisioning is also
supported.

dbver requires you to think about your database schema as an API. Your schema
supports certain patterns of reads and writes. Changes to your schema may break
those patterns, or they may be backward-compatible.

Examples of backward-compatible changes:
  * Adding a table
  * Adding a non-unique index

Examples of some "grey area" backward-compatible changes:
  * Adding a column to the end of a table
  * Changing a table to a view

You will have to decide what compatibility means for your app. dbver doesn't
expect or enforce specifics.

dbver requires you to store an explicit schema version in the database, which
must be updated during any migration.

dbver allows for any DB-API 2.0 sqlite3 interface, including pysqlite3 and
apsw.

Some other considerations for sqlite3 schema compatibility:
  * Always keep in mind which schema versions are supported by a version of
    your app.
  * If your app drops support for a schema version, that should be considered a
    breaking change in the app (your app's version should change from 1.0.0 to
    2.0.0).
  * It's helpful to consider a new, un-provisioned database (no tables exist)
    as being at a "null" version.
  * It's helpful to consider readers (clients who only use SELECT) separately
    from writers.
  * A writer may implicitly migrate a schema (breaking or non-breaking); a
    reader may not.
  * If a writer does implicit migrations, they should normally be non-breaking.
    An implicit breaking migration by the writer should be considered a
    breaking change in the app, but an explicit (user-initiated) breaking
    migration need not be considered a breaking change in the app.
  * Readers should normally support a "null"-version database as being
    equivalent to a provisioned database with empty tables. To avoid
