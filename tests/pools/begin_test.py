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


class DummyException(Exception):
    pass


LOCK_MODES = (dbver.DEFERRED, dbver.IMMEDIATE, dbver.EXCLUSIVE)


def check_in_transaction(conn: dbver.Connection, in_transaction: bool) -> None:
    with pytest.raises(dbver.Errors):
        conn.cursor().execute("BEGIN" if in_transaction else "COMMIT")


@pytest.mark.parametrize("lock_mode", LOCK_MODES)
def test_success(conn: dbver.Connection, lock_mode: dbver.LockMode) -> None:
    conn.cursor().execute("CREATE TABLE x (x INT PRIMARY KEY)")
    check_in_transaction(conn, False)
    with dbver.begin(conn, lock_mode):
        check_in_transaction(conn, True)
        conn.cursor().execute("INSERT INTO x (x) VALUES (1)")
    check_in_transaction(conn, False)
    assert conn.cursor().execute("SELECT * FROM x").fetchall() == [(1,)]


@pytest.mark.parametrize("lock_mode", LOCK_MODES)
def test_failure(conn: dbver.Connection, lock_mode: dbver.LockMode) -> None:
    conn.cursor().execute("CREATE TABLE x (x INT PRIMARY KEY)")
    check_in_transaction(conn, False)
    with pytest.raises(DummyException):
        with dbver.begin(conn, lock_mode):
            check_in_transaction(conn, True)
            conn.cursor().execute("INSERT INTO x (x) VALUES (1)")
            raise DummyException()
    check_in_transaction(conn, False)
    assert conn.cursor().execute("SELECT * FROM x").fetchall() == []
