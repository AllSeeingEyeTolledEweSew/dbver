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

import functools
import sqlite3
from typing import Callable

import pytest

import dbver

try:
    import apsw
except ImportError:
    # https://github.com/python/mypy/issues/1153
    apsw = None  # type: ignore


def _conn_factory_sqlite() -> Callable[[], dbver.Connection]:
    return functools.partial(sqlite3.connect, ":memory:", isolation_level=None)


def _conn_factory_apsw() -> Callable[[], dbver.Connection]:
    return functools.partial(apsw.Connection, ":memory:")


@pytest.fixture(
    params=(
        _conn_factory_sqlite,
        pytest.param(
            _conn_factory_apsw,
            marks=pytest.mark.skipif(not apsw, reason="apsw not used"),
        ),
    ),
    ids=("sqlite", "apsw"),
)
def conn_factory(request: pytest.FixtureRequest) -> Callable[[], dbver.Connection]:
    return request.param()  # type: ignore


@pytest.fixture
def conn(conn_factory: Callable[[], dbver.Connection]) -> dbver.Connection:
    return conn_factory()
