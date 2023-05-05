# -*- coding: utf-8 -*-
"""The tokenizer class provides method tokenize for converting a string into
a list of tokens. A token may be:

  * A number (represented as an int or float)
  * A boolean (represented as a bool)
  * A symbol (represented as a string)
  * A delimiter, including parentheses, dots, and single quotes

This file also includes some features of Scheme that have not been addressed
in the course, such as Scheme strings.
"""


class Tokenizer:

    _NUMERAL_STARTS = set("0123456789") | set("+-.")
    _SYMBOL_CHARS = (set("!$%&*/:<=>?@^_~") | set("abcdefghijklmnopqrstuvwxyz")
                     | set("ABCDEFGHIJKLMNOPQRSTUVWXYZ") | _NUMERAL_STARTS)
    _STRING_DELIMS = set("\"")
    _WHITESPACE = set(" \t\n\r")
    _SINGLE_CHAR_TOKENS = set("()[]'`")
    _TOKEN_END = _WHITESPACE | _SINGLE_CHAR_TOKENS | _STRING_DELIMS | {
        ",", ",@"}
    DELIMITERS = _SINGLE_CHAR_TOKENS | {".", ",", ",@"}
    _MAX_TOKEN_LENGTH = 50

    def tokenize(self, line: str):
        """The list of Scheme tokens on line.  Excludes comments and
        whitespace."""
        result = []
        text, i = self.next_candidate_token(line, 0)
        while text is not None:
            if text in self.DELIMITERS:
                result.append(text)
            elif text == "#t" or text.lower() == "true":
                result.append(True)
            elif text == "#f" or text.lower() == "false":
                result.append(False)
            elif text == "nil":
                result.append(text)
            elif text[0] in self._SYMBOL_CHARS:
                number = False
                if text[0] in self._NUMERAL_STARTS:
                    try:
                        result.append(int(text))
                        number = True
                    except ValueError:
                        try:
                            result.append(float(text))
                            number = True
                        except ValueError:
                            pass
                if not number:
                    if self.valid_symbol(text):
                        result.append(text.lower())
                    else:
                        raise ValueError(
                            "invalid numeral or symbol: {0}".format(text))
            elif text[0] in self._STRING_DELIMS:
                result.append(text)
            else:
                error_message = [
                    "warning: invalid token: {0}".format(text),
                    " " * 4 + line,
                    " " * (i + 4) + "^"
                ]
                raise ValueError("\n".join(error_message))
            text, i = self.next_candidate_token(line, i)
        return result

    def valid_symbol(self, s):
        """Returns whether s is a well-formed symbol."""
        if len(s) == 0:
            return False
        for c in s:
            if c not in self._SYMBOL_CHARS:
                return False
        return True

    def next_candidate_token(self, line, k):
        """A tuple (tok, k'), where tok is the next substring of line at or
        after position k that could be a token (assuming it passes a validity
        check), and k' is the position in line following that token.  Returns
        (None, len(line)) when there are no more tokens."""
        while k < len(line):
            c = line[k]
            if c == ";":
                return None, len(line)
            elif c in self._WHITESPACE:
                k += 1
            elif c in self._SINGLE_CHAR_TOKENS:
                if c == "]":
                    c = ")"
                if c == "[":
                    c = "("
                return c, k+1
            elif c == "#":  # Boolean values #t and #f
                return line[k:k+2], min(k+2, len(line))
            elif c == ",":  # Unquote; check for @
                if k+1 < len(line) and line[k+1] == "@":
                    return ",@", k+2
                return c, k+1
            elif c in self._STRING_DELIMS:
                # No triple quotes in Scheme
                if k+1 < len(line) and line[k+1] == c:
                    return c+c, k+2
                s = ""
                k += 1
                while k < len(line):
                    c = line[k]
                    if c == "\"":
                        self.check_token_length_warning(s, len(s) + 2)
                        return "\"" + s + "\"", k+1
                    elif c == "\\":
                        if k + 1 == len(line):
                            raise SyntaxError("String ended abruptly")
                        next = line[k + 1]
                        if next == "n":
                            s += "\n"
                        else:
                            s += next
                        k += 2
                    else:
                        s += c
                        k += 1
                raise SyntaxError("String ended abruptly")
            else:
                j = k
                while j < len(line) and line[j] not in self._TOKEN_END:
                    j += 1
                self.check_token_length_warning(
                    line[k:j], min(j, len(line)) - k)
                return line[k:j], min(j, len(line))
        return None, len(line)

    def check_token_length_warning(self, token, length):
        if length > self._MAX_TOKEN_LENGTH:
            import warnings
            warnings.warn("Token {} has exceeded the maximum token length {}".
                          format(token, self._MAX_TOKEN_LENGTH))
