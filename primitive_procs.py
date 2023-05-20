# -*- coding: utf-8 -*-
"""This module implements the primitive procedures of the Scheme language.

You can refer to:
https://inst.eecs.berkeley.edu/~cs61a/fa16/articles/scheme-primitives.html
"""
import math
import numbers
import operator
import sys
import os
from internal_ds import Pair, nil, repl_str


class SchemeError(Exception):
    """Exception indicating an error in a Scheme program."""


# A list of triples (<python function>, <function name>,
# <whether to use the environment>).  Added to by function `primitive()`
# and used in `tiny_scm.setup_environment``.
PRIMITIVE_PROCS = []


def primitive(name, use_env=False):
    """`primitive` is a factory function, which can accepet arguments and
    returns a python decorator `add`. The function `add` add triples (<python
    function>, <function name>, <whether to use the environment>) into list
    `PRIMITIVE_PROCS`.
    """
    def add(fn):
        PRIMITIVE_PROCS.append((fn, name, use_env))
        return fn
    return add


def validate_type(val, predicate, k, name):
    """Returns `val`.  Raises a SchemeError if `not predicate(val)`
    using "argument <k> of <name>" to describe the offending value.
    """
    if not predicate(val):
        msg = "argument {0} of {1} has wrong type ({2})"
        type_name = type(val).__name__
        raise SchemeError(msg.format(k, name, type_name))
    return val

##############################
#       Core Interpreter     #
##############################


@primitive("display")
def scheme_display(*vals):
    vals = [repl_str(val[1:-1] if is_scheme_string(val) else val)
            for val in vals]
    print(*vals, end="")


@primitive("displayln")
def scheme_displayln(*vals):
    scheme_display(*vals)
    scheme_newline()


@primitive("error")
def scheme_error(msg=None):
    msg = "" if msg is None else repl_str(msg)
    raise SchemeError(msg)


@primitive("exit")
def scheme_exit():
    raise EOFError


def scheme_open(filename):
    """If either "<filename>" or "<filename>.scm" is the name of a valid file,
    return a Python file opened to it. Otherwise, raise an error.
    """
    try:
        return open(filename)
    except IOError as exc:
        if filename.endswith(".scm"):
            raise SchemeError(str(exc))
    try:
        return open(filename + ".scm")
    except IOError as exc:
        raise SchemeError(str(exc))


@primitive("load", use_env=True)
def scheme_load(*args):
    """Loads a Scheme source file. `args` should be of the form (<symol>,
    <environment>) or (<symbol>, <quiet>, <environment>). The file named
    `symbol` is loaded into Frame `env`, with verbosity determined by `quiet`
    (default true).
    """
    from tiny_scm import read_eval_print_loop
    if not (2 <= len(args) <= 3):
        expressions = args[:-1]
        raise SchemeError("\"load\" given incorrect number of arguments: "
                          "{0}".format(len(expressions)))
    sym = args[0]
    quiet = args[1] if len(args) > 2 else True
    env = args[-1]
    if (is_scheme_string(sym)):
        sym = eval(sym)
    validate_type(sym, is_scheme_symbol, 0, "load")
    with scheme_open(sym) as infile:
        infile_lines = infile.readlines()

    read_eval_print_loop(env, infile_lines=infile_lines,
                         quiet=quiet, report_errors=True)


@primitive("load-all", use_env=True)
def scheme_load_all(directory, env):
    """Loads all ".scm" files in the given directory, alphabetically.
    """
    assert is_scheme_string(directory)
    directory = directory[1:-1]
    for x in sorted(os.listdir(".")):
        if not x.endswith(".scm"):
            continue
        scheme_load(x, env)


@primitive("newline")
def scheme_newline():
    print()
    sys.stdout.flush()


@primitive("print")
def scheme_print(*vals):
    vals = [repl_str(val) for val in vals]
    print(*vals)


@primitive("print-then-return")
def scheme_print_return(val1, val2):
    print(repl_str(val1))
    return val2

##############################
#        Type Checking       #
##############################


def is_scheme_true(val):
    """All values in Scheme are true except False."""
    return val is not False


def is_scheme_false(val):
    """Only False is false in Scheme."""
    return val is False


@primitive("atom?")
def is_scheme_atom(x):
    return (is_scheme_boolean(x) or is_scheme_number(x) or
            is_scheme_symbol(x) or is_scheme_null(x) or is_scheme_string(x))


@primitive("boolean?")
def is_scheme_boolean(x):
    return x is True or x is False


@primitive("integer?")
def is_scheme_integer(x):
    return is_scheme_number(x) and (isinstance(x, numbers.Integral) or int(x)
                                    == x)


@primitive("list?")
def is_scheme_list(x):
    """Returns whether x is a well-formed Scheme list. Assumes no cycles."""
    while x is not nil:
        if not isinstance(x, Pair):
            return False
        x = x.rest
    return True


@primitive("number?")
def is_scheme_number(x):
    """Check whether `x` is a Scheme number. Note:
    >>> import numbers
    >>> isinstance(False, numbers.Real)
    True
    That is why we need `not is_scheme_boolean(x)`.
    """

    return isinstance(x, numbers.Real) and not is_scheme_boolean(x)


@primitive("null?")
def is_scheme_null(x):
    return x is nil


@primitive("pair?")
def is_scheme_pair(x):
    return isinstance(x, Pair)


@primitive("procedure?")
def is_scheme_procedure(x):
    from internal_ds import Procedure
    return isinstance(x, Procedure)


@primitive("promise?")
def is_scheme_promise(obj):
    from internal_ds import Promise
    return isinstance(obj, Promise)


@primitive("scheme-valid-cdr?")
def is_scheme_valid_cdr(x):
    return is_scheme_pair(x) or is_scheme_null(x) or is_scheme_promise(x)


@primitive("string?")
def is_scheme_string(x):
    return isinstance(x, str) and x.startswith("\"")


@primitive("symbol?")
def is_scheme_symbol(x):
    return isinstance(x, str) and not is_scheme_string(x)

##############################
# Pair and List Manipulation #
##############################


@primitive("append")
def scheme_append(*vals):
    if len(vals) == 0:
        return nil
    result = vals[-1]
    for i in range(len(vals)-2, -1, -1):
        v = vals[i]
        if v is not nil:
            validate_type(v, is_scheme_pair, i, "append")
            r = p = Pair(v.first, result)
            v = v.rest
            while is_scheme_pair(v):
                p.rest = Pair(v.first, result)
                p = p.rest
                v = v.rest
            result = r
    return result


@primitive("car")
def scheme_car(x):
    validate_type(x, is_scheme_pair, 0, "car")
    return x.first


@primitive("cdr")
def scheme_cdr(x):
    validate_type(x, is_scheme_pair, 0, "cdr")
    return x.rest


@primitive("cons")
def scheme_cons(x, y):
    return Pair(x, y)


@primitive("length")
def scheme_length(x):
    validate_type(x, is_scheme_list, 0, "length")
    if x is nil:
        return 0
    return len(x)


@primitive("list")
def scheme_list(*vals):
    result = nil
    for e in reversed(vals):
        result = Pair(e, result)
    return result

##############################
#    Arithmetic Operations   #
##############################


def _check_nums(*vals):
    """Checks that all arguments in `vals` are Scheme numbers."""
    for i, v in enumerate(vals):
        if not is_scheme_number(v):
            msg = "operand {0} ({1}) is not a number"
            raise SchemeError(msg.format(i, v))


def _arith(fn, init, vals):
    """Performs the `fn` operation on the number values of `vals`, with `init`
    as the value when `vals` is empty. Returns the result as a Scheme value.
    """
    _check_nums(*vals)
    s = init
    for val in vals:
        s = fn(s, val)
    s = _ensure_int(s)
    return s


def _ensure_int(x):
    if int(x) == x:
        x = int(x)
    return x


@primitive("+")
def scheme_add(*vals):
    return _arith(operator.add, 0, vals)


@primitive("-")
def scheme_sub(val0, *vals):
    _check_nums(val0, *vals)  # fixes off-by-one error
    if len(vals) == 0:
        return _ensure_int(-val0)
    return _arith(operator.sub, val0, vals)


@primitive("*")
def scheme_mul(*vals):
    return _arith(operator.mul, 1, vals)


@primitive("/")
def scheme_div(val0, *vals):
    _check_nums(val0, *vals)  # fixes off-by-one error
    try:
        if len(vals) == 0:
            return _ensure_int(operator.truediv(1, val0))
        return _arith(operator.truediv, val0, vals)
    except ZeroDivisionError as err:
        raise SchemeError(err)


@primitive("abs")
def scheme_abs(val0):
    return abs(val0)


@primitive("expt")
def scheme_expt(val0, val1):
    _check_nums(val0, val1)
    return pow(val0, val1)


@primitive("modulo")
def scheme_modulo(val0, val1):
    _check_nums(val0, val1)
    try:
        return val0 % val1
    except ZeroDivisionError as err:
        raise SchemeError(err)


@primitive("quotient")
def scheme_quo(val0, val1):
    _check_nums(val0, val1)
    try:
        return -(-val0 // val1) if (val0 < 0) ^ (val1 < 0) else val0 // val1
    except ZeroDivisionError as err:
        raise SchemeError(err)


@primitive("remainder")
def scheme_remainder(val0, val1):
    _check_nums(val0, val1)
    try:
        result = val0 % val1
    except ZeroDivisionError as err:
        raise SchemeError(err)
    while result < 0 and val0 > 0 or result > 0 and val0 < 0:
        result -= val1
    return result


def number_fn(module, name, fallback=None):
    """A Scheme primitive procedure that calls the numeric Python function
    named `module.name`.
    """
    py_fn = getattr(module, name) if fallback is None else getattr(
        module, name, fallback)

    def scheme_fn(*vals):
        _check_nums(*vals)
        return py_fn(*vals)
    return scheme_fn

# Additional Math Primitives


# Add number functions in the math module as primitive procedures in Scheme
for _name in ["acos", "acosh", "asin", "asinh", "atan", "atan2", "atanh",
              "ceil", "copysign", "cos", "cosh", "degrees", "floor", "log",
              "log10", "log1p", "radians", "sin", "sinh", "sqrt",
              "tan", "tanh", "trunc"]:
    primitive(_name)(number_fn(math, _name))
# Python 2 compatibility
primitive("log2")(number_fn(math, "log2", lambda x: math.log(x, 2)))

##############################
#      Boolean Operations    #
##############################

# General


@primitive("eq?")
def is_scheme_eq(x, y):
    if is_scheme_symbol(x) and is_scheme_symbol(y):
        return x == y
    else:
        return x is y


@primitive("equal?")
def is_scheme_equal(x, y):
    if is_scheme_pair(x) and is_scheme_pair(y):
        return is_scheme_equal(x.first, y.first) \
            and is_scheme_equal(x.rest, y.rest)
    elif is_scheme_number(x) and is_scheme_number(y):
        return x == y
    else:
        return type(x) == type(y) and x == y


@primitive("eqv?")
def is_scheme_eqv(x, y):
    if is_scheme_number(x) and is_scheme_number(y):
        return x == y
    elif is_scheme_symbol(x) and is_scheme_symbol(y):
        return x == y
    else:
        return x is y


@primitive("not")
def scheme_not(x):
    return not is_scheme_true(x)

# On Numbers


def _numcomp(op, x, y):
    _check_nums(x, y)
    return op(x, y)


@primitive("=")
def scheme_eq(x, y):
    return _numcomp(operator.eq, x, y)


@primitive("<")
def scheme_lt(x, y):
    return _numcomp(operator.lt, x, y)


@primitive(">")
def scheme_gt(x, y):
    return _numcomp(operator.gt, x, y)


@primitive("<=")
def scheme_le(x, y):
    return _numcomp(operator.le, x, y)


@primitive(">=")
def scheme_ge(x, y):
    return _numcomp(operator.ge, x, y)


@primitive("even?")
def is_scheme_even(x):
    _check_nums(x)
    return x % 2 == 0


@primitive("odd?")
def is_scheme_odd(x):
    _check_nums(x)
    return x % 2 == 1


@primitive("zero?")
def is_scheme_zero(x):
    _check_nums(x)
    return x == 0

##############################
#       Mutation Extras      #
##############################


@primitive("set-car!")
def scheme_set_car(x, y):
    validate_type(x, is_scheme_pair, 0, "set-car!")
    x.first = y


@primitive("set-cdr!")
def scheme_set_cdr(x, y):
    validate_type(x, is_scheme_pair, 0, "set-cdr!")
    validate_type(y, is_scheme_valid_cdr, 1, "set-cdr!")
    x.rest = y

##############################
#      map/filter/reduce     #
##############################

# Although `map`/`filter`/`reduce` are not primitive procedures (they are
# built-in high order proceduress), we define them here.


@ primitive("map", use_env=True)
def scheme_map(proc, items, env):
    from eval_apply import complete_apply
    validate_type(proc, is_scheme_procedure, 0, "map")
    validate_type(items, is_scheme_list, 1, "map")

    def scheme_map_iter(proc, items, env):
        if is_scheme_null(items):
            return nil
        return scheme_cons(complete_apply(proc, scheme_list(items.first), env),
                           scheme_map_iter(proc, items.rest, env))

    return scheme_map_iter(proc, items, env)


@ primitive("filter", use_env=True)
def scheme_filter(predicate, items, env):
    from eval_apply import complete_apply
    validate_type(predicate, is_scheme_procedure, 0, "filter")
    validate_type(items, is_scheme_list, 1, "filter")

    def scheme_filter_iter(predicate, items, env):
        if is_scheme_null(items):
            return nil
        elif complete_apply(predicate, scheme_list(items.first), env):
            return scheme_cons(items.first, scheme_filter_iter(predicate,
                                                               items.rest, env))
        else:
            return scheme_filter_iter(predicate, items.rest, env)

    return scheme_filter_iter(predicate, items, env)


@ primitive("reduce", use_env=True)
def scheme_reduce(op, items, env):
    from eval_apply import complete_apply
    validate_type(op, is_scheme_procedure, 0, "reduce")
    validate_type(items, lambda x: x is not nil, 1, "reduce")
    validate_type(items, is_scheme_list, 1, "reduce")

    def scheme_reduce_iter(op, initial, items, env):
        if is_scheme_null(items):
            return initial
        return complete_apply(op, scheme_list(items.first,
                                              scheme_reduce_iter(op,
                                                                 initial,
                                                                 items.rest,
                                                                 env)), env)

    return scheme_reduce_iter(op, items.first, items.rest, env)

##############################
#    Promises and Streams    #
##############################


@ primitive("force")
def scheme_force(obj):
    """Note that `force` is a primitive procedure, not a special form
    """
    from eval_apply import scheme_eval

    validate_type(obj, lambda x: is_scheme_promise(x), 0, "stream-force")
    return scheme_eval(obj.expr, obj.env)


@primitive("stream-car")
def stream_car(stream):
    validate_type(stream, lambda x: is_stream_pair(x), 0, "stream-car")
    return stream.first


@primitive("stream-cdr")
def stream_cdr(stream):
    validate_type(stream, lambda x: is_stream_pair(x), 0, "stream-cdr")
    return scheme_force(stream.rest)


@primitive("stream-null?")
def is_stream_null(stream):
    return is_scheme_null(stream)


@primitive("stream-pair?")
def is_stream_pair(obj):
    return is_scheme_pair(obj) and is_scheme_promise(obj.rest)


@primitive("stream-map", use_env=True)
def stream_map(proc, stream, env):
    from eval_apply import complete_apply
    validate_type(proc, is_scheme_procedure, 0, "map")
    validate_type(stream, is_stream_pair, 1, "map")

    def stream_map_iter(proc, stream, env):
        if is_stream_null(stream):
            return nil
        return scheme_cons(complete_apply(proc, scheme_list(stream_car(stream)
                                                            ), env),
                           stream_map_iter(proc, stream_cdr(stream), env))

    return stream_map_iter(proc, stream, env)


@primitive("stream-filter", use_env=True)
def stream_filter(predicate, stream, env):
    from eval_apply import complete_apply
    validate_type(predicate, is_scheme_procedure, 0, "filter")
    validate_type(stream, is_stream_pair, 1, "filter")

    def scheme_filter_iter(predicate, stream, env):
        if is_stream_null(stream):
            return nil
        elif complete_apply(predicate, scheme_list(stream_car(stream)), env):
            return scheme_cons(stream_car(stream),
                               scheme_filter_iter(predicate,
                                                  stream_cdr(stream), env))
        else:
            return scheme_filter_iter(predicate, stream_cdr(stream), env)

    return scheme_filter_iter(predicate, stream, env)


@primitive("stream-reduce", use_env=True)
def stream_reduce(op, stream, env):
    from eval_apply import complete_apply
    validate_type(op, is_scheme_procedure, 0, "reduce")
    validate_type(stream, lambda x: x is not nil, 1, "reduce")
    validate_type(stream, is_stream_pair, 1, "reduce")

    def scheme_reduce_iter(op, initial, stream, env):
        if is_stream_null(stream):
            return initial
        return complete_apply(op, scheme_list(stream_car(stream),
                                              scheme_reduce_iter(op,
                                                                 initial,
                                                                 stream_cdr(
                                                                     stream),
                                                                 env)), env)

    return scheme_reduce_iter(op, stream_car(stream), stream_cdr(stream), env)
