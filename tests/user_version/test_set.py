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
        dbver.set_user_version(1, conn, 1)  # type: ignore
    with pytest.raises(ValueError):
        dbver.set_user_version(1, conn, 'invalid"schema')


def test_set(conn: dbver.Connection) -> None:
    conn.cursor().execute("attach ':memory:' as ?", ("other schema",))
    dbver.set_user_version(1, conn)
    assert conn.cursor().execute("pragma user_version").fetchall() == [(1,)]

    dbver.set_user_version(2, conn, "main")
    assert conn.cursor().execute("pragma user_version").fetchall() == [(2,)]

    dbver.set_user_version(3, conn, "other schema")
    assert conn.cursor().execute('pragma "other schema".user_version').fetchall() == [
        (3,)
    ]


def test_set_invalid(conn: dbver.Connection) -> None:
    with pytest.raises(ValueError):
        dbver.set_user_version(1 << 40, conn)

    with pytest.raises(ValueError):
        dbver.set_user_version(-(1 << 40), conn)

    with pytest.raises(TypeError):
        dbver.set_user_version("str", conn)  # type: ignore
