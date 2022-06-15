# PySSG - Json

try:
    from orjson import loads, dumps as ordumps
except ImportError:
    from json import loads, dumps
else:
    dumps = lambda *args, **kwargs: ordumps(*args, **kwargs).decode()