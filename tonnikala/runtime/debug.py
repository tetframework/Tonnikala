"""
tonnikala.runtime.debug
~~~~~~~~~~~~~~~~~~~~~~~

Implements the debug interface for Tonnikala. This module does some pretty
ugly stuff with the Python traceback system in order to achieve tracebacks
with correct line numbers, locals and contents.

Based on Jinja2 module `jinja2.debug`, original code is

:copyright: (c) 2010 by the Jinja Team.

Copyright 2007 Pallets

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice, this
list of conditions and the following disclaimer.

Redistributions in binary form must reproduce the above copyright notice,
this list of conditions and the following disclaimer in the documentation
and/or other materials provided with the distribution.

Neither the name of the copyright holder nor the names of its contributors
may be used to endorse or promote products derived from this software without
specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
THE POSSIBILITY OF SUCH DAMAGE.
"""

import sys
import traceback

from types import TracebackType, CodeType

from .exceptions import TemplateSyntaxError
from ..helpers import internal_code, reraise


# on pypy we can take advantage of transparent proxies
try:
    from __pypy__ import tproxy
except ImportError:
    tproxy = None


# how does the raise helper look like?
try:
    exec("raise TypeError, 'foo'")
except SyntaxError:  # pragma: python3
    raise_helper = (
        "__tonnikala_exception__[1].__traceback__ = None; raise "
        "__tonnikala_exception__[1]"
    )
except TypeError:  # pragma: python2
    raise_helper = "raise __tonnikala_exception__[0], " "__tonnikala_exception__[1]"


class TracebackFrameProxy(object):
    """Proxies a traceback frame."""

    def __init__(self, tb):
        self.tb = tb
        self._tb_next = None

    @property
    def tb_next(self):
        return self._tb_next

    def set_next(self, next):
        if tb_set_next is not None:
            try:
                tb_set_next(self.tb, next and next.tb or None)
            except Exception:
                # this function can fail due to all the hackery it does
                # on various python implementations.  We just catch errors
                # down and ignore them if necessary.
                pass

        self._tb_next = next

    @property
    def is_tonnikala_frame(self):
        return "__tonnikala_template__" in self.tb.tb_frame.f_globals

    def __getattr__(self, name):
        return getattr(self.tb, name)


def make_frame_proxy(frame):
    proxy = TracebackFrameProxy(frame)
    if tproxy is None:
        return proxy

    def operation_handler(operation, *args, **kwargs):
        if operation in ("__getattribute__", "__getattr__"):
            return getattr(proxy, args[0])
        elif operation == "__setattr__":
            proxy.__setattr__(*args, **kwargs)
        else:
            return getattr(proxy, operation)(*args, **kwargs)

    return tproxy(TracebackType, operation_handler)


class ProcessedTraceback(object):
    """Holds a Tonnikala preprocessed traceback for printing or reraising."""

    def __init__(self, exc_type, exc_value, frames):
        assert frames, "no frames for this traceback?"
        self.exc_type = exc_type
        self.exc_value = exc_value
        self.frames = frames

        # newly concatenate the frames (which are proxies)
        prev_tb = None
        for tb in self.frames:
            if prev_tb is not None:
                prev_tb.set_next(tb)
            prev_tb = tb
        prev_tb.set_next(None)

    def render_as_text(self, limit=None):
        """Return a string with the traceback."""
        lines = traceback.format_exception(
            self.exc_type, self.exc_value, self.frames[0], limit=limit
        )
        return "".join(lines).rstrip()

    def render_as_html(self, full=False):
        """Return a unicode string with the traceback as rendered HTML."""
        from jinja2.debugrenderer import render_traceback

        return u"%s\n\n<!--\n%s\n-->" % (
            render_traceback(self, full=full),
            self.render_as_text().decode("utf-8", "replace"),
        )

    @property
    def is_template_syntax_error(self):
        """`True` if this is a template syntax error."""
        return isinstance(self.exc_value, TemplateSyntaxError)

    @property
    def exc_info(self):
        """Exception info tuple with a proxy around the frame objects."""
        return self.exc_type, self.exc_value, self.frames[0]

    @property
    def standard_exc_info(self):
        """Standard python exc_info for re-raising"""
        tb = self.frames[0]
        # the frame will be an actual traceback (or transparent proxy) if
        # we are on pypy or a python implementation with support for tproxy
        if type(tb) is not TracebackType:
            tb = tb.tb
        return self.exc_type, self.exc_value, tb


def make_traceback(exc_info, source_hint=None):
    """Creates a processed traceback object from the exc_info."""
    exc_type, exc_value, tb = exc_info
    if isinstance(exc_value, TemplateSyntaxError):
        exc_info = translate_syntax_error(exc_value, source_hint)
        initial_skip = 0
    else:
        initial_skip = 1
    return translate_exception(exc_info, initial_skip)


def translate_syntax_error(error, source=None):
    """Rewrites a syntax error to please traceback systems."""
    error.source = source
    error.translated = True
    exc_info = (error.__class__, error, None)
    filename = error.filename
    if filename is None:
        filename = "<unknown>"
    return fake_exc_info(exc_info, filename, error.lineno)


def translate_exception(exc_info, initial_skip=0):
    """If passed an exc_info it will automatically rewrite the exceptions
    all the way down to the correct line numbers and frames.
    """
    tb = exc_info[2]
    frames = []

    # skip some internal frames if wanted
    for x in range(initial_skip):
        if tb is not None:
            tb = tb.tb_next
    initial_tb = tb

    while tb is not None:
        # skip frames decorated with @internalcode.  These are internal
        # calls we can't avoid and that are useless in template debugging
        # output.
        if tb.tb_frame.f_code in internal_code:
            tb = tb.tb_next
            continue

        # save a reference to the next frame if we override the current
        # one with a faked one.
        next = tb.tb_next

        # fake template exceptions
        template = tb.tb_frame.f_globals.get("__TK_template_info__")
        if template is not None:
            lineno = template.get_corresponding_lineno(tb.tb_lineno)
            tb = fake_exc_info(exc_info[:2] + (tb,), template.filename, lineno)[2]

        frames.append(make_frame_proxy(tb))
        tb = next

    # if we don't have any exceptions in the frames left, we have to
    # reraise it unchanged. XXX: can we backup here?  when could this happen?
    if not frames:
        reraise(exc_info[0], exc_info[1], exc_info[2])

    return ProcessedTraceback(exc_info[0], exc_info[1], frames)


if sys.version_info >= (3, 8):

    def code_with_custom_location(code, filename, location):
        return code.replace(co_filename=filename, co_name=location)


else:

    def code_with_custom_location(code, filename, location):
        return CodeType(
            code.co_argcount,
            code.co_kwonlyargcount,
            code.co_nlocals,
            code.co_stacksize,
            code.co_flags,
            code.co_code,
            code.co_consts,
            code.co_names,
            code.co_varnames,
            filename,
            location,
            code.co_firstlineno,
            code.co_lnotab,
            code.co_freevars,
            code.co_cellvars,
        )


def fake_exc_info(exc_info, filename, lineno):
    """Helper for `translate_exception`."""
    exc_type, exc_value, tb = exc_info

    # figure the real context out
    if tb is not None:
        # if there is a local called __tonnikala_exception__, we get
        # rid of it to not break the debug functionality.
        locals = tb.tb_frame.f_locals.copy()
        locals.pop("__tonnikala_exception__", None)
    else:
        locals = {}

    # assemble fake globals we need
    globals = {
        "__name__": filename,
        "__file__": filename,
        "__tonnikala_exception__": exc_info[:2],
        # we don't want to keep the reference to the template around
        # to not cause circular dependencies, but we mark it as Tonnikala
        # frame for the ProcessedTraceback
        "__TK_template_info__": None,
    }

    # and fake the exception
    lineno = lineno or 0
    code = compile("\n" * (lineno - 1) + raise_helper, filename, "exec")

    # if it's possible, change the name of the code.  This won't work
    # on some python environments such as google appengine
    try:
        if tb is None:
            location = "template"
        else:
            function = tb.tb_frame.f_code.co_name
            if function == "__main__":
                location = "top-level template code"
            elif function.startswith("__TK__block__"):
                location = 'block "%s"' % function[13:]
            elif function.startswith("__TK__typed__"):
                functype = function[13:].split("__")[0].replace("_", " ")
                location = functype
            elif function.startswith("__TK_"):
                location = "template"
            else:
                location = 'def "%s"' % function

        code = code_with_custom_location(code, filename, location)

    except Exception:
        pass

    # execute the code and catch the new traceback
    try:
        new_tb = None
        exec(code, globals, locals)
    except BaseException:
        exc_info = sys.exc_info()
        new_tb = exc_info[2].tb_next

    # return without this frame
    return exc_info[:2] + (new_tb,)


def _init_ugly_crap():
    """This function implements a few ugly things so that we can patch the
    traceback objects.  The function returned allows resetting `tb_next` on
    any python traceback object.  Do not attempt to use this on non cpython
    interpreters
    """
    import ctypes
    from types import TracebackType

    _Py_ssize_t = ctypes.c_ssize_t

    if hasattr(sys, "getobjects"):  # pragma: no cover
        # cannot support this, as don't have access to it
        raise Exception("traceback hacking not supported on tracing Python builds")

    # this isn't the full structure definition but we don't need the rest anyway,
    # these are enough here. All struct pointers being compatible we use a wrong
    # struct pointer for ob_type.
    class _Traceback(ctypes.Structure):
        pass

    _Traceback._fields_ = [
        ("ob_refcnt", _Py_ssize_t),
        ("ob_type", ctypes.POINTER(_Traceback)),
        ("tb_next", ctypes.POINTER(_Traceback)),
    ]

    def tb_set_next(tb, next):
        """Set the tb_next attribute of a traceback object."""
        if not (
            isinstance(tb, TracebackType)
            and (next is None or isinstance(next, TracebackType))
        ):
            raise TypeError("tb_set_next arguments must be traceback objects")
        obj = _Traceback.from_address(id(tb))
        if tb.tb_next is not None:
            old = _Traceback.from_address(id(tb.tb_next))
            old.ob_refcnt -= 1
        if next is None:
            obj.tb_next = ctypes.POINTER(_Traceback)()
        else:
            next = _Traceback.from_address(id(next))
            next.ob_refcnt += 1
            obj.tb_next = ctypes.pointer(next)

    return tb_set_next


if sys.version_info >= (3, 7):
    # tb_next is directly assignable as of Python 3.7
    def tb_set_next(tb, tb_next) -> TracebackType:
        tb.tb_next = tb_next
        return tb


else:
    # try to get a tb_set_next implementation if we don't have transparent
    # proxies.
    tb_set_next = None
    if tproxy is None:  # pragma: no cover
        try:
            tb_set_next = _init_ugly_crap()
        except Exception:
            pass

        del _init_ugly_crap
