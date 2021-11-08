# Why dbver?

dbver is restricted to SQLite. It *doesn't* provide an abstraction layer to switch your app to other databases.

dbver *doesn't* provide an ORM layer.

dbver *re-implements* stuff that pysqlite and apsw already do, like managing transactions.

Those all sound like anti-features! What's the point of dbver?

## TL;DR: When to use dbver

You should use dbver if

1. your app will only ever use SQLite,
2. your schema may still change over time.

## Why is dbver restricted to SQLite?

There is a common thought that app should *never* be tightly coupled to one database type; that it's *always* better for an app to have a data access layer that is generic over many databases.

This is not always the case. Firefox uses SQLite for local storage, but it would never make sense for it to have MySQL as an option.

MySQL and other database servers can be multi-homed. But to take advantage of this for greater availability, your app must be multi-homed *itself*. Not all apps can be designed this way.

[Many of SQLite's features are unique to SQLite](https://sqlite.org/different.html), which can lead to unique app design. For example, a SQLite app will typically do manage schemas (`CREATE TABLE`s, etc) implicitly on startup, or even in every transaction. A MySQL app typically relies on an administrator to run a `CREATE TABLE` script. These two designs cannot be merged by some generic data access layer.

If your app will only ever use SQLite, the best way to take advantage of its features is to use it natively, not through a generic-SQL abstraction layer.

## Why doesn't dbver have an ORM?

**TL;DR**: ORMs don't come for free.

There is a common desire to work with ORMs, and ignore the underlying raw SQL.

This makes it hard to think about performance. Performance analysis in SQL is always done *at the SQL level*; SQLite's query planner can produce very different results from similar-looking SQL. So the best practice is to think about what SQL you want, and translate this into appropriate ORM operations. But working this way, the ORM *creates* complexity.

ORMs add memory management pressure, and it is perilous to ignore this. Python performs best when doing *as little work as possible in python*. Python performs especially poorly for mixed CPU- and IO-intensive tasks. Memory management counts as python work, so as data scales, the performance hit of ORMs can be much higher than expected. Memory management-based performance problems are difficult to discover through profiling.

In many cases, inappropriate use of ORMs is simply the result of lack of experience with SQL. If you mainly want to use an ORM because you find SQL to be "ugly", consider that this may be a bad reason.

dbver is designed around DBAPI. If an ORM is desired, hopefully any ORM that can be used with DBAPI can be used with dbver.

## Why does dbver re-implement transaction control?

**TL;DR**: pysqlite and apsw don't do it well.

**pysqlite**, by default, will implicitly `BEGIN` a transaction before a DML statement (`INSERT`, `UPDATE`, `DELETE`, `REPLACE`). This is inconsistent since you must still *explicitly* call `commit()` or `rollback()`. It's also inconsistent because it's good practice to `BEGIN` transactions for multiple `SELECT` statements as well, as this gives a consistent data view in WAL mode.

**apsw** provides transaction control by using the connection as a context manager (`with conn:`). Internally, this emits `SAVEPOINT`, so the transactions can be nested. But the outermost `SAVEPOINT` is equivalent to `BEGIN DEFERRED`, which is not useful when you really need `BEGIN IMMEDIATE`. In practice this is a significant downside, and the upside of nested transactions [is not useful](https://docs.sqlalchemy.org/en/13/core/connections.html#arbitrary-transaction-nesting-as-an-antipattern).

The best approach to sqlite transaction control is an explicit context manager which gives control over the transaction mode. dbver does this with the `begin()` function and friends.
