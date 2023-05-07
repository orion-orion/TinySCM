# -*- coding: utf-8 -*-
"""This module implements utility methods for checking the structure of Scheme
programs
"""
from internal_ds import repl_str, Pair, nil, Procedure
from primitive_procs import SchemeError, is_scheme_list, is_scheme_symbol


def validate_form(expr, min, max=float('inf')):
    """Checks `expr` is a proper list whose length is at least `min` and no
    more than `max` (default: no maximum). Raises a SchemeError if this is not
    the case.

    >>> validate_form(parser.parse(iter([tokenizer.tokenize("(a b)")])), min=2)
    """
    if not is_scheme_list(expr):
        raise SchemeError('badly formed expression: ' + repl_str(expr))
    length = len(expr)
    if length < min:
        raise SchemeError('too few operands in form')
    elif length > max:
        raise SchemeError('too many operands in form')


def validate_parameters(parameters):
    """Checks that parameters is a valid parameter list, a Scheme list of
    symbols in which each symbol is distinct. Raises a SchemeError if the
    list of parameters is not a list of symbols or if any symbol is repeated.

    >>> validate_parameters(parser.parse(iter([tokenizer.tokenize("(a b c)")] \
    ... )))
    """
    symbols = set()

    def validate_and_add(symbol, is_last):
        if not is_scheme_symbol(symbol):
            raise SchemeError('non-symbol: {0}'.format(symbol))
        if symbol in symbols:
            raise SchemeError('duplicate symbol: {0}'.format(symbol))
        symbols.add(symbol)

    while isinstance(parameters, Pair):
        validate_and_add(parameters.first, parameters.rest is nil)
        parameters = parameters.rest


def validate_procedure(procedure):
    """Checks that `procedure` is a valid Scheme procedure."""
    if not isinstance(procedure, Procedure):
        raise SchemeError('{0} is not callable: {1}'.format(
            type(procedure).__name__.lower(), repl_str(procedure)))
