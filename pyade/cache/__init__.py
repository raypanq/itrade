from typing import Protocol

class Cacheable(Protocol):
    @staticmethod
    def update(new_kvs:dict):
        raise NotImplementedError()

    @staticmethod
    def get_val(key:str):
        raise NotImplementedError()
