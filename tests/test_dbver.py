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

import sqlite3
import unittest

import dbver


def _create_conn() -> sqlite3.Connection:
    return sqlite3.Connection(":memory:", isolation_level=None)


class SemverMigrationsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.migrations = dbver.SemverMigrations[dbver.Connection](application_id=1)

        @self.migrations.migrates(0, 1000000)
        def migrate_1(conn: dbver.Connection, schema: str) -> None:
            conn.cursor().execute(f'create table "{schema}".a (a int primary key)')

        @self.migrations.migrates(1000000, 1001000)
        def migrate_1dot1(conn: dbver.Connection, schema: str) -> None:
            cur = conn.cursor()
            cur.execute(f'alter table "{schema}".a add column t text')

        @self.migrations.migrates(1001000, 2000000)
        def migrate_2(conn: dbver.Connection, schema: str) -> None:
            cur = conn.cursor()
            cur.execute(f'create table "{schema}".a2 (a int primary key, t text)')
            cur.execute(f'insert into "{schema}".a2 select * from "{schema}".a')
            cur.execute(f'drop table "{schema}".a')

        self.conn = _create_conn()
        self.conn.cursor().execute("attach ':memory:' as ?", ("other schema",))

    def test_unprovisioned(self) -> None:
        self.assertEqual(self.migrations.get_format(self.conn), 0)
        self.assertEqual(self.migrations.get_format(self.conn, "main"), 0)
        self.assertEqual(self.migrations.get_format(self.conn, "other schema"), 0)

    def test_invalid_application_id(self) -> None:
        self.conn.cursor().execute("pragma application_id = 2")
        with self.assertRaises(dbver.VersionError):
            self.migrations.get_format(self.conn)

    def test_invalid_version_progression(self) -> None:
        with self.assertRaises(AssertionError):

            @self.migrations.migrates(2, 1)
            def migrate_backward(conn: dbver.Connection, schema: str) -> None:
                pass  # pragma: no cover

    def test_nonempty_db(self) -> None:
        self.conn.cursor().execute("create table x (x int primary key)")
        with self.assertRaises(dbver.VersionError):
            self.migrations.get_format(self.conn)

    def test_provision(self) -> None:
        version = self.migrations.upgrade(self.conn)
        self.assertEqual(version, 2000000)
        self.assertEqual(self.migrations.get_format(self.conn), 2000000)

        version = self.migrations.upgrade(self.conn, "other schema")
        self.assertEqual(version, 2000000)
        self.assertEqual(self.migrations.get_format(self.conn, "other schema"), 2000000)

    def test_upgrade_nonbreaking(self) -> None:
        self.migrations[0][1000000](self.conn, "main")
        self.assertEqual(self.migrations.get_format(self.conn), 1000000)

        version = self.migrations.upgrade(self.conn)
        self.assertEqual(version, 1001000)

    def test_upgrade_breaking(self) -> None:
        self.migrations[0][1000000](self.conn, "main")
        self.assertEqual(self.migrations.get_format(self.conn), 1000000)

        version = self.migrations.upgrade(self.conn, breaking=True)
        self.assertEqual(version, 2000000)

    def test_upgrade_condition(self) -> None:
        def condition(orig: int, new: int) -> bool:
            return new <= 1001000

        version = self.migrations.upgrade(self.conn, condition=condition)
        self.assertEqual(version, 1001000)
