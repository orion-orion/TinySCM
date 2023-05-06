# -*- coding: utf-8 -*-
"""This module implements the internal data structures of the Scheme
language.

In addition to the internal data stuctures defined in this file, some data
types in Scheme are represented by their corresponding type in Python:
    number:       int or float
    symbol:       string
    boolean:      bool
    unspecified:  None

The __repr__ method of a Scheme value will return a Python expression that
would be evaluated to the value, where possible.

The __str__ method of a Scheme value will return a Scheme expression that
would be read to the value, where possible.
"""


def repl_str(val):
    """Should largely match str(val), except for booleans and undefined."""
    if val is True:
        return "#t"
    if val is False:
        return "#f"
    if val is None:
        return "undefined"
    if isinstance(val, str) and val and val[0] == "\"":
        return "\"" + repr(val[1:-1])[1:-1] + "\""
    return str(val)


class Pair:
    """A pair has two instance attributes: first and rest. rest must be a Pair
    or nil

    >>> s = Pair(1, Pair(2, nil))
    >>> s
    Pair(1, Pair(2, nil))
    >>> print(s)
    (1 2)
    >>> print(s.map(lambda x: x+4))
    (5 6)
    """

    def __init__(self, first, rest):
        self.first = first
        self.rest = rest

    def __repr__(self):
        return "Pair({0}, {1})".format(repr(self.first), repr(self.rest))

    def __str__(self):
        s = "(" + repl_str(self.first)
        rest = self.rest
        while isinstance(rest, Pair):
            s += " " + repl_str(rest.first)
            rest = rest.rest
        if rest is not nil:
            s += " . " + repl_str(rest)
        return s + ")"

    def __len__(self):
        n, rest = 1, self.rest
        while isinstance(rest, Pair):
            n += 1
            rest = rest.rest
        # The tail of the list must be nil
        if rest is not nil:
            raise TypeError("length attempted on improper list")
        return n

    def __eq__(self, p):
        if not isinstance(p, Pair):
            return False
        return self.first == p.first and self.rest == p.rest

    def map(self, fn):
        """Return a Scheme list after mapping Python function `fn` to `self`.
        """
        mapped = fn(self.first)
        if self.rest is nil or isinstance(self.rest, Pair):
            return Pair(mapped, self.rest.map(fn))
        else:
            raise TypeError("ill-formed list (cdr is a promise)")

    def flatmap(self, fn):
        """Return a Scheme list after flatmapping Python function `fn` to
        `self`."""
        from primitive_procs import scheme_append
        mapped = fn(self.first)
        if self.rest is nil or isinstance(self.rest, Pair):
            return scheme_append(mapped, self.rest.flatmap(fn))
        else:
            raise TypeError("ill-formed list (cdr is a promise)")


class nil:
    """The empty list"""

    def __repr__(self):
        return "nil"

    def __str__(self):
        return "()"

    def __len__(self):
        return 0

    def map(self, fn):
        return self

    def flatmap(self, fn):
        return self


# Assignment hides the nil class; there is only one instance, so when we check
# whether the object is nil later, we always use the `is null` syntax
nil = nil()


class Frame:
    """An frame binds Scheme symbols to Scheme values."""

    def __init__(self):
        self.bindings = {}

    def add_binding(self, var, val):
        self.bindings[var] = val

    def __repr__(self):
        s = sorted(["{0}: {1}".format(k, v)
                   for k, v in self.bindings.items()])
        return "{" + ", ".join(s) + "}"


class Environment:
    """An environment is a list of frames."""
    import primitive_procs as pprocs

    def __init__(self):
        """An environment is initialized as a list containing a empty frame."""
        self.frames = self.pprocs.scheme_list(Frame())

    def __repr__(self):
        def env_loop_repr(frames):
            # If there is no enclosing environment
            if self.pprocs.is_scheme_null(frames.rest):
                return "{Global Frame}"
            else:
                frame = frames.first
                return repr(frame) + " -> " + env_loop_repr(frames.rest)
        return env_loop_repr(self.frames)

    def define_variable(self, var, val):
        """Define Scheme variable to have value."""
        frame = self.frames.first
        frame.add_binding(var, val)

    def lookup_variable_value(self, var):
        """Return the value bound to variable. Errors if variable is not
        found."""
        def env_loop(frames):
            # If cannot find the variable in the current environment
            if self.pprocs.is_scheme_null(frames):
                raise self.pprocs.SchemeError(
                    "Unbound variable: {0}".format(var))
            frame = frames.first
            if var in frame.bindings.keys():
                return frame.bindings[var]
            else:
                return env_loop(frames.rest)
        return env_loop(self.frames)

    @ staticmethod
    def make_frame(vars, vals):
        """Return a new frame containing the bindings of the variables and
        values."""
        frame = Frame()
        while isinstance(vars, Pair):
            var = vars.first
            val = vals.first
            frame.add_binding(var, val)
            vars = vars.rest
            vals = vals.rest
        return frame

    def extend_environment(self, vars, vals):
        """Return a new environment containing a new frame, in which the
        symbols in a Scheme list `vars` of formal parameters parameters are
        bounded to the Scheme values in the Scheme list `vals`. Both
        parameters and `vals` are represented as Pairs. Raise an error if too
        many or too few vals are given.
        >>> from tiny_scm import setup_environment
        >>> from primitive_procs import scheme_list
        >>> env = setup_environment()
        >>> parameters, expressions = scheme_list("a", "b", "c"), \
                                      scheme_list(1, 2, 3)
        >>> env.extend_environment(parameters, expressions)
        {a: 1, b: 2, c: 3} -> {Global Frame}
        """
        new_env = Environment()
        if len(vars) == len(vals):
            new_env.frames = self.pprocs.scheme_cons(
                self.make_frame(vars, vals),
                self.frames)
        elif len(vars) < len(vals):
            raise self.pprocs.SchemeError(
                "Too many arguemtns supplied")
        else:
            raise self.pprocs.SchemeError(
                "Too few arguemtns supplied")
        return new_env


##############
# Procedures #
##############


class Procedure:
    """The supertype of all Scheme procedures."""


class PrimitiveProcedure(Procedure):
    """A Scheme procedure defined as a Python function."""
    import primitive_procs as pprocs

    def __init__(self, fn, name='primitive', use_env=False):
        self.name = name
        self.fn = fn
        self.use_env = use_env

    def __str__(self):
        return '#[{0}]'.format(self.name)

    def apply(self, arguments, env):
        """Apply `self` to `args` in Frame `env`, where `args` is a Scheme
        list (a Pair instance).
        >>> from tiny_scm import setup_environment
        >>> from internal_ds import Pair, nil
        >>> env =  setup_environment()
        >>> plus = env.frames.first.bindings['+']
        >>> twos = Pair(2, Pair(2, nil))
        >>> plus.apply(twos, env)
        4
        """
        if not self.pprocs.is_scheme_list(arguments):
            raise self.pprocs.SchemeError(
                'arguments are not in a list: {0}'.format(arguments))

        # Convert a Scheme list to a Python list
        arguments_list = self.flatten(arguments)
        try:
            if self.use_env:
                return self.fn(*arguments_list, env)
            return self.fn(*arguments_list)
        except TypeError:
            raise self.pprocs.SchemeError(
                'incorrect number of arguments: {0}'.format(self))

    def flatten(self, arguments):
        if arguments is nil:
            return []
        else:
            return [arguments.first] + self.flatten(arguments.rest)
