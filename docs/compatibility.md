# Best Practices for Schema Compatibility

!!! reminder
    Your schema is an API.

Compatibility matters when two pieces of technology change independently of each other.

**Your app and its database change independently**. When a user upgrades or downgrades your app, the data stays put. Your new code will talk to your old database, or vice versa.

In SQLite, **compatibility matters more** than with traditional databases. Your SQLite app automatically sets up its own database, so **users expect it to automatically upgrade the database too**. It's also more common to treat a SQLite database as a public API, or as an [application file format](https://www.sqlite.org/appfileformat.html). These factors put pressure on your compatibility strategy.

Backward-compatible schema changes are desirable, but they require planning ahead!

## Semantic versioning

!!! reminder
    Your schema is an API.

    Unless your database is packaged inside your app, you should version your schema, like any other API.

The benefits of assigning version numbers are widely known. They should be used for databases!

SQLite offers [`PRAGMA user_version`](https://www.sqlite.org/pragma.html), but you must remember to set it.

You should **always store** a schema version number to your database, **even in the first release**.

You should **always check** the schema version number when reading and writing, **even in the first release**.

You should **always use a [semantic versioning scheme](https://semver.org)**. I recommend using SQLite's style, which encodes version `X.Y.Z` in decimal digits as the number `XXXYYYZZZ`.

```sql
CREATE TABLE my_table (...);
CREATE INDEX my_index ON my_table (...);
PRAGMA user_version = 1000000; -- set the version as 1.0.0!
```

```python
def read_my_data():
    conn = sqlite3.Connection("my_database.db")
    # always check the version!
    version, = conn.cursor().execute("PRAGMA user_version").fetchone()
    # new, empty database with nothing in it
    if version == 0:
        return []
    # support schema version 1.x
    elif version < 2_000_000:
        return conn.cursor().execute("SELECT col1 from my_table").fetchall()
    assert False, "unsupported database version"
```

**Why always store a version number?** This is the simplest way to identify your database schema. It lets you distinguish between your v1.0 schema and your v2.0 schema, and between an empty uninitialized database and an initialized one. But if you don't set it when creating your first schema, you can't take advantage of it later!

**Why always check the version number?** Your v1.0 app might see a v2.0 database. This happens if a user downgrades your app, or if there are multiple separately-deployed apps using the same database. If you make backward-incompatible schema changes, but your v1.0 app doesn't check the version number, then it might fail in a nasty way. Worse, it might *not* fail, and act on bad data!

**Why use semantic versioning?** This lets you make backward-compatible *or* -incompatible schema changes in the future, as needed. Semantic versioning doesn't mean you *must* [plan for backward compatibility](#schema-compatibility), as this is complex. Your initial releases can just make backward-incompatible changes, and bump the major version of the schema. If you use semantic versioning from the start, you get a single coherent versioning scheme for the life of your app.

## App Version vs. Schema Version

The **schema version** is different from your **app version**.

A given **app version** *supports* one or more **schema versions**. It's essential to track which app versions support which schema versions.

For example, you might have:

* App version 1.0.0 supports schema version 1.0.0.
* App version 1.1.0 supports schema version 1.0.0, *and* a backward-incompatible version 2.0.0.
* App version 2.0.0 drops support for schema 1.x, and only supports schema 2.0.0.

Note that **dropping support for a schema version is a breaking change**. The new app version must be 2.0.0; it cannot be 1.2.0, within the rules of semantic versioning.

## Documentation

!!! reminder
    Your schema is an API.

    It supports certain patterns of reads and writes, with certain semantics.

Like any API, you must document the supported usage of your schema, so clients know which schema versions they are compatible with.

**Compatibility in SQL relies heavily on documentation**. SQLite is an expressive language, and does not have fine-grained support for *programmatically* dividing usage into "supported" and "unsupported" queries.

The most important thing is to document **potential changes** you might make to your schema, and still consider the change "backward-compatible". Clients of the database must only use it in ways that wouldn't be affected by documented potential changes. If some usage *would* be affected by potential changes, that usage is *unsupported*, even if it "works".

**Example**: you declare that they you may add columns to any table in a "non-breaking" schema change, using `ALTER TABLE ADD COLUMN`. Adding columns changes the output of `SELECT *`, so if a client were to rely on the output of `SELECT *`, then that client may be broken by a "non-breaking" change of your schema. Relying on the output of `SELECT *` is unsupported for your schema.

**Example**: you declare that clients may create their own persistent indexes on your tables with `CREATE INDEX`. You may not *also* declare that you may change tables to views in a "non-breaking" change. Indexes cannot be created on views, so if a client creates an index on a table that changes to a view, that client would be broken despite following supported usage.

You should **minimize the number of potential changes you may make to your schema**, and **minimize restrictions on usage of your schema**. The goal is to minimize the usage that is *functional, but unsupported*, like TODO.

## Client-created data

If your database might be used by multiple clients, they may all have different indexing needs.

Rather than maintain every conceivable index, it can be convenient to just document that clients are allowed to create their own persistent indexes, even though they don't "own" the database.

You might define that apps should namespace their indexes so they don't conflict:

```sql
CREATE INDEX _myapp_index1 ON t1 (col1);
CREATE INDEX _myapp_index2 ON t2 (col1, col2);
```

You could also define canonical index names, to avoid duplicate indexes:

```sql
CREATE INDEX IF NOT EXISTS t1__col1__col2 ON t1 (col1, col2);
```

## Potential schema changes

Here is a selection of possible schema changes you may want to be able to make in a non-breaking release.

### Adding a table

A new table is comatible with nearly all existing statements. It will only conflict with other `CREATE` statements using the same name.

### Adding an index

A new *non-unique* index is comatible with nearly all existing statements. It will only conflict with other `CREATE` statements using the same name.

A new *unique* index introduces a new constraint, so it may not be compatible with existing `INSERT`/`UPDATE`/`DELETE` statements.

### Adding new a column

Adding a new column is compatible with most existing `SELECT` statements. The output of `SELECT *` will contain the new column.

For best compatibility with existing `INSERT` statements, the column should be added to the end of the column list and have a default value.

It's good practice for clients to not rely on column order, or the output of `SELECT *`. When writing a schema contract, it's good to remind clients of this.

### Changing a table to a view

You might reserve the right to change a table to an equivalent view.

The view would normally be compatible with existing `SELECT`s. You can add `INSTEAD OF` triggers, to make the view compatible with existing `INSERT`, `UPDATE` and `DELETE`.

Note that indexes don't work with views, so if you might change a table to a view, you shouldn't advertise that the app may create its own indexes.

### Semantic changes

You may have schema changes that don't change the SQL structure at all, but change the meaning of the data.

```sql
-- migrate_v1.0.0_to_v2.0.0.sql
-- change fahrenheit to celsius
UPDATE TABLE t SET temperature = (temperature - 32) * 5 / 9;
```

Any existing queries will continue to work after this change, but may yield bad data.

Semantic changes will almost always be breaking changes. It's hard to make them backward-compatible.

## Transaction Model

SQLite works best when you separate your code into one of these two:

 * **Readers**, which use `BEGIN DEFERRED` transactions
 * **Writers**, which use `BEGIN IMMEDIATE` transactions

`BEGIN DEFERRED` isn't a good choice for writing data due to an API subtlety. If you execute these statements:

```sql
BEGIN DEFERRED;
PRAGMA user_version; -- check the schema version before writing
INSERT INTO ...;
```

SQLite will create a read transaction when executing `PRAGMA`, then "upgrade" to a write transaction when executing `INSERT`. When a transaction is upgraded in this case, and another connection has an active write transaction, or committed data since the start of the read transaction, then the `INSERT` will fail immediately with `SQLITE_BUSY` and **the busy handler will not run**. You will need to implement busy handler logic outside of the normal busy handler callback. Starting the write transaction immediately with `BEGIN IMMEDIATE` has a vanishingly small impact on concurrency, for a significant gain to code structure.

## Don't use nested transactions

[Don't use nested transactions (`SAVEPOINT`, etc)](https://docs.sqlalchemy.org/en/13/core/connections.html#arbitrary-transaction-nesting-as-an-antipattern). Your transaction control should be at the top level of your code.

## Don't use BEGIN EXCLUSIVE

Don't use `BEGIN EXCLUSIVE`. From a data concurrency perspective, it's exactly the same as `BEGIN IMMEDIATE` with a performance disadvantage, because readers can't run *parallel* with writers in WAL mode.

`BEGIN EXCLUSIVE` doesn't save you from thinking about concurrency in your app. Your readers must still use read transactions. If you want to *eliminate* concurrency, you probably want `PRAGMA locking_mode = EXCLUSIVE`.

The only good use of `BEGIN EXCLUSIVE` is as a multi-process mutex (guarding something other than the database's data, because other locking modes guard it better) in high level languages like python.

## Readers and Writers

It's useful think about code that accesses the database as either a **reader** (uses only `SELECT`) or a **writer** (uses `INSERT`, `CREATE`, etc).

Readers and writers might be

* different apps,
* different threads, or
* different modes of the same app.

Readers and writers should both use transactions, and check the version in the transaction.

```python
with begin(conn, ...):
    version, = conn.cursor().execute("PRAGMA user_version").fetchone()
    check_version(version)
    # read or write data
```

**Code that changes the schema is a writer**, by definition.

A writer may make **automatic, unprompted, unconditional schema changes**. If you don't want to break other apps, **unprompted schema changes must be backward-compatible**.

```python
with begin(conn, IMMEDIATE):
    version, = conn.cursor().execute("PRAGMA user_version").fetchone()
    if version == 1:
        conn.cursor().execute("ALTER TABLE t ADD COLUMN ...")
        conn.cursor().execute("PRAGMA user_version = 2")
    conn.cursor().execute("INSERT INTO t ...")
```

In some scenarios, **a reader may run before any writer**. It will encounter an **empty database with no tables**.

The `SELECT` statement cannot deal with this gracefully, and will raise an error.

Instead of the error, it can be useful to treat this as a **provisioned database with tables having no rows**. You can think of this as "schema version 0", since `PRAGMA user_version` defaults to 0.

```python
def read(conn):
    with begin(conn, DEFERRED):
        version, = conn.cursor().execute("PRAGMA user_version").fetchone()
        if version == 0:
            return []
        elif version == 1:
            return conn.cursor().execute("SELECT * from t").fetchall()
```

This is consistent with SQLite's design. If SQLite connects to a database that doesn't exist, it just creates the database and treats it as valid. It does not need a special "initialization" step.

## Migration Code

A **migration** is any code that changes the schema of a database, and meaningfully preserves the data.

Migrations may be any combination of SQL or normal code.

In the previous section, we treated a newly-created empty database as schema version 0. Consistent with this, we can say **the initial table creation is a migration from version 0 to version 1.0.0.**

```sql
-- init_v1.0.0.sql
CREATE TABLE t (x INT PRIMARY KEY);
```

Further migrations should preserve any existing data.

```sql
-- migrate_v1.0.0_to_v1.1.0.sql
ALTER TABLE t ADD COLUMN (y INT); -- column defaults to null
```

### Don't Delete Migrations

**Usually, you should never delete migration code**.

Just add new code to migrate to a new version, from the most-recently-released version.

Initializing a new database should run **every migration in order**, as opposed to running "combined" `CREATE TABLE` statements that create the final product directly.

This is the best way to ensure that **upgrading** your app has the same behavior as a **new install**.

#### Exception: Migration Bugs

You *should* delete a migration if it has a **data-loss bug**.

Let's say you release a migration to a new format, and forget to migrate the data.

```sql
-- migrate_v1.0.0_to_v2.0.0.sql
CREATE TABLE t2 (...);
DROP TABLE t1; -- oops, we dropped the table and forgot to migrate anything
```

This migration should never be run. We should delete it.

Create a new, fixed migration. **The new migration should migrate from the last-known-good version number to a *new* version, skipping the version number of the broken migration**. This way, the broken migration's version number will be an explicit signal that the data is bad. Apps can check for this version number and act accordingly.

```sql
-- migrate_v1.0.0_to_v2.1.0.sql
CREATE TABLE t2 (...);
INSERT INTO t2 SELECT FROM t1; -- remember to migrate this time
DROP TABLE t1;
```

#### Optimizations

You may end up with a long chain of migrations.

```sql
-- init_v1.0.0.sql
CREATE TABLE t (x INT PRIMARY KEY);
```

```sql
-- migrate_v1.0.0_to_v2.0.0.sql
CREATE TABLE t2 (...);
INSERT INTO t2 SELECT FROM t1;
DROP TABLE t1;
```

```sql
-- migrate_v2.0.0_to_v3.0.0.sql
CREATE TABLE t3 (...);
INSERT INTO t3 SELECT FROM t2;
DROP TABLE t2;
```

If the database is large, or the migrations complex, you may want to skip the intermediary migration.

**Keep the existing migrations**, but add an optimized path from 1.0.0 to 3.0.0.

```sql
-- migrate_v1.0.0_to_v3.0.0.sql
CREATE TABLE t3 (...);
INSERT INTO t3 SELECT FROM t1;
DROP TABLE t1;
```
