# Copyright (c) 2022 AllSeeingEyeTolledEweSew
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
# OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.

import collections
from typing import cast
from typing import Mapping
from typing import Optional
from typing import Set
from typing import Tuple

import pytest

import dbver


class NamedFormatMigrations(dbver.Migrations[Optional[str], dbver.Connection]):
    def get_format_unchecked(
        self, conn: dbver.Connection, schema: str = "main"
    ) -> Optional[str]:
        if dbver.get_application_id(conn, schema) == 0:
            return None
        cur = conn.cursor()
        cur.execute(f'select name from "{schema}".format')
        (name,) = cast(Tuple[str], cur.fetchone())
        return name

    def set_format(
        self, new_format: Optional[str], conn: dbver.Connection, schema: str = "main"
    ) -> None:
        assert new_format is not None
        super().set_format(new_format, conn, schema=schema)
        cur = conn.cursor()
        cur.execute(f'drop table if exists "{schema}".format')
        cur.execute(f'create table "{schema}".format (name text not null)')
        cur.execute(f'insert into "{schema}".format (name) values (?)', (new_format,))


MIGRATIONS = NamedFormatMigrations(application_id=1)


@MIGRATIONS.migrates(None, "A")
def migrate_null_a(conn: dbver.Connection, schema: str = "main") -> None:
    conn.cursor().execute(f'create table "{schema}".a (a int primary key)')


@MIGRATIONS.migrates(None, "B")
def migrate_null_b(conn: dbver.Connection, schema: str = "main") -> None:
    conn.cursor().execute(f'create table "{schema}".b (b int primary key)')


@MIGRATIONS.migrates("A", "B")
def migrate_a_b(conn: dbver.Connection, schema: str = "main") -> None:
    cur = conn.cursor()
    cur.execute(f'create table "{schema}".b (b int primary key)')
    cur.execute(f'insert into "{schema}".b select * from "{schema}".a')
    cur.execute(f'drop table "{schema}".a')


@MIGRATIONS.migrates("B", "A")
def migrate_b_a(conn: dbver.Connection, schema: str = "main") -> None:
    cur = conn.cursor()
    cur.execute(f'create table "{schema}".a (a int primary key)')
    cur.execute(f'insert into "{schema}".a select * from "{schema}".b')
    cur.execute(f'drop table "{schema}".b')


def assert_migration_map(
    mapping: Mapping[Optional[str], dbver.Migration], targets: Set[Optional[str]]
) -> None:
    assert set(mapping.keys()) == targets
    for migration in mapping.values():
        assert callable(migration) is True


def test_mapping() -> None:
    assert_migration_map(MIGRATIONS[None], {"A", "B"})
    assert_migration_map(MIGRATIONS["A"], {"B"})
    assert_migration_map(MIGRATIONS["B"], {"A"})

    assert MIGRATIONS.get("does not exist") is None

    assert len(MIGRATIONS) == 3
    assert collections.Counter(iter(MIGRATIONS)) == collections.Counter(
        (None, "A", "B")
    )


def test_unprovisioned(conn: dbver.Connection) -> None:
    assert MIGRATIONS.get_format(conn) is None
    assert MIGRATIONS.get_format(conn, "main") is None
    conn.cursor().execute("attach ':memory:' as ?", ("other schema",))
    assert MIGRATIONS.get_format(conn, "other schema") is None


def test_invalid_application_id(conn: dbver.Connection) -> None:
    conn.cursor().execute("pragma application_id = 2")
    with pytest.raises(dbver.VersionError):
        MIGRATIONS.get_format(conn)


def test_nonempty_db(conn: dbver.Connection) -> None:
    conn.cursor().execute("create table x (x int primary key)")
    with pytest.raises(dbver.VersionError):
        MIGRATIONS.get_format(conn)


def test_provision_a(conn: dbver.Connection) -> None:
    MIGRATIONS[None]["A"](conn, "main")
    assert MIGRATIONS.get_format(conn) == "A"
    conn.cursor().execute("insert into a (a) values (?)", (1,))

    conn.cursor().execute("attach ':memory:' as ?", ("other schema",))
    MIGRATIONS[None]["A"](conn, "other schema")
    assert MIGRATIONS.get_format(conn, "other schema") == "A"
    conn.cursor().execute('insert into "other schema".a (a) values (?)', (1,))


def test_provision_b(conn: dbver.Connection) -> None:
    MIGRATIONS[None]["B"](conn, "main")
    assert MIGRATIONS.get_format(conn) == "B"
    conn.cursor().execute("insert into b (b) values (?)", (1,))

    conn.cursor().execute("attach ':memory:' as ?", ("other schema",))
    MIGRATIONS[None]["B"](conn, "other schema")
    assert MIGRATIONS.get_format(conn, "other schema") == "B"
    conn.cursor().execute('insert into "other schema".b (b) values (?)', (1,))


def test_migrate_a_b(conn: dbver.Connection) -> None:
    MIGRATIONS[None]["A"](conn, "main")
    assert MIGRATIONS.get_format(conn) == "A"
    conn.cursor().execute("insert into a (a) values (?)", (1,))
    MIGRATIONS["A"]["B"](conn, "main")
    assert MIGRATIONS.get_format(conn) == "B"
    assert conn.cursor().execute("select * from b").fetchall() == [(1,)]

    conn.cursor().execute("attach ':memory:' as ?", ("other schema",))
    MIGRATIONS[None]["A"](conn, "other schema")
    assert MIGRATIONS.get_format(conn, "other schema") == "A"
    conn.cursor().execute('insert into "other schema".a (a) values (?)', (1,))
    MIGRATIONS["A"]["B"](conn, "other schema")
    assert MIGRATIONS.get_format(conn, "other schema") == "B"
    assert conn.cursor().execute('select * from "other schema".b').fetchall() == [(1,)]


def test_migrate_b_a(conn: dbver.Connection) -> None:
    MIGRATIONS[None]["B"](conn, "main")
    assert MIGRATIONS.get_format(conn) == "B"
    conn.cursor().execute("insert into b (b) values (?)", (1,))
    MIGRATIONS["B"]["A"](conn, "main")
    assert MIGRATIONS.get_format(conn) == "A"
    assert conn.cursor().execute("select * from a").fetchall() == [(1,)]

    conn.cursor().execute("attach ':memory:' as ?", ("other schema",))
    MIGRATIONS[None]["B"](conn, "other schema")
    assert MIGRATIONS.get_format(conn, "other schema") == "B"
    conn.cursor().execute('insert into "other schema".b (b) values (?)', (1,))
    MIGRATIONS["B"]["A"](conn, "other schema")
    assert MIGRATIONS.get_format(conn, "other schema") == "A"
    assert conn.cursor().execute('select * from "other schema".a').fetchall() == [(1,)]
