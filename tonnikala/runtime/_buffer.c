#include <Python.h>
#include <structmember.h>
#include <stdio.h>

#if PY_MAJOR_VERSION >= 3
#define IS_PY3 1
#else
#define IS_PY3 0
#endif

typedef struct {
    PyObject_HEAD
    PyObject *buffer_list;
    PyObject *output_boolean_attr;
    PyObject *output;
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
        self->buffer_list = PyList_New(0);
        if (self->buffer_list == NULL) {
            Py_DECREF(self);
            return NULL;
        }
        Py_INCREF(Py_None);
        self->output_boolean_attr = Py_None;
        self->output = (PyObject *)self;
    }

    return (PyObject *)self;
}

static PyObject *
Buffer_call(Buffer *self, PyObject *args, PyObject *other)
{
    Py_ssize_t tuple_size;
    Py_ssize_t i;
    if (other != NULL) {
        PyErr_SetString(PyExc_TypeError,
            "__call__ does not take keyword arguments");

        return NULL;
    }

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
Buffer__html__(PyObject* self) {
    Py_INCREF(self);
    return self;
}

static PyMemberDef Buffer_members[] = {
    {"buffer", T_OBJECT_EX, offsetof(Buffer, buffer_list), 0,
         "The buffer list"},
    { "output_boolean_attr", T_OBJECT_EX,
         offsetof(Buffer, output_boolean_attr), 0, "The attr output function" },
    { "output", T_OBJECT_EX,
         offsetof(Buffer, output), 0, "The attr output function" },
    {NULL}  /* Sentinel */
};

static PyMethodDef Buffer_methods[] = {
    { "__html__", (PyCFunction)Buffer__html__, METH_NOARGS,
        "Returns self unmodified" },
    { "join", (PyCFunction)Buffer_join, METH_NOARGS,
        "Returns the contents of the buffer as a string" },
    {NULL}  /* Sentinel */
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
    (ternaryfunc)Buffer_call,  /* tp_call */
    Buffer_join,               /* tp_str */
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

#define BUFFER_DOC "Accelerated Buffer type for speeding up output ops on Tonnikala templates"

#if IS_PY3
static PyModuleDef buffermodule = {
    PyModuleDef_HEAD_INIT,
    "buffer",
    BUFFER_DOC,
    -1,
    NULL,
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
    if (m == NULL)
        return NULL;

    if (PyType_Ready(&buffer_BufferType) < 0)
        return NULL;

    Py_INCREF(&buffer_BufferType);
    PyModule_AddObject(m, "Buffer", (PyObject *)&buffer_BufferType);
    return m;
}
#else // Python 2

PyMODINIT_FUNC
init_buffer(void) {
    PyObject *m;
    m = Py_InitModule3("_buffer", NULL, BUFFER_DOC);
    if (m == NULL)
        return;

    if (PyType_Ready(&buffer_BufferType) < 0)
        return;

    Py_INCREF(&buffer_BufferType);
    PyModule_AddObject(m, "Buffer", (PyObject *)&buffer_BufferType);
}

#endif
