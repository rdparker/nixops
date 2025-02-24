import json
import collections
import sqlite3
import nixops.util
from typing import Any, List, Iterator, AbstractSet, Tuple, NewType

RecordId = NewType("RecordId", str)


class StateDict(collections.abc.MutableMapping):
    """
    An implementation of a MutableMapping container providing
    a python dict like behavior for the NixOps state file.
    """

    # TODO implement __repr__ for convenience e.g debugging the structure
    def __init__(self, depl, id: RecordId):
        super(StateDict, self).__init__()
        self._db: sqlite3.Connection = depl._db
        self.id = id

    def __setitem__(self, key: str, value: Any) -> None:
        with self._db:
            c = self._db.cursor()
            if value is None:
                c.execute(
                    "delete from ResourceAttrs where machine = ? and name = ?",
                    (self.id, key),
                )
            else:
                v = value
                if isinstance(value, list) or isinstance(value, dict):
                    v = json.dumps(value, cls=nixops.util.NixopsEncoder)
                c.execute(
                    "insert or replace into ResourceAttrs(machine, name, value) values (?, ?, ?)",
                    (self.id, key, v),
                )

    def __getitem__(self, key: str) -> Any:
        with self._db:
            c = self._db.cursor()
            c.execute(
                "select value from ResourceAttrs where machine = ? and name = ?",
                (self.id, key),
            )
            row: Tuple[str] = c.fetchone()
            if row is not None:
                try:
                    v = json.loads(row[0])
                    if isinstance(v, list):
                        v = tuple(v)
                    return v
                except ValueError:
                    return row[0]
            raise KeyError("couldn't find key {} in the state file".format(key))

    def __delitem__(self, key: str) -> None:
        with self._db:
            c = self._db.cursor()
            c.execute(
                "delete from ResourceAttrs where machine = ? and name = ?",
                (self.id, key),
            )

    def keys(self) -> AbstractSet[str]:
        # Generally the list of keys per ResourceAttrs is relatively small
        # so this should be also relatively fast.
        _keys = set()
        with self._db:
            c = self._db.cursor()
            c.execute("select name from ResourceAttrs where machine = ?", (self.id,))
            rows: List[Tuple[str]] = c.fetchall()
            for row in rows:
                _keys.add(row[0])
            return _keys

    def __iter__(self) -> Iterator[str]:
        return iter(self.keys())

    def __len__(self) -> int:
        return len(self.keys())
