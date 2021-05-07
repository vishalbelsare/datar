"""Recode values

https://github.com/tidyverse/dplyr/blob/master/R/recode.R
"""
from typing import Any, Iterable, Mapping, Optional

import numpy
import pandas
from pandas import Categorical, Series
from pandas.core.dtypes.common import is_categorical_dtype
from pipda import register_func

from ..core.contexts import Context
from ..core.utils import logger
from ..core.types import is_scalar
from ..base import NA, unique, c, intersect, NA_integer_, NA_character_

def get_first(x: Iterable[Any]) -> Any:
    """Get first raw item from an iterable"""
    x = x[0]
    try:
        return x.item()
    except AttributeError:
        return x

def args_to_recodings(
        *args: Any,
        _base0: bool = False,
        _force_index: bool = False,
        **kwargs: Any
) -> Mapping[Any, Any]:
    """Convert arguments to replaceable"""
    values = {}
    for i, arg in enumerate(args):
        if isinstance(arg, dict):
            values.update(arg)
        else:
            values[i + int(not _base0)] = arg

    values.update(kwargs)
    if _force_index:
        for key in list(values):
            if isinstance(key, str) and key.isdigit():
                values[int(key)] = values.pop(key)
    return values

def check_length(val: numpy.ndarray, x: numpy.ndarray, name: str):
    """Check the length of the values to recode"""
    length_x = len(val)
    n = len(x)
    if length_x in (1, n):
        return

    if n == 1:
        raise ValueError(
            f"{name} must be length 1, not {length_x}."
        )
    raise ValueError(
        f"{name} must be length {n}, not {length_x}."
    )

def check_type(val: numpy.ndarray, out_type: Optional[type], name: str):
    """Check the type of the values to recode"""
    if val.dtype is numpy.dtype(object):
        if out_type and not all(isinstance(elem, out_type) for elem in val):
            raise TypeError(
                f"{name} must be {out_type.__name__}, not {type(val[0])}."
            )
    elif out_type and not isinstance(get_first(val), out_type):
        raise TypeError(
            f"{name} must be {out_type.__name__}, not {val.dtype.name}."
        )


def replace_with(
        # pylint: disable=invalid-name
        x: numpy.ndarray,
        out_type: Optional[type],
        i: numpy.ndarray,
        val: Any,
        name: str
) -> numpy.ndarray:
    """Replace with given value at index"""
    # https://github.com/tidyverse/dplyr/blob/HEAD/R/utils-replace-with.R
    if val is None:
        return x

    if is_scalar(val):
        val = numpy.array([val])
    else:
        val = numpy.array(val)

    check_length(val, x, name)
    check_type(val, out_type, name)
    # check_class(val, x, name)

    i[pandas.isna(i)] = False

    if len(val) == 1:
        x[i] = val[0]
    else:
        x[i] = val[i]

    return x

def validate_recode_default(
        default: Any,
        x: numpy.ndarray,
        out: numpy.ndarray,
        out_type: Optional[type],
        replaced: numpy.ndarray
) -> numpy.ndarray:
    """Validate default for recoding"""
    default = recode_default(x, default, out_type)
    if (
            default is None and
            sum(replaced & ~pandas.isna(x)) < len(out[~pandas.isna(x)])
    ):
        logger.warning(
            "Unreplaced values treated as NA as `_x` is not compatible. "
            "Please specify replacements exhaustively or supply `_default`",
        )

    return default

def recode_default(
        x: numpy.ndarray,
        default: Any,
        out_type: Optional[type]
) -> Any:
    """Get right default for recoding"""
    if default is None and (
            out_type is None or isinstance(get_first(x), out_type)
    ):
        return x
    return default

def recode_numeric(
        _x: numpy.ndarray,
        *args: Any,
        _default: Any = None,
        _missing: Any = None,
        _base0: bool = False,
        **kwargs: Any
) -> numpy.ndarray:
    """Recode numeric vectors"""

    values = args_to_recodings(
        *args, **kwargs,
        _base0=_base0,
        _force_index=True
    )
    check_args(values, _default, _missing)
    if any(not isinstance(val, int) for val in values):
        raise ValueError(
            "All values must be unnamed (or named with integers)."
        )

    n = len(_x)
    out = numpy.array([NA] * n, dtype=object)
    replaced = numpy.array([False] * n)
    out_type = None

    for val in values:
        if out_type is None:
            out_type = type(values[val])
        out = replace_with(
            out, out_type, _x == val, values[val], f"Element {val}"
        )
        replaced[_x == val] = True

    _default = validate_recode_default(_default, _x, out, out_type, replaced)
    out = replace_with(
        out, out_type, ~replaced & ~pandas.isna(_x), _default, "`_default`"
    )
    out = replace_with(
        out, out_type,
        pandas.isna(_x) | (_x == NA_integer_),
        _missing,
        "`_missing`"
    )
    if out_type and not any(pandas.isna(out)):
        out = out.astype(out_type)
    return out

def recode_character(
        _x: Iterable[Any],
        *args: Any,
        _default: Any = None,
        _missing: Any = None,
        _base0: bool = False,
        **kwargs: Any
) -> numpy.ndarray:
    """Recode character vectors"""
    values = args_to_recodings(*args, **kwargs, _base0=_base0)
    check_args(values, _default, _missing)
    if not all(isinstance(val, str) for val in values):
        raise ValueError("All values must be named.")

    n = len(_x)
    out = numpy.array([NA] * n, dtype=object)
    replaced = numpy.array([False] * n)
    out_type = None

    for val in values:
        if out_type is None:
            out_type = type(values[val])
        out = replace_with(out, out_type, _x == val, values[val], f"`{val}`")
        replaced[_x == val] = True

    _default = validate_recode_default(_default, _x, out, out_type, replaced)
    out = replace_with(
        out, out_type, ~replaced & ~pandas.isna(_x), _default, "`_default`"
    )
    out = replace_with(
        out, out_type,
        pandas.isna(_x) | (_x == NA_character_),
        _missing,
        "`_missing`"
    )
    if out_type and not any(pandas.isna(out)):
        out = out.astype(out_type)
    return out

def check_args(
        values: Mapping[Any, Any],
        default: Any,
        missing: Any
) -> None:
    """Check if any replacement specified"""
    if not values and default is None and missing is None:
        raise ValueError("No replacements provided.")


@register_func(context=Context.EVAL)
def recode(
        _x: Iterable[Any],
        *args: Any,
        _default: Any = None,
        _missing: Any = None,
        _base0: bool = False,
        **kwargs: Any
) -> Iterable[Any]:
    """Recode a vector, replacing elements in it

    Args:
        x: A vector to modify
        *args: and
        **kwargs: replacements
        _default: If supplied, all values not otherwise matched will be
            given this value. If not supplied and if the replacements are
            the same type as the original values in series, unmatched values
            are not changed. If not supplied and if the replacements are
            not compatible, unmatched values are replaced with NA.
        _missing: If supplied, any missing values in .x will be replaced
            by this value.
        _base0: Whether the positional argument replacement is 0-based.

    Returns:
        The vector with values replaced
    """
    if is_scalar(_x):
        _x = [_x]

    if not isinstance(_x, numpy.ndarray):
        _x_obj = numpy.array(_x, dtype=object) # Keep NAs
        _x = numpy.array(_x)
        if numpy.issubdtype(_x.dtype, numpy.str_):
            na_len = len(NA_character_)
            if (_x.dtype.itemsize >> 2) < na_len: # length not enough
                _x = _x.astype(f'<U{na_len}')
            _x[pandas.isna(_x_obj)] = NA_character_
        elif numpy.issubdtype(_x.dtype, numpy.integer):
            _x[pandas.isna(_x_obj)] = NA_integer_

    if numpy.issubdtype(_x.dtype, numpy.number):
        return recode_numeric(
            _x, *args,
            _default=_default,
            _missing=_missing,
            _base0=_base0,
            **kwargs
        )

    return recode_character(
        _x, *args,
        _default=_default,
        _missing=_missing,
        _base0=_base0,
        **kwargs
    )

@recode.register((Categorical, Series), context=Context.EVAL)
def _(
        _x: Iterable[Any],
        *args: Any,
        _default: Any = None,
        _missing: Any = None,
        _base0: bool = False,
        **kwargs: Any
) -> Categorical:
    """Recode factors"""
    if not is_categorical_dtype(_x): # non-categorical Series
        return recode(
            _x.values,
            *args,
            _default=_default,
            _missing=_missing,
            _base0=_base0,
            **kwargs
        )
    if isinstance(_x, Series):
        _x = _x.values # get the Categorical object

    values = args_to_recodings(*args, **kwargs, _base0=_base0)
    if not values:
        raise ValueError("No replacements provided.")

    if not all(isinstance(key, str) for key in values):
        raise ValueError(
            "Named values required for recoding factors/categoricals."
        )

    if _missing is not None:
        raise ValueError("`_missing` is not supported for factors.")

    n = len(_x)
    check_args(values, _default, _missing)
    out = numpy.array([NA] * n, dtype=object)
    replaced = numpy.array([False] * n)
    out_type = None

    for val in values:
        if out_type is None:
            out_type = type(values[val])
        out = replace_with(
            out,
            out_type,
            _x.categories == val,
            values[val],
            f"`{val}`"
        )
        replaced[_x.categories == val] = True

    _default = validate_recode_default(_default, _x, out, out_type, replaced)
    out = replace_with(
        out, out_type, ~replaced, _default, "`_default`"
    )

    if out_type is str:
        return Categorical(out)
    return out[_x.codes]

@register_func(None, context=Context.EVAL)
def recode_factor(
        _x: Iterable[Any],
        *args: Any,
        _default: Any = None,
        _missing: Any = None,
        _ordered: bool = False,
        _base0: bool = False,
        **kwargs: Any
) -> Iterable[Any]:
    """Recode a factor

    see recode().
    """
    values = args_to_recodings(*args, **kwargs, _base0=_base0)
    recoded = recode(
        _x, values,
        _default=_default,
        _missing=_missing,
        _base0=_base0
    )

    out_type = type(get_first(recoded))
    _default = recode_default(_x, _default, out_type)
    all_levels = unique(c(
        list(values.values()),
        [] if _default is None else _default,
        [] if _missing is None else _missing
    ))

    recoded_levels = (
        recoded.categories
        if isinstance(recoded, Categorical)
        else unique(recoded[pandas.notna(recoded)])
    )
    levels = intersect(all_levels, recoded_levels)

    return Categorical(recoded, categories=levels, ordered=_ordered)

recode_categorical = recode_factor # pylint: disable=invalid-name