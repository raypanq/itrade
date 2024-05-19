import string, random
from datetime import datetime, timezone

def random_str(len:int=10) -> str:
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=len))

def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)

def utc_date(timestamp:float) -> datetime:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)
