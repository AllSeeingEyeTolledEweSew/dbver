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

import pytest

import dbver

MIGRATIONS = dbver.SemverMigrations[dbver.Connection](application_id=1)


@MIGRATIONS.migrates(0, 1000000)
def migrate_1(conn: dbver.Connection, schema: str) -> None:
    conn.cursor().execute(f'create table "{schema}".a (a int primary key)')


@MIGRATIONS.migrates(1000000, 1001000)
def migrate_1dot1(conn: dbver.Connection, schema: str) -> None:
    cur = conn.cursor()
    cur.execute(f'alter table "{schema}".a add column t text')


@MIGRATIONS.migrates(1001000, 2000000)
def migrate_2(conn: dbver.Connection, schema: str) -> None:
    cur = conn.cursor()
    cur.execute(f'create table "{schema}".a2 (a int primary key, t text)')
    cur.execute(f'insert into "{schema}".a2 select * from "{schema}".a')
    cur.execute(f'drop table "{schema}".a')


def test_unprovisioned(conn: dbver.Connection) -> None:
    assert MIGRATIONS.get_format(conn) == 0
    assert MIGRATIONS.get_format(conn, "main") == 0
    conn.cursor().execute("attach ':memory:' as ?", ("other schema",))
    assert MIGRATIONS.get_format(conn, "other schema") == 0


def test_invalid_application_id(conn: dbver.Connection) -> None:
    conn.cursor().execute("pragma application_id = 2")
    with pytest.raises(dbver.VersionError):
        MIGRATIONS.get_format(conn)


def test_invalid_version_progression(conn: dbver.Connection) -> None:
    with pytest.raises(AssertionError):

        @MIGRATIONS.migrates(2, 1)
        def migrate_backward(conn: dbver.Connection, schema: str) -> None:
            pass  # pragma: no cover


def test_nonempty_db(conn: dbver.Connection) -> None:
    conn.cursor().execute("create table x (x int primary key)")
    with pytest.raises(dbver.VersionError):
        MIGRATIONS.get_format(conn)


def test_provision(conn: dbver.Connection) -> None:
    version = MIGRATIONS.upgrade(conn)
    assert version == 2000000
    assert MIGRATIONS.get_format(conn) == 2000000

    conn.cursor().execute("attach ':memory:' as ?", ("other schema",))
    version = MIGRATIONS.upgrade(conn, "other schema")
    assert version == 2000000
    assert MIGRATIONS.get_format(conn, "other schema") == 2000000


def test_upgrade_nonbreaking(conn: dbver.Connection) -> None:
    MIGRATIONS[0][1000000](conn, "main")
    assert MIGRATIONS.get_format(conn) == 1000000

    version = MIGRATIONS.upgrade(conn)
    assert version == 1001000


def test_upgrade_breaking(conn: dbver.Connection) -> None:
    MIGRATIONS[0][1000000](conn, "main")
    assert MIGRATIONS.get_format(conn) == 1000000

    version = MIGRATIONS.upgrade(conn, breaking=True)
    assert version == 2000000


def test_upgrade_condition(conn: dbver.Connection) -> None:
    def condition(orig: int, new: int) -> bool:
        return new <= 1001000

    version = MIGRATIONS.upgrade(conn, condition=condition)
    assert version == 1001000
