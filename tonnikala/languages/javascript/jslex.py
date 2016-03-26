# -*- coding: utf8 -*-
from __future__ import absolute_import, division, print_function, \
    unicode_literals

"""JsLex: a lexer for Javascript"""
# From https://bitbucket.org/ned/jslex

import re


class Tok(object):
    """A specification for a token class."""

    num = 0

    def __init__(self, name, regex, next=None):
        self.id = Tok.num
        Tok.num += 1
        self.name = name
        self.regex = regex
        self.next = next


def literals(choices, prefix="", suffix=""):
    """Create a regex from a space-separated list of literal `choices`.

    If provided, `prefix` and `suffix` will be attached to each choice
    individually.

    """
    return "|".join(prefix + re.escape(c) + suffix for c in choices.split())


class Lexer(object):
    """A generic multi-state regex-based lexer."""

    def __init__(self, states, first):
        self.regexes = {}
        self.toks = {}

        for state, rules in states.items():
            parts = []
            for tok in rules:
                groupid = "t%d" % tok.id
                self.toks[groupid] = tok
                parts.append("(?P<%s>%s)" % (groupid, tok.regex))
            self.regexes[state] = re.compile("|".join(parts),
                                             re.MULTILINE | re.VERBOSE)

        self.state = first

    def lex(self, text, start=0):
        """Lexically analyze `text`.

        Yields pairs (`name`, `tokentext`).

        """
        max = len(text)
        eaten = start
        s = self.state
        r = self.regexes
        toks = self.toks
        while eaten < max:
            for match in r[s].finditer(text, eaten):
                name = match.lastgroup
                tok = toks[name]
                toktext = match.group(name)
                eaten += len(toktext)
                yield (tok.name, toktext)

                if tok.next:
                    s = tok.next
                    break

        self.state = s


class JsLexer(Lexer):
    """A Javascript lexer

    >>> lexer = JsLexer()
    >>> list(lexer.lex("a = 1"))
    [("id", "a"), ("ws", " "), ("punct", "="), ("ws", " "), ("dnum", "1")]

    This doesn't properly handle non-Ascii characters in the Javascript source.

    """

    # Because these tokens are matched as alternatives in a regex, longer
    # possibilities
    # must appear in the list before shorter ones, for example, '>>' before '>'.
    #
    # Note that we don't have to detect malformed Javascript, only properly lex
    # correct Javascript, so much of this is simplified.

    # Details of Javascript lexical structure are taken from
    # http://www.ecma-international.org/publications/files/ECMA-ST/ECMA-262.pdf

    # A useful explanation of automatic semicolon insertion is at
    # http://inimino.org/~inimino/blog/javascript_semicolons

    both_before = [
        Tok("comment", r"/\*(.|\n)*?\*/"),
        Tok("linecomment", r"//.*?$"),
        Tok("ws", r"\s+"),
        Tok("keyword", literals("""
                                break case catch class const continue debugger
                                default delete do else enum export extends
                                finally for function if import in instanceof new
                                return super switch this throw try typeof var
                                void while with
                                """, suffix=r"\b"), next='reg'),
        Tok("reserved", literals("null true false", suffix=r"\b"), next='div'),
        Tok("id", r"""
                            ([a-zA-Z_$   ]|\\u[0-9a-fA-Z]{4})       # first char
                            ([a-zA-Z_$0-9]|\\u[0-9a-fA-F]{4})*      # rest chars
                            """, next='div'),
        Tok("hnum", r"0[xX][0-9a-fA-F]+", next='div'),
        Tok("onum", r"0[0-7]+"),
        Tok("dnum", r"""
                            (   (0|[1-9][0-9]*)         # DecimalIntegerLiteral
                                \.                      # dot
                                [0-9]*                  # DecimalDigits-opt
                                ([eE][-+]?[0-9]+)?      # ExponentPart-opt
                            |
                                \.                      # dot
                                [0-9]+                  # DecimalDigits
                                ([eE][-+]?[0-9]+)?      # ExponentPart-opt
                            |
                                (0|[1-9][0-9]*)         # DecimalIntegerLiteral
                                ([eE][-+]?[0-9]+)?      # ExponentPart-opt
                            )
                            """, next='div'),
        Tok("punct", literals("""
                                >>>= === !== >>> <<= >>= <= >= == != << >> &&
                                || += -= *= %= &= |= ^=
                                """), next="reg"),
        Tok("punct", literals("++ -- ) ]"), next='div'),
        Tok("punct", literals("{ } ( [ . ; , < > + - * % & | ^ ! ~ ? : ="),
            next='reg'),
        Tok("string", r'"([^"\\]|(\\(.|\n)))*?"', next='div'),
        Tok("string", r"'([^'\\]|(\\(.|\n)))*?'", next='div'),
    ]

    both_after = [
        Tok("other", r"."),
    ]

    states = {
        'div':  # slash will mean division
            both_before + [
                Tok("punct", literals("/= /"), next='reg'),
            ] + both_after,

        'reg':  # slash will mean regex
            both_before + [
                Tok("regex",
                    r"""
                        /                       # opening slash
                        # First character is..
                        (   [^*\\/[]            # anything but * \ / or [
                        |   \\.                 # or an escape sequence
                        |   \[                  # or a class, which has
                                (   [^\]\\]     #   anything but \ or ]
                                |   \\.         #   or an escape sequence
                                )*              #   many times
                            \]
                        )
                        # Following characters are same, except for excluding
                        # a star
                        (   [^\\/[]             # anything but \ / or [
                        |   \\.                 # or an escape sequence
                        |   \[                  # or a class, which has
                                (   [^\]\\]     #   anything but \ or ]
                                |   \\.         #   or an escape sequence
                                )*              #   many times
                            \]
                        )*                      # many times
                        /                       # closing slash
                        [a-zA-Z0-9]*            # trailing flags
                    """, next='div'),
            ] + both_after,
    }

    def __init__(self):
        super(JsLexer, self).__init__(self.states, 'reg')
