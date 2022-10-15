#!/usr/bin/env python3
# coding: utf8
import unittest
import os
from dataclasses import dataclass, field, Field
from decimal import Decimal
from datetime import datetime, date, time
from ntlite import NtLite
class TestNtLite(unittest.TestCase):
    def setUp(self): pass
    def tearDown(self): pass
    def test_init_args_0(self):
        db = NtLite()
        self.assertEqual(':memory:', db.path)
        self.assertTrue(db.con)
        self.assertTrue(db.cur)
    def test_init_args_1(self):
        path = 'my.db'
        if os.path.isfile(path): os.remove(path)
        db = NtLite(path)
        self.assertEqual(path, db.path)
        self.assertTrue(os.path.isfile(path))
        if os.path.isfile(path): os.remove(path)
    def test_exec(self):
        db = NtLite()
        res = db.exec("create table users(id integer, name text, age integer);")
        self.assertEqual(None, res.fetchone())
        self.assertEqual([], res.fetchall())
    def test_exec_error(self):
        db = NtLite()
        res = db.exec("create table users(id integer, name text, age integer);")
        with self.assertRaises(ValueError) as cm:
            db.exec("select count(*) from users;").fetchone()
        self.assertEqual(cm.exception.args[0], "Type names and field names must be valid identifiers: 'count(*)'")
    def test_exec_rename_col(self):
        db = NtLite()
        db.exec("create table users(id integer, name text, age integer);")
        res = db.exec("select count(*) num from users;").fetchone()
        self.assertEqual(0, res.num)
    def test_execm(self):
        db = NtLite()
        db.exec("create table users(id integer, name text, age integer);")
        db.execm("insert into users values(?,?,?);", [(0,'A',7),(1,'B',8)])
        self.assertEqual(2, db.exec("select count(*) num from users;").fetchone().num)
        db.con.commit()
    def test_execs(self):
        db = NtLite()
        sql = """
begin;
create table users(id integer, name text, age integer);
insert into users values(0,'A',7);
insert into users values(1,'B',8);
commit;
"""
        db.execs(sql)
        self.assertEqual(2, db.exec("select count(*) num from users;").fetchone().num)
    def test_get(self):
        db = NtLite()
        db.exec("create table users(id integer, name text, age integer);")
        db.execm("insert into users values(?,?,?);", [(0,'A',7),(1,'B',8)])
        self.assertEqual(2, db.get("select count(*) num from users;").num)
    def test_get_preperd(self):
        db = NtLite()
        db.exec("create table users(id integer, name text, age integer);")
        db.execm("insert into users values(?,?,?);", [(0,'A',7),(1,'B',8)])
        self.assertEqual('A', db.get("select name from users where id=?;", (0,)).name)
    def test_gets(self):
        db = NtLite()
        db.exec("create table users(id integer, name text, age integer);")
        db.execm("insert into users values(?,?,?);", [(0,'A',7),(1,'B',8)])
        rows = db.gets("select name num from users order by name asc;")
        self.assertEqual('A', rows[0].num)
        self.assertEqual('B', rows[1].num)
    def test_gets_preperd(self):
        db = NtLite()
        db.exec("create table users(id integer, name text, age integer);")
        db.execm("insert into users values(?,?,?);", [(0,'A',7),(1,'B',8),(2,'C',6)])
        rows = db.gets("select name from users where age < ? order by name asc;", (8,))
        self.assertEqual('A', rows[0].name)
        self.assertEqual('C', rows[1].name)
 

if __name__ == '__main__':
    unittest.main()
