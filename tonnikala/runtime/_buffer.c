#include <Python.h>
#include <structmember.h>
#include <stdio.h>

struct Buffer_module_state {
    PyObject *escape;
    PyObject *equals_quot;
    PyObject *quot;
    PyObject *space;
};

#if PY_MAJOR_VERSION >= 3

static PyModuleDef buffermodule;

#define GETSTATE(m) ((struct Buffer_module_state*)PyModule_GetState(m))
#define IS_PY3 1

#else

#define GETSTATE(m) (&_state)
static struct Buffer_module_state _state;

#define IS_PY3 0
#endif

typedef struct {
    PyObject_HEAD
    PyObject *buffer_list;
    PyObject *escape_func;
    PyObject *equals_quot;
    PyObject *quot;
    PyObject *space;
} Buffer;

static void
Buffer_dealloc(Buffer* self)
{
    Py_XDECREF(self->buffer_list);
    Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyTypeObject buffer_BufferType;

static PyObject *
Buffer_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    Buffer *self;

    self = (Buffer *)type->tp_alloc(type, 0);
    if (self != NULL) {
#if IS_PY3
        PyObject* module = PyState_FindModule(&buffermodule);
#else
#endif
        self->buffer_list = PyList_New(0);
        if (self->buffer_list == NULL) {
            Py_DECREF(self);
            return NULL;
        }

        self->escape_func = GETSTATE(module)->escape;
        Py_INCREF(self->escape_func);

        self->equals_quot = GETSTATE(module)->equals_quot;
        Py_INCREF(self->equals_quot);

        self->quot = GETSTATE(module)->quot;
        Py_INCREF(self->quot);

        self->space = GETSTATE(module)->space;
        Py_INCREF(self->space);
    }

    return (PyObject *)self;
}

static PyObject *
_do_append(Buffer *self, PyObject *args) {
    Py_ssize_t tuple_size;
    Py_ssize_t i;

    tuple_size = PyTuple_GET_SIZE(args);
    for (i = 0; i < tuple_size; i++) {
        PyObject* obj;
        obj = PyTuple_GET_ITEM(args, i);
        if (Py_TYPE(obj) == &buffer_BufferType) {
            PyObject *rv;
            rv = _PyList_Extend((PyListObject*)self->buffer_list,
                ((Buffer*)obj)->buffer_list);
            if (! rv) {
                return NULL;
            }
            // extend returns Py_None on success
            Py_DECREF(rv);
        }
        else {
            if (! PyUnicode_CheckExact(obj)) {
                obj = PyObject_Str(obj);
                if (! obj) {
                    return NULL;
                }
                if (PyList_Append(self->buffer_list, obj) != 0) {
                    return NULL;
                }
                // it is a new reference
                Py_DECREF(obj);
            }
            else {
                if (PyList_Append(self->buffer_list, obj) != 0) {
                    return NULL;
                }
            }
        }
    }

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *
Buffer_call(PyObject *self, PyObject *args, PyObject *other)
{
    if (other != NULL) {
        PyErr_SetString(PyExc_TypeError,
            "__call__ does not take keyword arguments");

        return NULL;
    }

    return _do_append((Buffer*)self, args);
}

static PyObject *
Buffer_output_boolean_attr(Buffer *self, PyObject *args) {
    ternaryfunc call;
    Py_ssize_t tuple_size;

    tuple_size = PyTuple_GET_SIZE(args);
    if (tuple_size != 2) {
        PyErr_SetString(PyExc_TypeError,
            "output_boolean_attr takes 2 arguments: name and value");
        return NULL;
    }

    PyObject *value = PyTuple_GET_ITEM(args, 1);
    if (value == Py_None || value == Py_False) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    PyObject *name = PyTuple_GET_ITEM(args, 0);
    PyObject *tmp = PyTuple_New(5);
    if (! tmp) {
        goto error;
    }

    if (value == Py_True) {
        Py_INCREF(name);
        value = name;
    }
    else {
        call = self->escape_func->ob_type->tp_call;
        if (call == NULL) {
            PyErr_SetString(PyExc_TypeError,
                "escape function is not callable");
            return NULL;
        }

        PyObject *escape_args = PyTuple_New(1);
        Py_INCREF(value);
        PyTuple_SET_ITEM(escape_args, 0, value);

        PyObject *result = (*call)(self->escape_func, escape_args, NULL);
        if (result == NULL) {
            goto error;
        }

        Py_DECREF(escape_args);
        value = result;
    }

    Py_INCREF(self->space);
    PyTuple_SET_ITEM(tmp, 0, self->space);

    Py_INCREF(name);
    PyTuple_SET_ITEM(tmp, 1, name);

    Py_INCREF(self->equals_quot);
    PyTuple_SET_ITEM(tmp, 2, self->equals_quot);

    PyTuple_SET_ITEM(tmp, 3, value);

    Py_INCREF(self->quot);
    PyTuple_SET_ITEM(tmp, 4, self->quot);

    PyObject *rv = _do_append(self, tmp);
    Py_DECREF(tmp);

    return rv;
error:
    return NULL;
}


static PyObject *
Buffer_join(PyObject *self, PyObject *args) {
    PyObject *sep, *rv;
#if IS_PY3
    sep = PyUnicode_InternFromString("");
#else
    sep = PyUnicode_FromString("");
#endif
    rv = PyUnicode_Join(sep, ((Buffer*)self)->buffer_list);
    Py_DECREF(sep);
    return rv;
}

static PyObject *
Buffer_str(PyObject *self) {
    return Buffer_join(self, NULL);
}

static PyObject *
Buffer__html__(PyObject* self, PyObject *arg) {
    Py_INCREF(self);
    return self;
}

static PyObject *
_set_escape_method(PyObject *self, PyObject *args, PyObject *kwargs) {
    static char *_keywords[] = {"escape", NULL};

    PyObject *escape = NULL;
    if (!PyArg_ParseTupleAndKeywords(args, kwargs,
        "|O:_set_escape_method", _keywords,
        &escape))
        goto exit;

    PyObject *old = GETSTATE(self)->escape;

    Py_DECREF(old);
    Py_INCREF(escape);

    GETSTATE(self)->escape = escape;

    Py_INCREF(Py_None);
    return Py_None;

exit:
    return NULL;
}

static PyMemberDef Buffer_members[] = {
    {"buffer", T_OBJECT_EX, offsetof(Buffer, buffer_list), 0,
     "The buffer list"},
    {NULL}  /* Sentinel */
};

static PyMethodDef Buffer_methods[] = {
    { "__html__", Buffer__html__, METH_NOARGS,
        "Returns self unmodified" },
    { "join", Buffer_join, METH_NOARGS,
        "Returns the contents of the buffer as a string" },
    { "output_boolean_attr",
        (PyCFunction)Buffer_output_boolean_attr,
        METH_VARARGS,
        "Outputs a bool	ean or string attribute" },
    {NULL}  /* Sentinel */
};

static PyMethodDef Buffer_module_methods[] = {
    {"_set_escape_method",
     (PyCFunction)_set_escape_method,
     METH_VARARGS | METH_KEYWORDS,
     "Sets the escape method used by buffer to escape strings"},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};


static PyTypeObject buffer_BufferType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "buffer.Buffer",           /* tp_name */
    sizeof(Buffer),            /* tp_basicsize */
    0,                         /* tp_itemsize */
    (destructor)Buffer_dealloc,            /* tp_dealloc */
    0,                         /* tp_print */
    0,                         /* tp_getattr */
    0,                         /* tp_setattr */
    0,                         /* tp_reserved */
    0,                         /* tp_repr */
    0,                         /* tp_as_number */
    0,                         /* tp_as_sequence */
    0,                         /* tp_as_mapping */
    0,                         /* tp_hash  */
    Buffer_call,               /* tp_call */
    Buffer_str,                /* tp_str (is a reprfunc) */
    0,                         /* tp_getattro */
    0,                         /* tp_setattro */
    0,                         /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT,        /* tp_flags */
    "Buffer objects",          /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    Buffer_methods,            /* tp_methods */
    Buffer_members,            /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    0,                         /* tp_init */
    0,                         /* tp_alloc */
    Buffer_new,                /* tp_new */
};

#define BUFFER_DOC "Accelerated Buffer type for speeding up" \
                   "output ops on Tonnikala templates"

#if IS_PY3
static PyModuleDef buffermodule = {
    PyModuleDef_HEAD_INIT,
    "buffer",
    BUFFER_DOC,
    sizeof(struct Buffer_module_state),
    Buffer_module_methods,
    NULL,
    NULL,
    NULL,
    NULL
};

PyMODINIT_FUNC
PyInit__buffer(void)
{
    PyObject* m;

    m = PyModule_Create(&buffermodule);

#define ERROR_RET NULL
#else // Python 2

PyMODINIT_FUNC
init_buffer(void) {
    PyObject *m;
    m = Py_InitModule3("_buffer", Buffer_module_methods, BUFFER_DOC);

#define ERROR_RET
#endif

    if (m == NULL)
        return ERROR_RET;

    if (PyType_Ready(&buffer_BufferType) < 0)
        return ERROR_RET;

    Py_INCREF(&buffer_BufferType);
    PyModule_AddObject(m, "Buffer", (PyObject *)&buffer_BufferType);

    struct Buffer_module_state *st = GETSTATE(m);

    Py_INCREF(Py_None);

    st->escape = Py_None;
    st->equals_quot = PyUnicode_FromString("=\"");
    st->space = PyUnicode_FromString(" ");
    st->quot = PyUnicode_FromString("\"");

#if IS_PY3
    return m;
#endif
}
