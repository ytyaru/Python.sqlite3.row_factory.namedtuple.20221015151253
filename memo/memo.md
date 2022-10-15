【Python】sqlite3.connect.row_factoryでnamedtuple型にする薄いラッパーを書いた

　`.id`のようにドットで参照したくて。`[0]`や`['id']`は嫌だったから。

<!-- more -->

# ブツ

* [リポジトリ][]

[リポジトリ]:Python.sqlite3.row_factory.namedtuple.20221015151253

```sh
```

# 目的

　selectしたときの列を`r.name`としてプロパティで参照したい。それができる薄いラッパ`NtLite`を書いた。

```python
from ntlite import NtLite
db = NtLite(path)
db.exec("create table users(id integer, name text);")
db.exec("insert into users values(?,?,?);", [(0,'A'),(1,'B')])
db.get("select count(*) num from users;").num #=> 2
rows = db.gets("select * from users;")
rows[0].id   #=> 0
rows[0].name #=> A
rows[1].id   #=> 1
rows[1].name #=> B
```

　列名を変数にして取得するなら`getattr()`を使う。ここは`rows[0]['id']`のように参照したかった。残念。

```python
for key in ['id', 'name']:
    getattr(rows[0], key) #=> 0, A
```

## 裸のままだとインデックス参照しかできない

　[sqlite3][]をそのまま使うと列を参照するときインデックスで指定せねばならない。

[sqlite3]:https://docs.python.org/ja/3/library/sqlite3.html

```sql
import sqlite3
con = sqlite3.connect(':memory:')
cur = con.cursor()
cur.execute("create table users(id integer, name text);")
cur.executemany("insert into users values(?,?,?);", [(0,'A'),(1,'B')])
rows = cur.execute("select * from users;").fetchall()
rows[0][0] # 0
rows[0][1] # A
rows[1][0] # 1
rows[1][1] # B
```

　`0`番目は`id`である。`1`番目は`name`である。それを知るには`create table`文を見る必要がある。位置を数えて頭の中で名前と紐づけてインデックスに変換してコードを書くことになる。コードを読むときも同じ。すごく読みにくい。マジックナンバーやめて。どの列を指しているかさっぱり分からない。列名で参照したい。

## [row_factory][]の[sqlite3.Row][]を使うと冗長

　これでも名前で指定できる。でも`['']`と4字もあって長い。

[row_factory]:https://docs.python.org/ja/3/library/sqlite3.html#sqlite3.Connection.row_factory
[sqlite3.Row]:https://docs.python.org/ja/3/library/sqlite3.html#sqlite3.Row

```python
import sqlite3
con = sqlite3.connect(':memory:')
con.row_factory = sqlite3.Row
cur = con.cursor()
cur.execute("create table users(id integer, name text);")
cur.executemany("insert into users values(?,?,?);", [(0,'A'),(1,'B')])
rows = cur.execute("select * from users;").fetchall()
rows[0]['id']   # 0
rows[0]['name'] # A
rows[1]['id']   # 1
rows[1]['name'] # B
```

## [namedtuple][]なら短く書ける

[namedtuple]:https://docs.python.org/ja/3/library/collections.html#collections.namedtuple

　[row_factory][]を自前で実装し、[namedtuple][]を返すようにする。

```python
import sqlite3
from collections import namedtuple
class NtLite:
    def __init__(self, path=':memory:'):
        self._path = path
        self._con = sqlite3.connect(path)
        self._con.row_factory = self._namedtuple_factory
    def _namedtuple_factory(self, cursor, row):
        Row = namedtuple('Row', list(map(lambda d: d[0], cursor.description)))
        return Row(*row)
```

　`_namedtuple_factory()`がそれ。引数の`self`は飛ばして`cursor`, `row`はコールバック関数の引数。`sqlite3`が`fetchall()`や`fetchone()`を実行したときにこのメソッドが呼び出される。

　レコードを`Row`クラスとして[namedtuple][]で定義している。その型をインスタンス化して、実際にSQLで取得されたレコードの列名と値をセットしたものを返している。

　[cursor.description][]はクエリ実行直後の列名を返す。ちょっと特殊で7つの要素があるが、先頭以外はすべて`None`が入っているので`[0]`だけもらう。`select`文に続く列名が取得される。`select`文では好きな列を指定して返すように書けるので、それに合わせて必要な列名とその値だけを取得し、`Row`型として定義している。

　値はコールバック引数の`row`でもらえる。それを展開して[namedtuple][]のコンストラクタに渡すことで1行分のレコードデータが完成。あとはそれを`return`で返して終わり。

[cursor.description]:https://docs.python.org/ja/3/library/sqlite3.html#sqlite3.Cursor.description

# ラッパを書く

　[namedtuple][]で返すような[sqlite3][]の薄いラッパを書いた。

* DBファイルパスを渡す
* SQLを渡す
	* 任意でpreperd statementにする
* 必要なら`connect`や`cursor`も参照する

　`connect`や`cursor`を意識したくなかったので`commit`や`rollback`のようなよく使いそうなものだけラップした。

```python
import sqlite3
from collections import namedtuple
class NtLite:
    def __init__(self, path=':memory:'):
        self._path = path
        self._con = sqlite3.connect(path)
        self._con.row_factory = self._namedtuple_factory # sqlite3.Row
        self._cur = self._con.cursor()
    def __del__(self): self._con.close()
    def exec(self, sql, params=()): return self.con.execute(sql, params)
    def execm(self, sql, params=()): return self.con.executemany(sql, params)
    def execs(self, sql): return self.con.executescript(sql)
    def get(self, sql, params=()): return self.exec(sql, params).fetchone()
    def gets(self, sql, params=()): return self.exec(sql, params).fetchall()
    def _namedtuple_factory(self, cursor, row):
        Row = namedtuple('Row', list(map(lambda d: d[0], cursor.description)))
        return Row(*row)
    def commit(self): return self.con.commit()
    def rollback(self): return self.con.rollback()
    @property
    def con(self): return self._con
    @property
    def cur(self): return self._cur
    @property
    def path(self): return self._path
```

　このNtLiteクラスをインポートして使ってみたのが冒頭にも出した下のコード。

```python
from ntlite import NtLite
db = NtLite(path)
db.exec("create table users(id integer, name text);")
db.exec("insert into users values(?,?,?);", [(0,'A'),(1,'B')])
db.get("select count(*) num from users;").num #=> 2
rows = db.gets("select * from users;")
rows[0].id   #=> 0
rows[0].name #=> A
rows[1].id   #=> 1
rows[1].name #=> B
```

　`.num`、`.id`、`.name`のようにドットで参照できる。`[0]`でも`['id']`でもない。OK！

# 単体テストする

```python
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
```

　実行する。問題なし。

```sh
$ test-ntlite.py
...........
----------------------------------------------------------------------
Ran 11 tests in 0.015s

OK
```


　列とその値を





# コード


# selectしたときの列を`r.name`としてプロパティで参照したい

# そのまま使う

　[sqlite3][]をそのまま使うと列を参照するとき名前でなくインデックスで指定せねばならない。

[sqlite3]:https://docs.python.org/ja/3/library/sqlite3.html

```sql
import sqlite3
con = sqlite3.connect(':memory:')
cur = con.cursor()
cur.execute("create table users(id integer, name text);")
cur.executemany("insert into users values(?,?,?);", [(0,'A'),(1,'B')])
rows = cur.execute("select * from users;").fetchall()
rows[0][0] # 0
rows[0][1] # A
rows[1][0] # 1
rows[1][1] # B
```

# [row_factory][]を使う

[row_factory]:https://docs.python.org/ja/3/library/sqlite3.html#sqlite3.Connection.row_factory


con = sqlite3.connect(':memory:')

```
