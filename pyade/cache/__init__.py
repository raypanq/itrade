from typing import Protocol

class Cacheable(Protocol):
    def update(self, new_kvs:dict):
        pass

    def get_val(self, key:str):
        pass
