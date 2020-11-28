from numbers import Number

from pipda import register_func
from .common import Collection, UnaryNeg
from .utils import select_columns, filter_columns

__all__ = (
    'c', '__neg__',
    'starts_with', 'ends_with', 'contains', 'matches', 'num_range',
    'everything',
    'columns_between', 'columns_from', 'columns_to',
    'where', 'last_col',
    'seq', 'seq_along', 'seq_len',
)

@register_func
def c(_data, *args):
    return Collection(args)

@register_func
def __neg__(_data, operand):
    if isinstance(operand, Number):
        return -operand
    return UnaryNeg(operand)

@register_func
def __invert__(_data, operand):
    return UnaryNeg(operand)

@register_func
def starts_with(_data, match, ignore_case=True, vars=None):
    return filter_columns(vars or _data.columns,
                          match,
                          ignore_case,
                          lambda mat, cname: cname.startswith(mat))

@register_func
def ends_with(_data, match, ignore_case=True, vars=None):
    return filter_columns(vars or _data.columns,
                          match,
                          ignore_case,
                          lambda mat, cname: cname.endswith(mat))

@register_func
def contains(_data, match, ignore_case=True, vars=None):
    return filter_columns(vars or _data.columns,
                          match,
                          ignore_case,
                          lambda mat, cname: mat in cname)

@register_func
def matches(_data, match, ignore_case=True, vars=None):
    import re
    return filter_columns(vars or _data.columns,
                          match,
                          ignore_case,
                          lambda mat, cname: re.search(mat, cname))

@register_func
def num_range(_data, prefix, range, width=None, vars=None):
    return [f'{prefix}{elem if not width else str(elem).zfill(width)}'
            for elem in range]

@register_func
def everything(_data):
    return _data.columns.to_list()

@register_func
def columns_between(_data, start_col, end_col, inclusive=True):
    colnames = _data.columns.to_list()
    if not isinstance(start_col, int):
        start_col = colnames.index(start_col)
    if not isinstance(end_col, int):
        end_col = colnames.index(end_col)
    if inclusive:
        end_col += 1

    return colnames[start_col:end_col]

@register_func
def columns_from(_data, start_col):
    return columns_between.__pipda__(_data, start_col, _data.shape[1])

@register_func
def columns_to(_data, end_col, inclusive=True):
    return columns_between.__pipda__(_data, 0, end_col, inclusive)

@register_func
def where(_data, filter):
    return [column for column in _data.columns if filter(_data[column])]

@register_func
def last_col(_data):
    return _data.columns[-1]

@register_func
def all_of(_data, column, *columns):
    return select_columns(_data, column, *columns)

@register_func
def any_of(_data, column, *columns):
    return select_columns(_data, column, *columns, raise_nonexist=False)

@register_func
def seq_along(_data, along_with):
    return list(range(len(along_with)))

@register_func
def seq_len(_data, length_out):
    return list(range(length_out))

@register_func
def seq(_data, from_=None, to=None, by=None, length_out=None, along_with=None):
    if along_with is not None:
        return seq_along.__pipda__(_data, along_with)
    if from_ is not None and not isinstance(from_, Number):
        return seq_along.__pipda__(_data, from_)
    if length_out is not None and from_ is None and to is None:
        return seq_len.__pipda__(_data, length_out)

    if from_ is None:
        from_ = 0
    elif to is None:
        from_, to = 0, from_

    if length_out is not None:
        by = (float(to) - float(from_)) / float(length_out)
    elif by is None:
        by = 1
        length_out = to - from_
    else:
        length_out = (to - from_ + by - by/10.0) // by
    return [from_ + n * by for n in range(int(length_out))]

