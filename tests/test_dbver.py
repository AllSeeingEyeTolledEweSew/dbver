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
import sqlite3
from typing import cast
from typing import Collection
from typing import List
from typing import Mapping
from typing import Optional
from typing import Tuple
import unittest

import dbver


def _create_conn() -> sqlite3.Connection:
    return sqlite3.Connection(":memory:", isolation_level=None)


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
        self,
        new_format: Optional[str],
        conn: dbver.Connection,
        schema: str = "main",
    ) -> None:
        assert new_format is not None
        super().set_format(new_format, conn, schema=schema)
        cur = conn.cursor()
        cur.execute(f'drop table if exists "{schema}".format')
        cur.execute(f'create table "{schema}".format (name text not null)')
        cur.execute(f'insert into "{schema}".format (name) values (?)', (new_format,))


class NamedFormatMigrationsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.migrations = NamedFormatMigrations(application_id=1)

        @self.migrations.migrates(None, "A")
        def migrate_null_a(conn: dbver.Connection, schema: str = "main") -> None:
            conn.cursor().execute(f'create table "{schema}".a (a int primary key)')

        @self.migrations.migrates(None, "B")
        def migrate_null_b(conn: dbver.Connection, schema: str = "main") -> None:
            conn.cursor().execute(f'create table "{schema}".b (b int primary key)')

        @self.migrations.migrates("A", "B")
        def migrate_a_b(conn: dbver.Connection, schema: str = "main") -> None:
            cur = conn.cursor()
            cur.execute(f'create table "{schema}".b (b int primary key)')
            cur.execute(f'insert into "{schema}".b select * from "{schema}".a')
            cur.execute(f'drop table "{schema}".a')

        @self.migrations.migrates("B", "A")
        def migrate_b_a(conn: dbver.Connection, schema: str = "main") -> None:
            cur = conn.cursor()
            cur.execute(f'create table "{schema}".a (a int primary key)')
            cur.execute(f'insert into "{schema}".a select * from "{schema}".b')
            cur.execute(f'drop table "{schema}".b')

        self.conn = _create_conn()
        self.conn.cursor().execute("attach ':memory:' as ?", ("other schema",))

    def assert_migration_map(
        self,
        mapping: Mapping[Optional[str], dbver.Migration],
        targets: Collection[Optional[str]],
    ) -> None:
        self.assertEqual(set(mapping.keys()), set(targets))
        for migration in mapping.values():
            self.assertTrue(callable(migration))

    def test_mapping(self) -> None:
        self.assert_migration_map(self.migrations[None], {"A", "B"})
        self.assert_migration_map(self.migrations["A"], {"B"})
        self.assert_migration_map(self.migrations["B"], {"A"})

        self.assertEqual(self.migrations.get("does_not_exist"), None)

        self.assertEqual(len(self.migrations), 3)
        self.assertEqual(
            collections.Counter(iter(self.migrations)),
            collections.Counter((None, "A", "B")),
        )

    def test_unprovisioned(self) -> None:
        self.assertIsNone(self.migrations.get_format(self.conn))
        self.assertIsNone(self.migrations.get_format(self.conn, "main"))
        self.assertIsNone(self.migrations.get_format(self.conn, "other schema"))

    def test_invalid_application_id(self) -> None:
        self.conn.cursor().execute("pragma application_id = 2")
        with self.assertRaises(dbver.VersionError):
            self.migrations.get_format(self.conn)

    def test_nonempty_db(self) -> None:
        self.conn.cursor().execute("create table x (x int primary key)")
        with self.assertRaises(dbver.VersionError):
            self.migrations.get_format(self.conn)

    def test_provision_a(self) -> None:
        self.migrations[None]["A"](self.conn, "main")
        self.assertEqual(self.migrations.get_format(self.conn), "A")
        self.conn.cursor().execute("insert into a (a) values (?)", (1,))

        self.migrations[None]["A"](self.conn, "other schema")
        self.assertEqual(self.migrations.get_format(self.conn, "other schema"), "A")
        self.conn.cursor().execute('insert into "other schema".a (a) values (?)', (1,))

    def test_provision_b(self) -> None:
        self.migrations[None]["B"](self.conn, "main")
        self.assertEqual(self.migrations.get_format(self.conn), "B")
        self.conn.cursor().execute("insert into b (b) values (?)", (1,))

        self.migrations[None]["B"](self.conn, "other schema")
        self.assertEqual(self.migrations.get_format(self.conn, "other schema"), "B")
        self.conn.cursor().execute('insert into "other schema".b (b) values (?)', (1,))

    def test_migrate_a_b(self) -> None:
        self.migrations[None]["A"](self.conn, "main")
        self.assertEqual(self.migrations.get_format(self.conn), "A")
        cur = self.conn.cursor()
        cur.execute("insert into a (a) values (?)", (1,))
        self.migrations["A"]["B"](self.conn, "main")
        self.assertEqual(self.migrations.get_format(self.conn), "B")
        cur.execute("select * from b")
        self.assertEqual(cast(List[Tuple[int]], cur.fetchall()), [(1,)])

        self.migrations[None]["A"](self.conn, "other schema")
        self.assertEqual(self.migrations.get_format(self.conn, "other schema"), "A")
        cur = self.conn.cursor()
        cur.execute('insert into "other schema".a (a) values (?)', (1,))
        self.migrations["A"]["B"](self.conn, "other schema")
        self.assertEqual(self.migrations.get_format(self.conn, "other schema"), "B")
        cur.execute('select * from "other schema".b')
        self.assertEqual(cast(List[Tuple[int]], cur.fetchall()), [(1,)])

    def test_migrate_b_a(self) -> None:
        self.migrations[None]["B"](self.conn, "main")
        self.assertEqual(self.migrations.get_format(self.conn), "B")
        cur = self.conn.cursor()
        cur.execute("insert into b (b) values (?)", (1,))
        self.migrations["B"]["A"](self.conn, "main")
        self.assertEqual(self.migrations.get_format(self.conn), "A")
        cur.execute("select * from a")
        self.assertEqual(cast(List[Tuple[int]], cur.fetchall()), [(1,)])

        self.migrations[None]["B"](self.conn, "other schema")
        self.assertEqual(self.migrations.get_format(self.conn, "other schema"), "B")
        cur = self.conn.cursor()
        cur.execute('insert into "other schema".b (b) values (?)', (1,))
        self.migrations["B"]["A"](self.conn, "other schema")
        self.assertEqual(self.migrations.get_format(self.conn, "other schema"), "A")
        cur.execute('select * from "other schema".a')
        self.assertEqual(cast(List[Tuple[int]], cur.fetchall()), [(1,)])


class UserVersionMigrationsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.migrations = dbver.UserVersionMigrations[dbver.Connection](
            application_id=1
        )

        @self.migrations.migrates(0, 1)
        def migrate_0_1(conn: dbver.Connection, schema: str) -> None:
            conn.cursor().execute(f'create table "{schema}".a (a int primary key)')

        @self.migrations.migrates(1, 2)
        def migrate_1_2(conn: dbver.Connection, schema: str) -> None:
            cur = conn.cursor()
            cur.execute(f'create table "{schema}".a2 (a int primary key)')
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
        self.assertEqual(version, 2)
        self.assertEqual(self.migrations.get_format(self.conn), 2)

        version = self.migrations.upgrade(self.conn, "other schema")
        self.assertEqual(version, 2)
        self.assertEqual(self.migrations.get_format(self.conn, "other schema"), 2)

    def test_upgrade_nonbreaking(self) -> None:
        self.migrations[0][1](self.conn, "main")
        self.assertEqual(self.migrations.get_format(self.conn), 1)

        version = self.migrations.upgrade(self.conn)
        self.assertEqual(version, 1)

    def test_upgrade_breaking(self) -> None:
        self.migrations[0][1](self.conn, "main")
        self.assertEqual(self.migrations.get_format(self.conn), 1)

        version = self.migrations.upgrade(self.conn, breaking=True)
        self.assertEqual(version, 2)

    def test_upgrade_condition(self) -> None:
        def condition(orig: int, new: int) -> bool:
            return new <= 1

        version = self.migrations.upgrade(self.conn, condition=condition)
        self.assertEqual(version, 1)


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
