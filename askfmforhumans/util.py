from typing import Any


def prepare_config(
    config: dict[str, Any],
    schema: dict[str, Any],
    allow_extra: bool = True,
    schema_name: str = "<unnamed>",
):
    if not allow_extra:
        for key in config:
            assert (
                key in schema
            ), f"Key {key!r} not allowed in config schema {schema_name!r}"
    res = {}
    for key, val in schema.items():
        if key in config:
            res[key] = config[key]
        else:
            assert (
                val is not ...
            ), f"Key {key!r} required in config schema {schema_name!r}"
            res[key] = val
    return res
