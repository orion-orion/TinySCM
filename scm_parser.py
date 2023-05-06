# -*- coding: utf-8 -*-
"""The `Parser` class provides method `parse` for converting tokens of a
complete expression(single-line or multi-line) into abstract syntax tree.
"""
from internal_ds import Pair, nil


class Parser:
    _SINGLE_CHAR_TOKENS = set("()[]'`")
    DELIMITERS = _SINGLE_CHAR_TOKENS | {".", ",", ",@"}

    def __init__(self):
        # `current_line` containing tokens of the currently parsed line
        self.current_line = []

    def read_line(self, lines_stream):
        try:
            self.current_line = next(lines_stream)
        except StopIteration:
            self.current_line = []

    def read_until_not_empty(self):
        while self.is_empty():
            self.read_line(self.lines_stream)

    def is_empty(self):
        # current_line里的token消化完了，说明需要出现scm>提示，从input中读了
        return not self.current_line

    def parse(self, lines_stream):
        """Parse a complete expression(single-line or multi-line) from
        `lines_stream`, a generator of lines.

        >>> from scm_tokenizer import Tokenizer
        >>> from scm_parser import Parser
        >>> tokenizer = Tokenizer()
        >>> parser = Parser()
        >>> parser.parse(iter([tokenizer.tokenize("nil")]))
        nil
        >>> parser.parse(iter([tokenizer.tokenize("1")]))
        1
        >>> parser.parse(iter([tokenizer.tokenize("true")]))
        True
        >>> parser.parse(iter([tokenizer.tokenize("(+ 1 2)")]))
        Pair('+', Pair(1, Pair(2, nil)))
        """
        self.lines_stream = lines_stream
        return self.expr()

    def expr(self):
        """Returns the parsing result of the next complete expression (single-
        line or multi-lines)
        """
        self.read_until_not_empty()

        tok = self.current_line.pop(0)
        if tok is None:
            raise EOFError
        # If the current token is the string "nil", return the nil object.
        elif tok == "nil":
            return nil
        # If the current token is "(", the expression is a list or pair. Call
        # "rest_expr()" and return its result.
        elif tok == "(":
            return self.rest_list()
        # If the current token is "'", the expression should be processed as a
        # quote expression.
        elif tok == "'":
            # We must use Pair(<expr>, nil) to wrap the quoted expression
            # (variable or list)
            return Pair("quote", Pair(self.expr(), nil))
        # If the next token is not a delimiter, then it must be a primitive
        # expression (i.e. a number, boolean). Return it.
        elif tok not in self.DELIMITERS:
            return tok
        # If none of the above cases apply, raise an error.
        else:
            raise SyntaxError("unexpected token: {0}".format(tok))

    def rest_list(self):
        """Returns the parsing result of the rest of a list or pair, starting
        before an element or ")".
        """
        try:
            self.read_until_not_empty()

            tok = self.current_line[0]
            # If there are no more tokens, then the list is missing a close
            # parenthesis and we should raise an error.
            if tok is None:
                raise SyntaxError("unexpected end of file")
            # If the token is ")", then we have reached the end of the list or
            # pair. Remove this token from the current line and return the nil
            # object.
            elif tok == ")":
                self.current_line.pop(0)
                return nil
            elif tok == ".":
                self.current_line.pop(0)
                expr = self.expr()

                self.read_until_not_empty()

                tok = self.current_line.pop(0)
                if tok is None:
                    raise SyntaxError("unexpected end of file")
                elif tok != ")":
                    raise SyntaxError("expected one element after .")
                return expr
            # If none of the above cases apply, the next token is the operator
            # in a combination(combinations includes call expressions and
            # special forms). For example, the input lines could contain ["+",
            # 2, 3, ")"]. To parse this:
            else:
                # `expr()` read the next complete expression in the input
                # lines.
                first = self.expr()
                # Call `rest_list()` to read the rest of the combination until
                # the matching closing parenthesis.
                rest = self.rest_list()

                # Return the results as a Pair instance, where the first
                # element is the next complete expression from (1) and the
                # second element is the rest of the combination from (2).
                # for ["+", 2, 3, ")"], return Pair('+', Pair(2, Pair(3, nil)))
                return Pair(first, rest)
        except EOFError:
            raise SyntaxError("unexpected end of file")
