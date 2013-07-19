/*
 * Modifications (C) 2011 Liilak Inc. All rights reserved,
 *
 * Copyright (C) 2006-2008 Edgewall Software
 * All rights reserved.
 *
 * This software is licensed as described in the file COPYING.speedups, which
 * you should have received as part of this distribution. The terms
 * are also available at http://genshi.edgewall.org/wiki/License.
 *
 * This software consists of voluntary contributions made by many
 * individuals. For the exact contribution history, see the revision
 * history and logs, available at http://genshi.edgewall.org/log/.
 */

#include <Python.h>
#include <structmember.h>

#if PY_VERSION_HEX < 0x02050000 && !defined(PY_SSIZE_T_MIN)
typedef int Py_ssize_t;
#define PY_SSIZE_T_MAX INT_MAX
#define PY_SSIZE_T_MIN INT_MIN
#endif

static PyUnicodeObject *amp, *lt, *gt, *qt;

static void
init_constants(void)
{
    amp = (PyUnicodeObject*)PyUnicode_FromString("&amp;");
    lt  = (PyUnicodeObject*)PyUnicode_FromString("&lt;");
    gt  = (PyUnicodeObject*)PyUnicode_FromString("&gt;");
    qt  = (PyUnicodeObject*)PyUnicode_FromString("&#34;");
}

static PyUnicodeObject *
escape(PyUnicodeObject *in, int quotes)
{
    PyUnicodeObject *out;
    Py_UNICODE *inp, *outp;
    int len, inn, outn;

    /* First we need to figure out how long the escaped string will be */
    len = inn = 0;
    inp = in->str;
    while (*(inp) || in->length > inp - in->str) {
        switch (*inp++) {
            case '&': len += 5; inn++;                                 break;
            case '"': len += quotes ? 5 : 1; inn += quotes ? 1 : 0;    break;
            case '<':
            case '>': len += 4; inn++;                                 break;
            default:  len++;
        }
    }

    /* Do we need to escape anything at all? */
    if (!inn) {
        Py_INCREF(in);
        return in;
    }

    /* Hmm, should this throw an exception? */
    out = (PyUnicodeObject*) PyUnicode_FromUnicode(NULL, len);
    if (! out) {
        return NULL;
    }

    outn = 0;
    inp = in->str;
    outp = out->str;
    while (*(inp) || in->length > inp - in->str) {
        if (outn == inn) {
            /* copy rest of string if we have already replaced everything */
            Py_UNICODE_COPY(outp, inp, in->length - (inp - in->str));
            break;
        }
        switch (*inp) {
            case '&':
                Py_UNICODE_COPY(outp, amp->str, 5);
                outp += 5;
                outn++;
                break;
            case '"':
                if (quotes) {
                    Py_UNICODE_COPY(outp, qt->str, 5);
                    outp += 5;
                    outn++;
                } else {
                    *outp++ = *inp;
                }
                break;
            case '<':
                Py_UNICODE_COPY(outp, lt->str, 4);
                outp += 4;
                outn++;
                break;
            case '>':
                Py_UNICODE_COPY(outp, gt->str, 4);
                outp += 4;
                outn++;
                break;
            default:
                *outp++ = *inp;
        }
        inp++;
    }

    return out;
}

PyDoc_STRVAR(escape__doc__,
"Escape an unicode instance from a string and escape special characters\n\
it may contain (<, >, & and \").\n\
\n\
>>> escape('\"1 < 2\"')\n\
u'&#34;1 &lt; 2&#34;'\n\
\n\
If the `quotes` parameter is set to `False`, the \" character is left\n\
as is. Escaping quotes is generally only required for strings that are\n\
to be used in attribute values.\n\
\n\
>>> escape('\"1 < 2\"', quotes=False)\n\
u'\"1 &lt; 2\"'\n\
\n\
:param text: the unicode string to escape\n\
:param quotes: if ``True``, double quote characters are escaped in\n\
               addition to the other special characters\n\
:return: the escaped unicode string\n\
:rtype: `unicode`\n\
");

static PyObject *
do_escape(PyObject *self, PyObject *args, PyObject *kwds)
{
    static char *kwlist[] = {"text", "quotes", 0};
    PyUnicodeObject *text = NULL;
    char quotes = 1;

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "U|b", kwlist, &text, &quotes)) {
        return NULL;
    }

    return (PyObject*)escape(text, quotes);
}

PyDoc_STRVAR(flatten__doc__,
"Escape an unicode instance from a string and escape special characters\n\
it may contain (<, >, & and \").\n\
");

static PyObject *
do_flatten(PyObject *self, PyObject *arg, PyObject *kwds)
{
    PyObject *iterator = PyObject_GetIter(arg);

    if (! iterator) {
        return NULL;
    }

    Py_ssize_t allocated = 16;
    Py_ssize_t used = 0;
    PyObject **iterator_stack = (PyObject **)PyMem_New(PyObject *, allocated);
    PyListObject *rv = (PyListObject*)PyList_New(0);

    while (1) {
        PyObject *new_obj = PyIter_Next(iterator);

        if (new_obj) {
            if (PyUnicode_CheckExact(new_obj)) {
                // steals the reference...
                PyList_Append((PyObject*)rv, new_obj);
            }
            else {
                iterator_stack[used ++] = iterator;
                iterator = PyObject_GetIter(new_obj);
                Py_DECREF(new_obj);

                if (! iterator) {
                    goto error;
                }

                // loop with next iter
            }
        }
        else {
            // iterator failed for one reason or another
            int had_err = !!PyErr_Occurred();
            Py_DECREF(iterator);

            if (had_err) {
                goto error;
            }

            // exit loop here, all exhausted
            if (! used) {
                break;
            }

            iterator = iterator_stack[-- used];
        }
    }

    PyMem_Free(iterator_stack);
    return (PyObject*)rv;

error:
    for (used -= 1; used >= 0; used --) {
        Py_DECREF(iterator_stack[used]);
    }

    PyMem_Free(iterator_stack);
    Py_DECREF(rv);
    return NULL;
}

static PyMethodDef module_methods[] = {
    {"escape",  (PyCFunction)do_escape,
        METH_VARARGS|METH_KEYWORDS, escape__doc__},
    {"flatten", (PyCFunction)do_flatten,
        METH_O, flatten__doc__},
    {NULL, NULL}  /* Sentinel */
};

PyMODINIT_FUNC
init_speedups(void)
{
    init_constants();
    Py_InitModule("_speedups", module_methods);
}
