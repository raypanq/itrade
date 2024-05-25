from datetime import datetime, timezone
import math
from decimal import Decimal
import string, random

def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)

def utc_date(timestamp:float) -> datetime:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)

def trunc(n, prec:int=2) -> Decimal:
    result = math.floor(n * 10 ** prec) / 10 ** prec
    # 这里用 str 转一下是因为 result 是 float, 虽然显示是n位数, 其实后面会带无限尾数小数
    # 如果直接转换成 decimal 会连带把后面的小数传过去
    # 先转成 str 就不会带有后面的小数了
    return Decimal(str(result))

def random_str(len:int=10) -> str:
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=len))