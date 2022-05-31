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


def test_invalid_schema(conn: dbver.Connection) -> None:
    with pytest.raises(TypeError):
        dbver.check_application_id(1, conn, 1)  # type: ignore
    with pytest.raises(ValueError):
        dbver.check_application_id(1, conn, 'invalid"schema')


def test_expected_empty(conn: dbver.Connection) -> None:
    conn.cursor().execute("pragma application_id = 1")
    dbver.check_application_id(1, conn)
    dbver.check_application_id(1, conn, "main")


def test_expected_empty_other(conn: dbver.Connection) -> None:
    conn.cursor().execute("attach ':memory:' as ?", ("other schema",))
    conn.cursor().execute('pragma "other schema".application_id = 1')
    dbver.check_application_id(1, conn, "other schema")


def test_expected_nonempty(conn: dbver.Connection) -> None:
    conn.cursor().execute("pragma application_id = 1")
    conn.cursor().execute("create table x (x int primary key)")
    dbver.check_application_id(1, conn)
    dbver.check_application_id(1, conn, "main")


def test_expected_nonempty_other(conn: dbver.Connection) -> None:
    conn.cursor().execute("attach ':memory:' as ?", ("other schema",))
    conn.cursor().execute('pragma "other schema".application_id = 1')
    conn.cursor().execute('create table "other schema".x ' "(x int primary key)")
    dbver.check_application_id(1, conn, "other schema")


def test_unexpected(conn: dbver.Connection) -> None:
    conn.cursor().execute("pragma application_id = 2")
    with pytest.raises(dbver.VersionError):
        dbver.check_application_id(1, conn)
    with pytest.raises(dbver.VersionError):
        dbver.check_application_id(1, conn, "main")


def test_unexpected_other(conn: dbver.Connection) -> None:
    conn.cursor().execute("attach ':memory:' as ?", ("other schema",))
    conn.cursor().execute('pragma "other schema".application_id = 2')
    with pytest.raises(dbver.VersionError):
        dbver.check_application_id(1, conn, "other schema")


def test_unprovisioned(conn: dbver.Connection) -> None:
    conn.cursor().execute("attach ':memory:' as ?", ("other schema",))
    dbver.check_application_id(1, conn)
    dbver.check_application_id(1, conn, "main")
    dbver.check_application_id(1, conn, "other schema")


def test_zero_nonempty(conn: dbver.Connection) -> None:
    conn.cursor().execute("create table x (x int primary key)")
    with pytest.raises(dbver.VersionError):
        dbver.check_application_id(1, conn)
    with pytest.raises(dbver.VersionError):
        dbver.check_application_id(1, conn, "main")


def test_zero_nonempty_other(conn: dbver.Connection) -> None:
    conn.cursor().execute("attach ':memory:' as ?", ("other schema",))
    conn.cursor().execute('create table "other schema".x ' "(x int primary key)")
    with pytest.raises(dbver.VersionError):
        dbver.check_application_id(1, conn, "other schema")
