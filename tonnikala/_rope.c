#include <Python.h>
#include "structmember.h"

typedef struct Rope {
    PyObject_HEAD
    int flags;
    PyObject **objects;
    Py_ssize_t length;
    Py_ssize_t used_slots;
    Py_ssize_t array_size;
} Rope;

static PyTypeObject RopeType;

static void
Rope_dealloc(Rope* self)
{
    if (self->used_slots) {
        Py_ssize_t i;
        for (i = self->used_slots - 1; i >= 0; i --) {
            Py_DECREF(self->objects[i]);
        }

        PyMem_Free(self->objects);
        self->used_slots = 0;
    }

    self->ob_type->tp_free((PyObject*)self);
}

static int
Rope_init(Rope *self, PyObject *args, PyObject *kwds)
{
    static char *kwlist[] = { NULL };
    if (! PyArg_ParseTupleAndKeywords(args, kwds, "", kwlist))
        return -1;

    self->objects = (PyObject**)PyMem_Malloc(sizeof(PyObject*) * 16);
    self->used_slots = 0;
    self->array_size = 16;
    return 0;
}

static PyObject *
Rope_append(Rope* self, PyObject *arg)
{
    Py_ssize_t length;
    if (self->flags & 7) {
        PyErr_SetString(PyExc_TypeError, "this Rope cannot be appended to now");
        return NULL;
    }

    self->flags |= 2;

    if (PyUnicode_CheckExact(arg)) {
        length = PyUnicode_GET_SIZE(arg);
    }
    else {
        if (! PyObject_TypeCheck(arg, &RopeType)) {
            PyErr_SetString(PyExc_TypeError, "append must be given a unicode object or a Rope");
            self->flags &= ~2;
            return NULL;
        }

        Rope *rope = (Rope*)arg;
        if (self == rope) {
            PyErr_SetString(PyExc_TypeError, "cannot add Rope to itself");
            self->flags &= ~2;
            return NULL;
        }

        // locked
        rope->flags |= 1;
	length = ((Rope*)arg)->length;
    }

    if (self->used_slots == self->array_size) {
        Py_ssize_t new_size = self->array_size << 1;
        PyObject **new_ary = PyMem_Realloc(self->objects, sizeof(PyObject *) * new_size);

        if (! new_ary) {
            self->flags &= ~2;
            return PyErr_NoMemory();
        }
        self->objects = new_ary;
        self->array_size = new_size;
    }

    Py_INCREF(arg);
    self->length += length;
    self->objects[self->used_slots ++] = arg;

    self->flags &= ~2;
    Py_INCREF(Py_None);
    return Py_None;
}

static int
rope_copy(Rope *self, PyUnicodeObject *to, Py_ssize_t from, Py_ssize_t array_length)
{
    Py_UNICODE *ptr = PyUnicode_AS_UNICODE(to);
    ptr += from;
    PyUnicodeObject *tmp;
    Py_ssize_t size;

    Py_ssize_t the_max = self->used_slots;
    Py_ssize_t ct;

    for (ct = 0; ct < the_max; ct ++) {
        PyObject *obj = self->objects[ct];

        if (PyUnicode_CheckExact(obj)) {
            tmp = (PyUnicodeObject*)obj;
            size = PyUnicode_GET_SIZE(tmp);
            Py_UNICODE_COPY(ptr, tmp->str, size);
        }
        else {
            Rope *rope = (Rope*)obj;
            size = rope->length;
            if (! rope_copy(rope, to, from, array_length)) {
                return 0;
            }
        }

        ptr += size;
        from += size;
    }

    return 1;
}

static PyObject *
Rope_unicode(Rope* self, PyObject *a, PyObject *kw)
{
    if (self->flags & 2) {
        PyErr_SetString(PyExc_TypeError, "cannot convert the rope to a string while a modify operation is in progress");
    }

    self->flags |= 4;
    PyUnicodeObject *rv = (PyUnicodeObject*)PyUnicode_FromUnicode(NULL, self->length);
    if (! rv) {
        goto error_exit_fast;
    }

    if (! rope_copy(self, rv, 0, self->length)) {
        goto error_exit;
    }

    self->flags &= ~4;
    return (PyObject*)rv;

error_exit:
    Py_DECREF(rv);

error_exit_fast:
    self->flags &= ~4;
    return NULL;
}


static PyMethodDef Rope_methods[] = {
    { "append", (PyCFunction)Rope_append, METH_O,
        "Append an object to the rope" },

    { "__unicode__", (PyCFunction)Rope_unicode, METH_NOARGS,
        "Convert the function to unicode" },

    {NULL}  /* Sentinel */
};

static PyTypeObject RopeType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "_rope.Rope",              /*tp_name*/
    sizeof(Rope),              /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)Rope_dealloc,  /*tp_dealloc*/
    0,                         /*tp_print*/
    0,                         /*tp_getattr*/
    0,                         /*tp_setattr*/
    0,                         /*tp_compare*/
    0,                         /*tp_repr*/
    0,                         /*tp_as_number*/
    0,                         /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/
    "Rope objects",            /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,		               /* tp_richcompare */
    0,		               /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
    Rope_methods,              /* tp_methods */
    0,  // Rope_members,              /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)Rope_init,       /* tp_init */
    0,                         /* tp_alloc */
    0 // Rope_new,             /* tp_new */
};

static PyMethodDef module_methods[] = {
    {NULL}  /* Sentinel */
};

#ifndef PyMODINIT_FUNC	/* declarations for DLL import/export */
#define PyMODINIT_FUNC void
#endif
PyMODINIT_FUNC
init_rope
(void)
{
    PyObject* m;

    RopeType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&RopeType) < 0)
        return;

    m = Py_InitModule3("_rope", module_methods,
                       "Rope type.");

    if (m == NULL)
      return;

    Py_INCREF(&RopeType);
    PyModule_AddObject(m, "Rope", (PyObject *)&RopeType);
}
