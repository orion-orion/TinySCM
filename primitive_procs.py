# -*- coding: utf-8 -*-
"""This module implements the primitive procedures of the Scheme language."""
import numbers
import operator
from internal_ds import Pair, nil


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
    `PRIMITIVE_PROCS`."""
    def add(fn):
        PRIMITIVE_PROCS.append((fn, name, use_env))
        return fn
    return add


def validate_type(val, predicate, k, name):
    """Return `val`.  Raises a SchemeError if `not predicate(val)`
    using "argument <k> of <name>" to describe the offending value."""
    if not predicate(val):
        msg = "argument {0} of {1} has wrong type ({2})"
        type_name = type(val).__name__
        if (val):
            type_name = "symbol"
        raise SchemeError(msg.format(k, name, type_name))
    return val


####################
# Core Interpreter #
####################


def scheme_open(filename):
    """If either "<filename>" or "<filename>.scm" is the name of a valid file,
    return a Python file opened to it. Otherwise, raise an error."""
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
    """Load a Scheme source file. `args` should be of the form (<symol>,
    <environment>) or (<symbol>, <quiet>, <environment>). The file named
    `symbol` is loaded into Frame `env`, with verbosity determined by `quiet`
    (default true)."""
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
    """
    Load all ".scm" files in the given directory, alphabetically.
    """
    assert is_scheme_string(directory)
    directory = directory[1:-1]
    import os
    for x in sorted(os.listdir(".")):
        if not x.endswith(".scm"):
            continue
        scheme_load(x, env)

####################
#   Type Checking  #
####################


@primitive("boolean?")
def is_scheme_boolean(x):
    return x is True or x is False


@primitive("list?")
def is_scheme_list(x):
    """Return whether x is a well-formed Scheme list. Assumes no cycles."""
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


@primitive("string?")
def is_scheme_string(x):
    return isinstance(x, str) and x.startswith("\"")


@primitive("symbol?")
def is_scheme_symbol(x):
    return isinstance(x, str) and not is_scheme_string(x)


################################
#  Pair and List Manipulation  #
################################


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


@primitive("cons")
def scheme_cons(x, y):
    return Pair(x, y)


@primitive("list")
def scheme_list(*vals):
    result = nil
    for e in reversed(vals):
        result = Pair(e, result)
    return result

#########################
# Arithmetic Operations #
#########################


def _check_nums(*vals):
    """Check that all arguments in `vals` are Scheme numbers."""
    for i, v in enumerate(vals):
        if not is_scheme_number(v):
            msg = "operand {0} ({1}) is not a number"
            raise SchemeError(msg.format(i, v))


def _arith(fn, init, vals):
    """Perform the `fn` operation on the number values of `vals`, with `init`
    as the value when `vals` is empty. Returns the result as a Scheme value."""
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
