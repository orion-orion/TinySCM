
# -*- coding: utf-8 -*-
"""This module implements the eval-apply cycle of the Scheme interpreter.
"""
from internal_ds import repl_str, Pair, nil, LambdaProcedure, MacroProcedure, \
    DLambdaProcedure, Promise, TailPromise, is_primitive_procedure, \
    is_compound_procedure
from primitive_procs import SchemeError, primitive, is_scheme_true, \
    is_scheme_false, is_scheme_boolean, is_scheme_list, is_scheme_number, \
    is_scheme_null, is_scheme_pair, is_scheme_string, is_scheme_symbol, \
    scheme_cons,  scheme_list
from utils import validate_form, validate_parameters, validate_procedure


##############################
#          Eval/Apply        #
##############################


@primitive("eval", use_env=True)
def scheme_eval(expr, env, _=None):
    """Evaluates Scheme expression `expr` in frame `env`. The optional third
    argument here is ignored (scheme_eval will be overloaded later for tail
    call optimization).

    >>> env = setup_environment()
    >>> scheme_eval(parser.parse(iter([tokenizer.tokenize("(+ 1 2)")])), env)
    3
    """
    # Evaluate literals
    if is_self_evaluating(expr):
        return expr
    # Evaluate variables
    elif is_scheme_variable(expr):
        return env.lookup_variable_value(expr)

    # All valid non-atomic expressions are lists (combinations)
    if not isinstance(expr, Pair):
        raise SchemeError(
            'Unknown expression type: {0}'.format(repl_str(expr)))
    first, rest = expr.first, expr.rest
    # Evaluate special forms
    if is_scheme_symbol(first) and first in SPECIAL_FORMS:
        return SPECIAL_FORMS[first](rest, env)
    # Evaluate an application
    else:
        operator = scheme_eval(first, env)
        # Check if the operator is a macro
        if isinstance(operator, MacroProcedure):
            return scheme_eval(complete_apply(operator, rest, env), env)
        operands = rest.map(lambda x: scheme_eval(x, env))
        return scheme_apply(operator, operands, env)


@primitive("apply", use_env=True)
def scheme_apply(procedure, arguments, env):
    """Applies Scheme procedure to arguments (a Scheme list) in the current
    environment `env`.
    """
    validate_procedure(procedure)
    if is_primitive_procedure(procedure):
        return procedure.apply(arguments, env)
    elif is_compound_procedure(procedure):
        new_env = procedure.make_call_frame(arguments, env)
        # Note that `tail` is set to True when `eval_sequence()` is called here
        return eval_sequence(procedure.body, new_env, tail=True)
    else:
        raise SchemeError(
            'Unknown procedure type: {0}'.format(repl_str(procedure)))


##############################
#        Special Forms       #
##############################

# Each of the following `eval_xxx()` functions takes the cdr of a special form
# as its first argument---a Scheme list representing a special form WITHOUT the
# initial identifying symbol ("if", "lambda", "quote", ...). Its second
# argument is the environment in which the special form is to be evaluated.

# Abount special forms in scheme, You can refer to:
# https://groups.csail.mit.edu/mac/ftpdir/scheme-7.4/doc-html/scheme_3.html

# Conditionals


def eval_if(expr, env, tail=True):
    """Evaluates an if form.

    >>> env = setup_environment()
    >>> eval_if(parser.parse(iter([tokenizer.tokenize("(#t (print 2) (print 3 \
    ... ))")])), env, tail=False)
    2
    >>> eval_if(parser.parse(iter([tokenizer.tokenize("(#f (print 2) (print 3 \
    ... ))")])), env, tail=False)
    3
    >>> eval_if(parser.parse(iter([tokenizer.tokenize("(#f (print 2) (print 3 \
    ... ))")])), env)
    Pair('print', Pair(3, nil))

    Note that `eval_if` can use tail call optimization.
    """
    validate_form(expr, min=2, max=3)

    if_predicate = expr.first
    if_predicate_val = scheme_eval(if_predicate, env)
    # All values in Scheme are true except `false` object,
    # that is why we need `is_scheme_true()`
    if is_scheme_true(if_predicate_val):
        # Note that for `if` caluse , it muse have consequnet,
        # so `if_consequent` can not be None (although it can be `nil`).
        # But for `cond` clause, `if_consequent` can be None.
        # For example,
        # scm> (if(= 1 1))
        # Error: too few operands in form
        # scm> (if(= 1 1) nil)
        # ()
        if_consequent = expr.rest.first
        if if_consequent is None:
            return if_predicate_val
        else:
            return scheme_eval(if_consequent, env, tail=tail)
    # Turn to alternative
    elif len(expr) == 3:
        if_alternative = expr.rest.rest.first
        return scheme_eval(if_alternative, env, tail=tail)
    # If there is no alternative, return False
    else:
        return False


def eval_cond(expr, env, tail=True):
    """Evaluates a cond form. The `cond_to_if` function here can transform the
    cond expression into an if expression, thereby simplifying the
    evaluation of the cond expression.

    >>> env = setup_environment()
    >>> eval_cond(parser.parse(iter([tokenizer.tokenize("((#f (print 2)) (#t \
    ... 3))")])), env)
    3

    Note that `eval_cond` can use tail call optimization.
    """
    def sequence_to_expr(seq):
        def make_begin(seq):
            return scheme_cons("begin", seq)

        if seq is nil:
            return seq
        elif seq.rest is nil:
            return seq.first
        else:
            return make_begin(seq)

    def cond_predicate(clause):
        return clause.first

    def cond_actions(clause):
        return clause.rest

    def make_if(predicate, consequent, alternative):
        return scheme_list("if", predicate, consequent, alternative)

    def cond_to_if(clauses):
        # return None means that interpreter does not print anything
        if clauses is nil:
            return None
        first = clauses.first
        rest = clauses.rest
        validate_form(first, min=1)
        if cond_predicate(first) == "else":
            if rest is nil:
                return sequence_to_expr(first.rest)
            else:
                raise SchemeError(
                    "ELSE clause isn't last: {0}".format(
                        repl_str(clauses)))
        else:
            if cond_actions(first) is nil:  # for example, (cond ((= 1 1)))
                # there is no consequent, we denote it as None
                # o distinguish it from nil
                if_consequent = None
            else:  # for example, (cond ((= 1 1) 2)) or (cond ((= 1 1) nil))
                # there is a consequent, including nil
                if_consequent = sequence_to_expr(first.rest)
            return make_if(cond_predicate(first), if_consequent, cond_to_if(
                rest))

    return scheme_eval(cond_to_if(expr), env, tail)


def eval_and(exprs, env, tail=True):
    """Evaluates a (short-circuited) and form.

    >>> env = setup_environment()
    >>> eval_and(parser.parse(iter([tokenizer.tokenize("(#f (print 1))")])), \
    ... env)
    False
    >>> eval_and(parser.parse(iter([tokenizer.tokenize("((print 1) (print 2) \
    ... (print 3) (print 4) 3 #f)")])), env)
    1
    2
    3
    4
    False

    Note that `eval_and` can use tail call optimization.
    """
    # If there is no expression to be evaluated, return True
    if exprs is nil:
        return True
    # If the last expression is reached (indicating that the values of the
    # previous expressions are all true), then the evaluation result is
    # returned directly
    elif exprs.rest is nil:
        return scheme_eval(exprs.first, env, tail=tail)

    value = scheme_eval(exprs.first, env)
    # If an expression evaluates to False, return False,
    # and the remaining expressions are not evaluated
    if is_scheme_false(value):
        return False
    else:
        # If an expression evaluates to True, go on,
        return eval_and(exprs.rest, env)


def eval_or(exprs, env, tail=True):
    """Evaluates a (short-circuited) or form.

    >>> env = setup_environment()
    >>> eval_or(parser.parse(iter([tokenizer.tokenize("(10 (print 1))")])), \
    ... env)
    10
    >>> eval_or(parser.parse(iter([tokenizer.tokenize("(#f 2 3 #t #f)")])), \
    ... env)
    2
    >>> eval_or(parser.parse(iter([tokenizer.tokenize("((begin (print 1) #f) \
    ... (begin (print 2) #f) 6 (begin (print 3) 7))")])), env)
    1
    2
    6
    """
    # If there is no expression to be evaluated, return True
    if exprs is nil:
        return False
    # If the last expression is reached (indicating that the values of the
    # previous expressions are all False), then the evaluation result is
    # returned directly
    elif exprs.rest is nil:
        return scheme_eval(exprs.first, env, tail=tail)

    value = scheme_eval(exprs.first, env)
    # If an expression evaluates to True, return value, and the remaining
    # expressions are not evaluated
    if is_scheme_true(value):
        return value
    else:
        return eval_or(exprs.rest, env)


# Sequencing


def eval_sequence(exprs, env, tail=False):
    """Evaluates each expression in the Scheme list `exprs` in the current
    environment `env` and return the value of the last.

    >>> env = setup_environment()
    >>> eval_sequence(parser.parse(iter([tokenizer.tokenize("(1)")])), env)
    1
    >>> eval_sequence(parser.parse(iter([tokenizer.tokenize("(1 2)")])), env)
    2
    >>> eval_sequence(parser.parse(iter([tokenizer.tokenize("((print 1) 2)")] \
    ... )), env)
    1
    2
    >>> eval_sequence(parser.parse(iter([tokenizer.tokenize("((define x 2) x) \
    ... ")])), env)
    2

    `eval_begin` is defined based on `eval_sequence`. Note that \
        `eval_sequence` can use tail call optimization.
    """

    if not isinstance(exprs, Pair):
        return
    # If `exprs` is the last expression
    if exprs.rest is nil:
        # The value of the last expression is returned as the value of the
        # entire `begin` special form(or the body of a procedure)
        return scheme_eval(exprs.first, env, tail)
    else:
        # Evaluate the expressions <expr 1>, <expr 2>, ..., <expr k> in order
        scheme_eval(exprs.first, env)
        return eval_sequence(exprs.rest, env, tail)


def eval_begin(exprs, env, tail=True):
    """Evaluates a begin form. `eval_begin` behaves the same as `eval_sequence
    (and it is also defined based on `eval_sequence`). Note that `eval_begin`
    also can use tail call optimization.
    """
    validate_form(exprs, min=1)
    return eval_sequence(exprs, env, tail)


def eval_let(exprs, env, tail=True):
    """Evaluates a let form.

    >>> env = setup_environment()
    >>> eval_let(parser.parse(iter([tokenizer.tokenize("(((x 2) (y 3)) (+ x y \
    ... ))")])), env, tail=False)
    5
    >>> eval_let(parser.parse(iter([tokenizer.tokenize("(((x 2) (y 3)) (+ x y \
    ... ))")])), env)
    Pair('+', Pair('x', Pair('y', nil)))

    `eval_let` is defined based on `eval_sequence`. Note that `eval_let` can
    use tail call optimization.
    """
    validate_form(exprs, min=2)
    let_env = make_let_frame(exprs.first, env)
    return eval_sequence(exprs.rest, let_env, tail=tail)


# Assignments


def eval_assignment(expr, env):
    """Evaluates a set! form.

    >>> env = setup_environment()
    >>> parameters, expressions = scheme_list("x"), scheme_list("1")
    >>> new_env = env.extend_environment(parameters, expressions)
    >>> eval_assignment(parser.parse(iter([tokenizer.tokenize("(x 3)")])), \
    ... new_env)
    >>> env.frames.first.bindings
    {'x': 3}
    """
    def assignment_variable(expr):
        return expr.first

    def assignment_value(expr):
        return expr.rest.first

    env.set_variable_value(assignment_variable(
        expr), scheme_eval(assignment_value(expr), env))

# Definitions


def eval_definition(expr, env):
    """Evaluates a define form.

    >>> env = setup_environment()
    >>> eval_definition(parser.parse(iter([tokenizer.tokenize("(x 2)")])), env)
    'x'
    >>> scheme_eval("x", env)
    2
    >>> eval_definition(parser.parse(iter([tokenizer.tokenize("(x (+ 2 8))")] \
    ... )), env)
    'x'
    >>> scheme_eval("x", env)
    10
    >>> env = setup_environment()
    >>> eval_definition(parser.parse(iter([tokenizer.tokenize("((f x) (+ x 2) \
    ... )")])), env)
    'f'
    >>> scheme_eval(parser.parse(iter([tokenizer.tokenize("(f 3)")])), env)
    5
    """
    def definition_varaible(expr):
        target = expr.first
        # For the case of (define <var> <value>)
        if is_scheme_symbol(target):
            #  `(define x)` or `(define x 2 y 4)` is invalid
            validate_form(expr, min=2, max=2)
            return target
        # For the case of (define (<var> <param 1>, ..., <param n>) <body>)
        elif isinstance(target, Pair) and is_scheme_symbol(target.first):
            return target.first
        else:
            bad_target = target.first if isinstance(target, Pair) else target
            raise SchemeError("non-symbol: {0}".format(bad_target))

    def definition_value(expr):
        target = expr.first
        # For the case of (define <var> <value>)
        if is_scheme_symbol(target):
            return expr.rest.first
        # For the case of (define (<var> <param 1>, ..., <param n>) <body>)
        elif isinstance(target, Pair) and is_scheme_symbol(target.first):
            # Note: The validation of the lambda special form is turned over
            # to `scheme_eval()`
            return make_lambda(target.rest, expr.rest)
        else:
            bad_target = target.first if isinstance(target, Pair) else target
            raise SchemeError("non-symbol: {0}".format(bad_target))

    # Check that expressions is a list of length at least 2
    validate_form(expr, min=2)

    var = definition_varaible(expr)
    val = definition_value(expr)
    env.define_variable(var,
                        scheme_eval(val, env))

    return var

# Lambda expressions


def eval_lambda(expr, env):
    """Evaluatse a lambda form.

    >>> env = setup_environment()
    >>> eval_lambda(parser.parse(iter([tokenizer.tokenize("((x) (+ x 2))")])) \
    ... , env)
    LambdaProcedure(Pair('x', nil), Pair(Pair('+', Pair('x', Pair(2, nil))),
    nil), {Global Frame})
    """
    validate_form(expr, min=2)
    parameters = expr.first
    validate_parameters(parameters)
    body = expr.rest
    return LambdaProcedure(parameters, body, env)


# Quoting


def eval_quote(expr, env):
    """Evaluates a quote form.

    >>> env = setup_environment()
    >>> eval_quote(parser.parse(iter([tokenizer.tokenize("((+ x 2))")])), env)
    Pair('+', Pair('x', Pair(2, nil)))

    Note that the current environment `env` is not used.
    """
    validate_form(expr, min=1, max=1)
    return expr.first


def eval_quasiquote(expr, env):
    """Evaluates a quasiquote form with arguments `expr` in the current
    environment `env`.

    About quasiquote, you can refer to:
    https://courses.cs.washington.edu/courses/cse341/04wi/lectures/14-scheme-quote.html
    """
    def quasiquote_item(val, env, depth):
        """Evaluate Scheme expression `val` that is nested at depth `level` in
        a quasiquote form in frame `env`."""
        if not is_scheme_pair(val):
            return val

        # When encountering `unquote`, we decrease the depth by 1.
        # If the depth is 0, we evaluate the rest expressions.
        if val.first == 'unquote':
            depth -= 1
            if depth == 0:
                expr = val.rest
                validate_form(expr, 1, 1)
                return scheme_eval(expr.first, env)
        elif val.first == 'quasiquote':
            # Leave the item unevaluated
            depth += 1

        # Recursively quasiquote the items of the list
        return val.map(lambda elem: quasiquote_item(elem, env, depth))

    validate_form(expr, min=1, max=1)
    # Note that when call `quasiquote_item`, we have encountered
    # the first quasiquote, so depth=1
    return quasiquote_item(expr.first, env, depth=1)


def eval_unquote(expr, env):
    raise SchemeError('unquote outside of quasiquote')


##############################
#  Representing Expressions  #
##############################


def is_self_evaluating(expr):
    """Returns whether `expr` evaluates to itself, i.e. whether `expr` is a
    literal.
    """
    return is_scheme_boolean(expr) or is_scheme_number(expr) or \
        is_scheme_null(expr) or is_scheme_string(expr) or expr is None


def is_scheme_variable(x):
    return is_scheme_symbol(x)


def make_lambda(parameters, body):
    return scheme_cons("lambda", scheme_cons(parameters, body))


def make_let_frame(bindings, env):
    """Create a new environment with a new frame that contains the definitions
    given in `bindings`. The Scheme list `bindings` must have the form of a
    proper bindings list in a let expression: each item must be a list
    containing a symbol and a Scheme expression.
    """
    def bindings_items(bindings, env):
        if bindings is nil:
            return nil, nil
        binding = bindings.first
        validate_form(binding, min=2, max=2)
        var = binding.first
        val = scheme_eval(binding.rest.first, env)
        vars, vals = bindings_items(bindings.rest, env)
        return scheme_cons(var, vars), scheme_cons(val, vals)

    if not is_scheme_list(bindings):
        raise SchemeError('bad bindings list in let form')

    vars, vals = bindings_items(bindings, env)
    validate_parameters(vars)
    return env.extend_environment(vars, vals)


##############################
#       Dynamic scoping      #
##############################


def eval_dlambda_form(expr, env):
    """Evaluate a dlambda form."""
    validate_form(expr, min=2)
    parameters = expr.first
    validate_parameters(parameters)
    return DLambdaProcedure(parameters, expr.rest)

##############################
#            Macro           #
##############################


def eval_macro_definition(expr, env):
    """Evaluate a define-macro form.

    >>> env = setup_environment()
    >>> eval_macro_definition(parser.parse(iter([tokenizer.tokenize("((f x) ( \
    ... car x))")])), env)
    'f'
    >>> scheme_eval(parser.parse(iter([tokenizer.tokenize("(f (1 2))")])), env)
    1

    About macro, you can refer to:
    https://liujiacai.net/blog/2017/08/31/master-macro-theory/  
    """
    validate_form(expr, min=2)
    target = expr.first
    if isinstance(target, Pair) and is_scheme_symbol(target.first):
        func_name = target.first
        # `target.rest` is parameters，not `target.rest.first`
        parameters = target.rest
        body = expr.rest
        # Just store the expression, rather than evaluate it
        env.define_variable(func_name, MacroProcedure(parameters, body, env))
        return func_name
    else:
        raise SchemeError("Invalid use of macro")


##############################
#           Stream           #
##############################

def eval_delay(expr, env):
    """Evaluates a delay form."""
    validate_form(expr, 1, 1)
    return Promise(expr.first, env)


def eval_cons_stream(expr, env):
    """Evaluates a cons-stream form."""
    validate_form(expr, 2, 2)
    return Pair(scheme_eval(expr.first, env), Promise(expr.rest.first, env))


##############################
#   Tail Call Optimization   #
##############################


def complete_apply(procedure, args, env):
    """Apply procedure to args in env; ensure the result is not a Thunk."""
    val = scheme_apply(procedure, args, env)
    if isinstance(val, TailPromise):
        return scheme_eval(val.expr, val.env)
    else:
        return val


def optimize_tail_calls(original_scheme_eval):
    """Return a properly tail recursive version of an eval function.
    """
    def optimized_eval(expr, env, tail=False):
        """Evaluate Scheme expression `expr` in the current environment `env`.
        If `tail`, return a Promise containing an expression for further
        evaluation.
        """
        # If tail is True and not expression is not self-evaluated,
        # return Promise directly, this is because a call to
        # `original_scheme_eval` causes the recursion depth to increase by 1.
        # Note that for `optimized_eval`, argument `tail` defaults to False,
        # which means that it is impossible to return Promise at the first,
        # call, that is, when the recursion depth is 1
        if tail and not is_scheme_variable(expr) and not is_self_evaluating(
                expr):
            return TailPromise(expr, env)

        # If tail is False or the expression is not self-evaluated, it will be
        # evaluated until the actual value is obtained (instead of Promise)
        result = TailPromise(expr, env)
        while (isinstance(result, TailPromise)):
            result = original_scheme_eval(result.expr, result.env)
        return result

    return optimized_eval


# Uncomment the following line to apply tail call optimization
scheme_eval = optimize_tail_calls(scheme_eval)


##############################
# Dispatch for special forms #
##############################


SPECIAL_FORMS = {
    # Conditionals
    "if": eval_if,
    "cond": eval_cond,
    "and": eval_and,
    "or": eval_or,
    # Sequencing
    "begin": eval_begin,
    "let": eval_let,
    # Assignments
    "set!": eval_assignment,
    # Definitions
    "define": eval_definition,
    # Lambda expressions
    "lambda": eval_lambda,
    # Quoting
    "quote": eval_quote,
    "unquote": eval_unquote,
    "quasiquote": eval_quasiquote,
    # Dynamic scoping
    "dlambda": eval_dlambda_form,
    # Macro
    "define-macro": eval_macro_definition,
    # Stream
    "delay": eval_delay,
    "cons-stream": eval_cons_stream
}
