import json
from pathlib import Path
from . import Cacheable

class Cacher(Cacheable):
    def __init__(self, filepath: Path) -> None:
        self._filepath = filepath

    def update(self, new_kvs:dict):
        if self._filepath.exists():
            with open(self._filepath, "r") as file:
                old_jsonstr = file.read()
                old_dict = json.loads(old_jsonstr)
                new_dict = {**old_dict, **new_kvs}
            with open(self._filepath, "w") as file:
                file.write(json.dumps(new_dict))
        else:
            with open(self._filepath, "w") as file:
                file.write(json.dumps(new_kvs))

    def get_val(self, key:str):
        if self._filepath.exists():
            with open(self._filepath, "r") as file:
                old_jsonstr = file.read()
                old_dict = json.loads(old_jsonstr)
                return old_dict.get(key)

