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
        dbver.get_user_version(conn, 1)  # type: ignore
    with pytest.raises(ValueError):
        dbver.get_user_version(conn, 'invalid"schema')


def test_get_zero(conn: dbver.Connection) -> None:
    conn.cursor().execute("attach ':memory:' as ?", ("other schema",))
    assert dbver.get_user_version(conn) == 0
    assert dbver.get_user_version(conn, "main") == 0
    assert dbver.get_user_version(conn, "other schema") == 0


def test_get_after_set(conn: dbver.Connection) -> None:
    conn.cursor().execute("attach ':memory:' as ?", ("other schema",))
    conn.cursor().execute("pragma user_version = 1")
    conn.cursor().execute('pragma "other schema".user_version= 2')
    assert dbver.get_user_version(conn) == 1
    assert dbver.get_user_version(conn, "main") == 1
    assert dbver.get_user_version(conn, "other schema") == 2
