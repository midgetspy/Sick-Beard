/*
#
# Copyright (c) 2006-2008 Canonical
#
# Written by Gustavo Niemeyer <gustavo@niemeyer.net>
#
# This file is part of Storm Object Relational Mapper.
#
# Storm is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 2.1 of
# the License, or (at your option) any later version.
#
# Storm is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
*/
#include <Python.h>
#include <structmember.h>


#if PY_VERSION_HEX < 0x02050000 && !defined(PY_SSIZE_T_MIN)
typedef int Py_ssize_t;
#define PY_SSIZE_T_MAX INT_MAX
#define PY_SSIZE_T_MIN INT_MIN
#endif


#define CATCH(error_value, expression) \
        do { \
            if ((expression) == error_value) {\
                /*printf("GOT AN ERROR AT LINE %d!\n", __LINE__);*/ \
                goto error; \
            } \
        } while (0)

#define REPLACE(variable, new_value) \
        do { \
            PyObject *tmp = variable; \
            variable = new_value; \
            Py_DECREF(tmp); \
        } while(0)


/* Python 2.4 does not include the PySet_* API, so provide a minimal
   implementation for the calls we care about. */
#if PY_VERSION_HEX < 0x02050000 && !defined(PySet_GET_SIZE)
#  define PySet_GET_SIZE(so) \
     ((PyDictObject *)((PySetObject *)so)->data)->ma_used
static PyObject *
PySet_New(PyObject *p)
{
    return PyObject_CallObject((PyObject *)&PySet_Type, NULL);
}

static int
PySet_Add(PyObject *set, PyObject *key)
{
    PyObject *dict;

    if (!PyType_IsSubtype(set->ob_type, &PySet_Type)) {
        PyErr_BadInternalCall();
        return -1;
    }
    dict = ((PySetObject *)set)->data;
    return PyDict_SetItem(dict, key, Py_True);
}

static int
PySet_Discard(PyObject *set, PyObject *key)
{
    PyObject *dict;
    int result;

    if (!PyType_IsSubtype(set->ob_type, &PySet_Type)) {
        PyErr_BadInternalCall();
        return -1;
    }
    dict = ((PySetObject *)set)->data;
    result = PyDict_DelItem(dict, key);
    if (result == 0) {
        /* key found and removed */
        result = 1;
    } else {
        if (PyErr_ExceptionMatches(PyExc_KeyError)) {
            /* key not found */
            PyErr_Clear();
            result = 0;
        }
    }
    return result;
}
#endif

static PyObject *Undef = NULL;
static PyObject *LazyValue = NULL;
static PyObject *raise_none_error = NULL;
static PyObject *get_cls_info = NULL;
static PyObject *EventSystem = NULL;
static PyObject *SQLRaw = NULL;
static PyObject *SQLToken = NULL;
static PyObject *State = NULL;
static PyObject *CompileError = NULL;
static PyObject *parenthesis_format = NULL;
static PyObject *default_compile_join = NULL;


typedef struct {
    PyObject_HEAD
    PyObject *_owner_ref;
    PyObject *_hooks;
} EventSystemObject;

typedef struct {
    PyObject_HEAD
    PyObject *_value;
    PyObject *_lazy_value;
    PyObject *_checkpoint_state;
    PyObject *_allow_none;
    PyObject *_validator;
    PyObject *_validator_object_factory;
    PyObject *_validator_attribute;
    PyObject *column;
    PyObject *event;
} VariableObject;

typedef struct {
    PyObject_HEAD
    PyObject *__weakreflist;
    PyObject *_local_dispatch_table;
    PyObject *_local_precedence;
    PyObject *_local_reserved_words;
    PyObject *_dispatch_table;
    PyObject *_precedence;
    PyObject *_reserved_words;
    PyObject *_children;
    PyObject *_parents;
} CompileObject;

typedef struct {
    PyDictObject super;
    PyObject *__weakreflist;
    PyObject *__obj_ref;
    PyObject *__obj_ref_callback;
    PyObject *cls_info;
    PyObject *event;
    PyObject *variables;
    PyObject *primary_vars;
} ObjectInfoObject;


static int
initialize_globals(void)
{
    static int initialized = 0;
    PyObject *module;

    if (initialized)
        return 1;

    initialized = 1;

    /* Import objects from storm module */
    module = PyImport_ImportModule("storm");
    if (!module)
        return 0;

    Undef = PyObject_GetAttrString(module, "Undef");
    if (!Undef)
        return 0;

    Py_DECREF(module);

    /* Import objects from storm.variables module */
    module = PyImport_ImportModule("storm.variables");
    if (!module)
        return 0;

    raise_none_error = PyObject_GetAttrString(module, "raise_none_error");
    if (!raise_none_error)
        return 0;

    LazyValue = PyObject_GetAttrString(module, "LazyValue");
    if (!LazyValue)
        return 0;

    Py_DECREF(module);

    /* Import objects from storm.info module */
    module = PyImport_ImportModule("storm.info");
    if (!module)
        return 0;

    get_cls_info = PyObject_GetAttrString(module, "get_cls_info");
    if (!get_cls_info)
        return 0;

    Py_DECREF(module);

    /* Import objects from storm.event module */
    module = PyImport_ImportModule("storm.event");
    if (!module)
        return 0;

    EventSystem = PyObject_GetAttrString(module, "EventSystem");
    if (!EventSystem)
        return 0;

    Py_DECREF(module);

    /* Import objects from storm.expr module */
    module = PyImport_ImportModule("storm.expr");
    if (!module)
        return 0;

    SQLRaw = PyObject_GetAttrString(module, "SQLRaw");
    if (!SQLRaw)
        return 0;

    SQLToken = PyObject_GetAttrString(module, "SQLToken");
    if (!SQLToken)
        return 0;

    State = PyObject_GetAttrString(module, "State");
    if (!State)
        return 0;

    CompileError = PyObject_GetAttrString(module, "CompileError");
    if (!CompileError)
        return 0;

    Py_DECREF(module);

    /* A few frequently used objects which are part of the fast path. */

    parenthesis_format = PyUnicode_DecodeASCII("(%s)", 4, "strict");
    default_compile_join = PyUnicode_DecodeASCII(", ", 2, "strict");

    return 1;
}


static int
EventSystem_init(EventSystemObject *self, PyObject *args, PyObject *kwargs)
{
    static char *kwlist[] = {"owner", NULL};
    PyObject *owner;
    int result = -1;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "O", kwlist, &owner))
        return -1;

    /* self._owner_ref = weakref.ref(owner) */
    self->_owner_ref = PyWeakref_NewRef(owner, NULL);
    if (self->_owner_ref) {
        /* self._hooks = {} */
        self->_hooks = PyDict_New();
        if (self->_hooks) {
            result = 0;
        }
    }

    return result;
}

static int
EventSystem_traverse(EventSystemObject *self, visitproc visit, void *arg)
{
    Py_VISIT(self->_owner_ref);
    Py_VISIT(self->_hooks);
    return 0;
}

static int
EventSystem_clear(EventSystemObject *self)
{
    Py_CLEAR(self->_owner_ref);
    Py_CLEAR(self->_hooks);
    return 0;
}

static void
EventSystem_dealloc(EventSystemObject *self)
{
    EventSystem_clear(self);
    self->ob_type->tp_free((PyObject *)self);
}

static PyObject *
EventSystem_hook(EventSystemObject *self, PyObject *args)
{
    PyObject *result = NULL;
    PyObject *name, *callback, *data;

    if (PyTuple_GET_SIZE(args) < 2) {
        PyErr_SetString(PyExc_TypeError, "Invalid number of arguments");
        return NULL;
    }

    name = PyTuple_GET_ITEM(args, 0);
    callback = PyTuple_GET_ITEM(args, 1);
    data = PyTuple_GetSlice(args, 2, PyTuple_GET_SIZE(args));
    if (data) {
        /*
           callbacks = self._hooks.get(name)
           if callbacks is None:
               self._hooks.setdefault(name, set()).add((callback, data))
           else:
               callbacks.add((callback, data))
        */
        PyObject *callbacks = PyDict_GetItem(self->_hooks, name);
        if (!PyErr_Occurred()) {
            if (callbacks == NULL) {
                callbacks = PySet_New(NULL);
                if (callbacks &&
                    PyDict_SetItem(self->_hooks, name, callbacks) == -1) {
                    Py_DECREF(callbacks);
                    callbacks = NULL;
                }
            } else {
                Py_INCREF(callbacks);
            }
            if (callbacks) {
                PyObject *tuple = PyTuple_New(2);
                if (tuple) {
                    Py_INCREF(callback);
                    PyTuple_SET_ITEM(tuple, 0, callback);
                    Py_INCREF(data);
                    PyTuple_SET_ITEM(tuple, 1, data);
                    if (PySet_Add(callbacks, tuple) != -1) {
                        Py_INCREF(Py_None);
                        result = Py_None;
                    }
                    Py_DECREF(tuple);
                }
                Py_DECREF(callbacks);
            }
        }
        Py_DECREF(data);
    }

    return result;
}

static PyObject *
EventSystem_unhook(EventSystemObject *self, PyObject *args)
{
    PyObject *result = NULL;
    PyObject *name, *callback, *data;

    if (PyTuple_GET_SIZE(args) < 2) {
        PyErr_SetString(PyExc_TypeError, "Invalid number of arguments");
        return NULL;
    }

    name = PyTuple_GET_ITEM(args, 0);
    callback = PyTuple_GET_ITEM(args, 1);
    data = PyTuple_GetSlice(args, 2, PyTuple_GET_SIZE(args));
    if (data) {
        /*
           callbacks = self._hooks.get(name)
           if callbacks is not None:
               callbacks.discard((callback, data))
        */
        PyObject *callbacks = PyDict_GetItem(self->_hooks, name);
        if (callbacks) {
            PyObject *tuple = PyTuple_New(2);
            if (tuple) {
                Py_INCREF(callback);
                PyTuple_SET_ITEM(tuple, 0, callback);
                Py_INCREF(data);
                PyTuple_SET_ITEM(tuple, 1, data);
                if (PySet_Discard(callbacks, tuple) != -1) {
                    Py_INCREF(Py_None);
                    result = Py_None;
                }
                Py_DECREF(tuple);
            }
        } else if (!PyErr_Occurred()) {
            Py_INCREF(Py_None);
            result = Py_None;
        }
        Py_DECREF(data);
    }

    return result;
}

static PyObject *
EventSystem__do_emit_call(PyObject *callback, PyObject *owner,
                          PyObject *args, PyObject *data)
{
    /* return callback(owner, *(args+data)) */
    PyObject *result = NULL;
    PyObject *tuple = PyTuple_New(PyTuple_GET_SIZE(args) +
                                  PyTuple_GET_SIZE(data) + 1);
    if (tuple) {
        Py_ssize_t i, tuple_i;

        Py_INCREF(owner);
        PyTuple_SET_ITEM(tuple, 0, owner);
        tuple_i = 1;
        for (i = 0; i != PyTuple_GET_SIZE(args); i++) {
            PyObject *item = PyTuple_GET_ITEM(args, i);
            Py_INCREF(item);
            PyTuple_SET_ITEM(tuple, tuple_i++, item);
        }
        for (i = 0; i != PyTuple_GET_SIZE(data); i++) {
            PyObject *item = PyTuple_GET_ITEM(data, i);
            Py_INCREF(item);
            PyTuple_SET_ITEM(tuple, tuple_i++, item);
        }
        result = PyObject_Call(callback, tuple, NULL);
        Py_DECREF(tuple);
    }
    return result;
}

static PyObject *
EventSystem_emit(EventSystemObject *self, PyObject *all_args)
{
    PyObject *result = NULL;
    PyObject *name, *args;

    if (PyTuple_GET_SIZE(all_args) == 0) {
        PyErr_SetString(PyExc_TypeError, "Invalid number of arguments");
        return NULL;
    }

    /* XXX In the following code we trust on the format inserted by
     *     the hook() method.  If it's hacked somehow, it may blow up. */

    name = PyTuple_GET_ITEM(all_args, 0);
    args = PyTuple_GetSlice(all_args, 1, PyTuple_GET_SIZE(all_args));
    if (args) {
        /* owner = self._owner_ref() */
        PyObject *owner = PyWeakref_GET_OBJECT(self->_owner_ref);
        /* if owner is not None: */
        if (owner != Py_None) {
            /* callbacks = self._hooks.get(name) */
            PyObject *callbacks = PyDict_GetItem(self->_hooks, name);
            Py_INCREF(owner);
            /* if callbacks: */
            if (callbacks && PySet_GET_SIZE(callbacks) != 0) {
                /* for callback, data in tuple(callbacks): */
                PyObject *sequence = \
                    PySequence_Fast(callbacks, "callbacks object isn't a set");
                if (sequence) {
                    int failed = 0;
                    Py_ssize_t i;
                    for (i = 0; i != PySequence_Fast_GET_SIZE(sequence); i++) {
                        PyObject *item = PySequence_Fast_GET_ITEM(sequence, i);
                        PyObject *callback = PyTuple_GET_ITEM(item, 0);
                        PyObject *data = PyTuple_GET_ITEM(item, 1);
                        PyObject *res;
                        /*
                           if callback(owner, *(args+data)) is False:
                               callbacks.discard((callback, data))
                        */
                        res = EventSystem__do_emit_call(callback, owner,
                                                        args, data);
                        Py_XDECREF(res);
                        if (res == NULL ||
                            (res == Py_False &&
                             PySet_Discard(callbacks, item) == -1)) {
                            failed = 1;
                            break;
                        }
                    }
                    if (!failed) {
                        Py_INCREF(Py_None);
                        result = Py_None;
                    }
                    Py_DECREF(sequence);
                }
            } else if (!PyErr_Occurred()) {
                Py_INCREF(Py_None);
                result = Py_None;
            }
            Py_DECREF(owner);
        } else {
            Py_INCREF(Py_None);
            result = Py_None;
        }
        Py_DECREF(args);
    }

    return result;
}


static PyMethodDef EventSystem_methods[] = {
    {"hook", (PyCFunction)EventSystem_hook, METH_VARARGS, NULL},
    {"unhook", (PyCFunction)EventSystem_unhook, METH_VARARGS, NULL},
    {"emit", (PyCFunction)EventSystem_emit, METH_VARARGS, NULL},
    {NULL, NULL}
};

#define OFFSETOF(x) offsetof(EventSystemObject, x)
static PyMemberDef EventSystem_members[] = {
    {"_object_ref", T_OBJECT, OFFSETOF(_owner_ref), READONLY, 0},
    {"_hooks", T_OBJECT, OFFSETOF(_hooks), READONLY, 0},
    {NULL}
};
#undef OFFSETOF

statichere PyTypeObject EventSystem_Type = {
    PyObject_HEAD_INIT(NULL)
    0,            /*ob_size*/
    "storm.variables.EventSystem",    /*tp_name*/
    sizeof(EventSystemObject), /*tp_basicsize*/
    0,            /*tp_itemsize*/
    (destructor)EventSystem_dealloc, /*tp_dealloc*/
    0,            /*tp_print*/
    0,            /*tp_getattr*/
    0,            /*tp_setattr*/
    0,            /*tp_compare*/
    0,          /*tp_repr*/
    0,            /*tp_as_number*/
    0,            /*tp_as_sequence*/
    0,            /*tp_as_mapping*/
    0,                      /*tp_hash*/
    0,                      /*tp_call*/
    0,                      /*tp_str*/
    0,                      /*tp_getattro*/
    0,                      /*tp_setattro*/
    0,                      /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC, /*tp_flags*/
    0,                      /*tp_doc*/
    (traverseproc)EventSystem_traverse,  /*tp_traverse*/
    (inquiry)EventSystem_clear,          /*tp_clear*/
    0,                      /*tp_richcompare*/
    0,                      /*tp_weaklistoffset*/
    0,                      /*tp_iter*/
    0,                      /*tp_iternext*/
    EventSystem_methods,        /*tp_methods*/
    EventSystem_members,        /*tp_members*/
    0,                      /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    (initproc)EventSystem_init, /*tp_init*/
    0,                      /*tp_alloc*/
    0,                      /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};


static PyObject *
Variable_new(PyTypeObject *type, PyObject *args, PyObject *kwargs)
{
    VariableObject *self = (VariableObject *)type->tp_alloc(type, 0);

    if (!initialize_globals())
        return NULL;

    /* The following are defined as class properties, so we must initialize
       them here for methods to work with the same logic. */
    Py_INCREF(Undef);
    self->_value = Undef;
    Py_INCREF(Undef);
    self->_lazy_value = Undef;
    Py_INCREF(Undef);
    self->_checkpoint_state = Undef;
    Py_INCREF(Py_True);
    self->_allow_none = Py_True;
    Py_INCREF(Py_None);
    self->event = Py_None;
    Py_INCREF(Py_None);
    self->column = Py_None;

    return (PyObject *)self;
}

static int
Variable_init(VariableObject *self, PyObject *args, PyObject *kwargs)
{
    static char *kwlist[] = {"value", "value_factory", "from_db",
                             "allow_none", "column", "event", "validator",
                             "validator_object_factory", "validator_attribute",
                             NULL};

    PyObject *value = Undef;
    PyObject *value_factory = Undef;
    PyObject *from_db = Py_False;
    PyObject *allow_none = Py_True;
    PyObject *column = Py_None;
    PyObject *event = Py_None;
    PyObject *validator = Py_None;
    PyObject *validator_object_factory = Py_None;
    PyObject *validator_attribute = Py_None;
    PyObject *tmp;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "|OOOOOOOOO", kwlist, &value,
                                     &value_factory, &from_db, &allow_none,
                                     &column, &event, &validator,
                                     &validator_object_factory,
                                     &validator_attribute))
        return -1;

    /* if not allow_none: */
    if (allow_none != Py_True &&
        (allow_none == Py_False || !PyObject_IsTrue(allow_none))) {
        /* self._allow_none = False */
        Py_INCREF(Py_False);
        REPLACE(self->_allow_none, Py_False);
    }

    /* if value is not Undef: */
    if (value != Undef) {
        /* self.set(value, from_db) */
        CATCH(NULL, tmp = PyObject_CallMethod((PyObject *)self,
                                              "set", "OO", value, from_db));
        Py_DECREF(tmp);
    }
    /* elif value_factory is not Undef: */
    else if (value_factory != Undef) {
        /* self.set(value_factory(), from_db) */
        CATCH(NULL, value = PyObject_CallFunctionObjArgs(value_factory, NULL));
        tmp = PyObject_CallMethod((PyObject *)self,
                                  "set", "OO", value, from_db);
        Py_DECREF(value);
        CATCH(NULL, tmp);
        Py_DECREF(tmp);
    }

    /* if validator is not None: */
    if (validator != Py_None) {
        /* self._validator = validator */
        Py_INCREF(validator);
        self->_validator = validator;
        /* self._validator_object_factory = validator_object_factory */
        Py_INCREF(validator_object_factory);
        self->_validator_object_factory = validator_object_factory;
        /* self._validator_attribute = validator_attribute */
        Py_INCREF(validator_attribute);
        self->_validator_attribute = validator_attribute;
    }

    /* self.column = column */
    Py_DECREF(self->column);
    Py_INCREF(column);
    self->column = column;

    /* self.event = event */
    Py_DECREF(self->event);
    Py_INCREF(event);
    self->event = event;

    return 0;

error:
    return -1;
}

static int
Variable_traverse(VariableObject *self, visitproc visit, void *arg)
{
    Py_VISIT(self->_value);
    Py_VISIT(self->_lazy_value);
    Py_VISIT(self->_checkpoint_state);
    /* Py_VISIT(self->_allow_none); */
    Py_VISIT(self->_validator);
    Py_VISIT(self->_validator_object_factory);
    Py_VISIT(self->_validator_attribute);
    Py_VISIT(self->column);
    Py_VISIT(self->event);
    return 0;
}

static int
Variable_clear(VariableObject *self)
{
    Py_CLEAR(self->_value);
    Py_CLEAR(self->_lazy_value);
    Py_CLEAR(self->_checkpoint_state);
    Py_CLEAR(self->_allow_none);
    Py_CLEAR(self->_validator);
    Py_CLEAR(self->_validator_object_factory);
    Py_CLEAR(self->_validator_attribute);
    Py_CLEAR(self->column);
    Py_CLEAR(self->event);
    return 0;
}

static void
Variable_dealloc(VariableObject *self)
{
    Variable_clear(self);
    self->ob_type->tp_free((PyObject *)self);
}

static PyObject *
Variable_parse_get(VariableObject *self, PyObject *args)
{
    /* return value */
    PyObject *value, *to_db;
    if (!PyArg_ParseTuple(args, "OO:parse_get", &value, &to_db))
        return NULL;
    Py_INCREF(value);
    return value;
}

static PyObject *
Variable_parse_set(VariableObject *self, PyObject *args)
{
    /* return value */
    PyObject *value, *from_db;
    if (!PyArg_ParseTuple(args, "OO:parse_set", &value, &from_db))
        return NULL;
    Py_INCREF(value);
    return value;
}

static PyObject *
Variable_get_lazy(VariableObject *self, PyObject *args, PyObject *kwargs)
{
    static char *kwlist[] = {"default", NULL};
    PyObject *default_ = Py_None;
    PyObject *result;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "|O:get_lazy", kwlist,
                                     &default_))
        return NULL;

    /*
       if self._lazy_value is Undef:
           return default
       return self._lazy_value
    */
    if (self->_lazy_value == Undef) {
        result = default_;
    } else {
        result = self->_lazy_value;
    }
    Py_INCREF(result);
    return result;
}

static PyObject *
Variable_get(VariableObject *self, PyObject *args, PyObject *kwargs)
{
    static char *kwlist[] = {"default", "to_db", NULL};
    PyObject *default_ = Py_None;
    PyObject *to_db = Py_False;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "|OO:get", kwlist,
                                     &default_, &to_db))
        return NULL;

    /* if self._lazy_value is not Undef and self.event is not None: */
    if (self->_lazy_value != Undef && self->event != Py_None) {
        PyObject *tmp;
        /* self.event.emit("resolve-lazy-value", self, self._lazy_value) */
        CATCH(NULL, tmp = PyObject_CallMethod(self->event, "emit", "sOO",
                                              "resolve-lazy-value", self,
                                              self->_lazy_value));
        Py_DECREF(tmp);
    }

    /* value = self->_value */
    /* if value is Undef: */
    if (self->_value == Undef) {
        /* return default */
        Py_INCREF(default_);
        return default_;
    }

    /* if value is None: */
    if (self->_value == Py_None) {
        /* return None */
        Py_RETURN_NONE;
    }

    /* return self.parse_get(value, to_db) */
    return PyObject_CallMethod((PyObject *)self, "parse_get",
                               "OO", self->_value, to_db);

error:
    return NULL;
}

static PyObject *
Variable_set(VariableObject *self, PyObject *args, PyObject *kwargs)
{
    static char *kwlist[] = {"value", "from_db", NULL};
    PyObject *value = Py_None;
    PyObject *from_db = Py_False;
    PyObject *old_value = NULL;
    PyObject *new_value = NULL;
    PyObject *tmp;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "|OO:set", kwlist,
                                     &value, &from_db))
        return NULL;

    Py_INCREF(value);

    /* if isinstance(value, LazyValue): */
    if (PyObject_IsInstance(value, LazyValue)) {
        /* self._lazy_value = value */
        Py_INCREF(value);
        REPLACE(self->_lazy_value, value);

        /* self._checkpoint_state = new_value = Undef */
        Py_INCREF(Undef);
        Py_INCREF(Undef);
        new_value = Undef;
        Py_DECREF(self->_checkpoint_state);
        self->_checkpoint_state = Undef;
    }
    /* else: */
    else {
        /* if not from_db and self._validator is not None: */
        if (self->_validator && !PyObject_IsTrue(from_db)) {
            /* value = self._validator(self._validator_object_factory and
                                       self._validator_object_factory(),
                                       self._validator_attribute, value) */
            PyObject *validator_object, *tmp;
            if (self->_validator_object_factory == Py_None) {
                Py_INCREF(Py_None);
                validator_object = Py_None;
            } else {
                CATCH(NULL, validator_object = PyObject_CallFunctionObjArgs(
                                self->_validator_object_factory, NULL));
            }
            tmp = PyObject_CallFunctionObjArgs(self->_validator,
                                               validator_object,
                                               self->_validator_attribute,
                                               value, NULL);
            Py_DECREF(validator_object);
            CATCH(NULL, tmp);

            Py_DECREF(value);
            value = tmp;
        }

        /* self._lazy_value = Undef */
        Py_INCREF(Undef);
        Py_DECREF(self->_lazy_value);
        self->_lazy_value = Undef;

        /* if value is None: */
        if (value == Py_None) {
            /* if self._allow_none is False: */
            if (self->_allow_none == Py_False) {
                /* raise_none_error(self.column) */
                tmp = PyObject_CallFunctionObjArgs(raise_none_error,
                                                   self->column, NULL);
                /* tmp should always be NULL here. */
                Py_XDECREF(tmp);
                goto error;
            }

            /* new_value = None */
            Py_INCREF(Py_None);
            new_value = Py_None;
        }
        /* else: */
        else {
            /* new_value = self.parse_set(value, from_db) */
            CATCH(NULL,
                  new_value = PyObject_CallMethod((PyObject *)self, "parse_set",
                                                  "OO", value, from_db));

            /* if from_db: */
            if (PyObject_IsTrue(from_db)) {
                /* value = self.parse_get(new_value, False) */
                Py_DECREF(value);
                CATCH(NULL,
                      value = PyObject_CallMethod((PyObject *)self, "parse_get",
                                                  "OO", new_value, Py_False));
            }
        }
    }

    /* old_value = self._value */
    old_value = self->_value;
    /* Keep the reference with old_value. */

    /* self._value = new_value */
    Py_INCREF(new_value);
    self->_value = new_value;

    /* if (self.event is not None and
           (self._lazy_value is not Undef or new_value != old_value)): */
    if (self->event != Py_None &&
        (self->_lazy_value != Undef ||
         PyObject_RichCompareBool(new_value, old_value, Py_NE))) {

        /* if old_value is not None and old_value is not Undef: */
        if (old_value != Py_None && old_value != Undef) {
            /* old_value = self.parse_get(old_value, False) */
            CATCH(NULL, tmp = PyObject_CallMethod((PyObject *)self, "parse_get",
                                                  "OO", old_value, Py_False));
            Py_DECREF(old_value);
            old_value = tmp;
        }
        /* self.event.emit("changed", self, old_value, value, from_db) */
        CATCH(NULL, tmp = PyObject_CallMethod((PyObject *)self->event, "emit",
                                              "sOOOO", "changed", self,
                                              old_value, value, from_db));
        Py_DECREF(tmp);
    }

    Py_DECREF(value);
    Py_DECREF(old_value);
    Py_DECREF(new_value);

    Py_RETURN_NONE;

error:
    Py_XDECREF(value);
    Py_XDECREF(old_value);
    Py_XDECREF(new_value);
    return NULL;
}

static PyObject *
Variable_delete(VariableObject *self, PyObject *args)
{
    PyObject *old_value;
    PyObject *tmp;

    /* old_value = self._value */
    old_value = self->_value;
    Py_INCREF(old_value);

    /* if old_value is not Undef: */
    if (old_value != Undef) {

        /* self._value = Undef */
        Py_DECREF(self->_value);
        Py_INCREF(Undef);
        self->_value = Undef;

        /* if self.event is not None: */
        if (self->event != Py_None) {
            /* if old_value is not None and old_value is not Undef: */
            if (old_value != Py_None && old_value != Undef) {
                /* old_value = self.parse_get(old_value, False) */
                CATCH(NULL,
                      tmp = PyObject_CallMethod((PyObject *)self, "parse_get",
                                                "OO", old_value, Py_False));
                Py_DECREF(old_value);
                old_value = tmp;
            }

            /* self.event.emit("changed", self, old_value, Undef, False) */
            CATCH(NULL,
                  tmp = PyObject_CallMethod((PyObject *)self->event, "emit",
                                            "sOOOO", "changed", self, old_value,
                                            Undef, Py_False));
            Py_DECREF(tmp);
        }
    }

    Py_DECREF(old_value);
    Py_RETURN_NONE;

error:
    Py_XDECREF(old_value);
    return NULL;
}

static PyObject *
Variable_is_defined(VariableObject *self, PyObject *args)
{
    /* return self._value is not Undef */
    return PyBool_FromLong(self->_value != Undef);
}

static PyObject *
Variable_has_changed(VariableObject *self, PyObject *args)
{
    /* return (self._lazy_value is not Undef or
               self.get_state() != self._checkpoint_state) */
    PyObject *result = Py_True;
    if (self->_lazy_value == Undef) {
        PyObject *state;
        int res;
        CATCH(NULL, state = PyObject_CallMethod((PyObject *)self,
                                                "get_state", NULL));
        res = PyObject_RichCompareBool(state, self->_checkpoint_state, Py_EQ);
        Py_DECREF(state);
        CATCH(-1, res);
        if (res)
            result = Py_False;
    }
    Py_INCREF(result);
    return result;

error:
    return NULL;
}

static PyObject *
Variable_get_state(VariableObject *self, PyObject *args)
{
    /* return (self._lazy_value, self._value) */
    PyObject *result;
    CATCH(NULL, result = PyTuple_New(2));
    Py_INCREF(self->_lazy_value);
    Py_INCREF(self->_value);
    PyTuple_SET_ITEM(result, 0, self->_lazy_value);
    PyTuple_SET_ITEM(result, 1, self->_value);
    return result;
error:
    return NULL;
}

static PyObject *
Variable_set_state(VariableObject *self, PyObject *args)
{
    /* self._lazy_value, self._value = state */
    PyObject *lazy_value, *value;
    if (!PyArg_ParseTuple(args, "(OO):set_state", &lazy_value, &value))
        return NULL;
    Py_INCREF(lazy_value);
    REPLACE(self->_lazy_value, lazy_value);
    Py_INCREF(value);
    REPLACE(self->_value, value);
    Py_RETURN_NONE;
}

static PyObject *
Variable_checkpoint(VariableObject *self, PyObject *args)
{
    /* self._checkpoint_state = self.get_state() */
    PyObject *state = PyObject_CallMethod((PyObject *)self, "get_state", NULL);
    if (!state)
        return NULL;
    Py_DECREF(self->_checkpoint_state);
    self->_checkpoint_state = state;
    Py_RETURN_NONE;
}

static PyObject *
Variable_copy(VariableObject *self, PyObject *args)
{
    PyObject *noargs = NULL;
    PyObject *variable = NULL;
    PyObject *state = NULL;
    PyObject *tmp;

    /* variable = self.__class__.__new__(self.__class__) */
    noargs = PyTuple_New(0);
    CATCH(NULL, variable = self->ob_type->tp_new(self->ob_type, noargs, NULL));

    /* variable.set_state(self.get_state()) */
    CATCH(NULL,
          state = PyObject_CallMethod((PyObject *)self, "get_state", NULL));

    CATCH(NULL, tmp = PyObject_CallMethod((PyObject *)variable,
                                          "set_state", "(O)", state));
    Py_DECREF(tmp);

    Py_DECREF(noargs);
    Py_DECREF(state);
    return variable;

error:
    Py_XDECREF(noargs);
    Py_XDECREF(state);
    Py_XDECREF(variable);
    return NULL;
}

static PyMethodDef Variable_methods[] = {
    {"parse_get", (PyCFunction)Variable_parse_get, METH_VARARGS, NULL},
    {"parse_set", (PyCFunction)Variable_parse_set, METH_VARARGS, NULL},
    {"get_lazy", (PyCFunction)Variable_get_lazy,
        METH_VARARGS | METH_KEYWORDS, NULL},
    {"get", (PyCFunction)Variable_get, METH_VARARGS | METH_KEYWORDS, NULL},
    {"set", (PyCFunction)Variable_set, METH_VARARGS | METH_KEYWORDS, NULL},
    {"delete", (PyCFunction)Variable_delete,
        METH_VARARGS | METH_KEYWORDS, NULL},
    {"is_defined", (PyCFunction)Variable_is_defined, METH_NOARGS, NULL},
    {"has_changed", (PyCFunction)Variable_has_changed, METH_NOARGS, NULL},
    {"get_state", (PyCFunction)Variable_get_state, METH_NOARGS, NULL},
    {"set_state", (PyCFunction)Variable_set_state, METH_VARARGS, NULL},
    {"checkpoint", (PyCFunction)Variable_checkpoint, METH_NOARGS, NULL},
    {"copy", (PyCFunction)Variable_copy, METH_NOARGS, NULL},
    {NULL, NULL}
};

#define OFFSETOF(x) offsetof(VariableObject, x)
static PyMemberDef Variable_members[] = {
    {"_value", T_OBJECT, OFFSETOF(_value), 0, 0},
    {"_lazy_value", T_OBJECT, OFFSETOF(_lazy_value), 0, 0},
    {"_checkpoint_state", T_OBJECT, OFFSETOF(_checkpoint_state), 0, 0},
    {"_allow_none", T_OBJECT, OFFSETOF(_allow_none), 0, 0},
    {"column", T_OBJECT, OFFSETOF(column), 0, 0},
    {"event", T_OBJECT, OFFSETOF(event), 0, 0},
    {NULL}
};
#undef OFFSETOF

statichere PyTypeObject Variable_Type = {
    PyObject_HEAD_INIT(NULL)
    0,            /*ob_size*/
    "storm.variables.Variable",    /*tp_name*/
    sizeof(VariableObject), /*tp_basicsize*/
    0,            /*tp_itemsize*/
    (destructor)Variable_dealloc, /*tp_dealloc*/
    0,            /*tp_print*/
    0,            /*tp_getattr*/
    0,            /*tp_setattr*/
    0,            /*tp_compare*/
    0,          /*tp_repr*/
    0,            /*tp_as_number*/
    0,            /*tp_as_sequence*/
    0,            /*tp_as_mapping*/
    0,            /*tp_hash*/
    0,                      /*tp_call*/
    0,                      /*tp_str*/
    0,                      /*tp_getattro*/
    0,                      /*tp_setattro*/
    0,                      /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT|Py_TPFLAGS_BASETYPE|Py_TPFLAGS_HAVE_GC, /*tp_flags*/
    0,                      /*tp_doc*/
    (traverseproc)Variable_traverse,  /*tp_traverse*/
    (inquiry)Variable_clear,          /*tp_clear*/
    0,                      /*tp_richcompare*/
    0,                      /*tp_weaklistoffset*/
    0,                      /*tp_iter*/
    0,                      /*tp_iternext*/
    Variable_methods,        /*tp_methods*/
    Variable_members,        /*tp_members*/
    0,                      /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    (initproc)Variable_init, /*tp_init*/
    0,                       /*tp_alloc*/
    Variable_new,      /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};


static PyObject *
Compile__update_cache(CompileObject *self, PyObject *args);

static int
Compile_init(CompileObject *self, PyObject *args, PyObject *kwargs)
{
    static char *kwlist[] = {"parent", NULL};

    PyObject *parent = Py_None;

    PyObject *module = NULL;
    PyObject *WeakKeyDictionary = NULL;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "|O", kwlist, &parent))
        return -1;

    /*
       self._local_dispatch_table = {}
       self._local_precedence = {}
       self._local_reserved_words = {}
       self._dispatch_table = {}
       self._precedence = {}
       self._reserved_words = {}
    */
    CATCH(NULL, self->_local_dispatch_table = PyDict_New());
    CATCH(NULL, self->_local_precedence = PyDict_New());
    CATCH(NULL, self->_local_reserved_words = PyDict_New());
    CATCH(NULL, self->_dispatch_table = PyDict_New());
    CATCH(NULL, self->_precedence = PyDict_New());
    CATCH(NULL, self->_reserved_words = PyDict_New());

    /* self._children = WeakKeyDictionary() */
    CATCH(NULL, module = PyImport_ImportModule("weakref"));
    CATCH(NULL, WeakKeyDictionary = \
                    PyObject_GetAttrString(module, "WeakKeyDictionary"));
    Py_CLEAR(module);
    CATCH(NULL, self->_children = \
                    PyObject_CallFunctionObjArgs(WeakKeyDictionary, NULL));
    Py_CLEAR(WeakKeyDictionary);

    /* self._parents = [] */
    CATCH(NULL, self->_parents = PyList_New(0));

    /* if parent: */
    if (parent != Py_None) {
        PyObject *tmp;

        /* self._parents.extend(parent._parents) */
        CompileObject *parent_object = (CompileObject *)parent;
        CATCH(-1, PyList_SetSlice(self->_parents, 0, 0,
                                  parent_object->_parents));

        /* self._parents.append(parent) */
        CATCH(-1, PyList_Append(self->_parents, parent));

        /* parent._children[self] = True */
        CATCH(-1, PyObject_SetItem(parent_object->_children,
                                   (PyObject *)self, Py_True));

        /* self._update_cache() */
        CATCH(NULL, tmp = Compile__update_cache(self, NULL));
        Py_DECREF(tmp);
    }

    return 0;

error:
    Py_XDECREF(module);
    Py_XDECREF(WeakKeyDictionary);
    return -1;
}

static int
Compile_traverse(CompileObject *self, visitproc visit, void *arg)
{
    Py_VISIT(self->_local_dispatch_table);
    Py_VISIT(self->_local_precedence);
    Py_VISIT(self->_local_reserved_words);
    Py_VISIT(self->_dispatch_table);
    Py_VISIT(self->_precedence);
    Py_VISIT(self->_reserved_words);
    Py_VISIT(self->_children);
    Py_VISIT(self->_parents);
    return 0;
}

static int
Compile_clear(CompileObject *self)
{
    if (self->__weakreflist)
        PyObject_ClearWeakRefs((PyObject *)self);
    Py_CLEAR(self->_local_dispatch_table);
    Py_CLEAR(self->_local_precedence);
    Py_CLEAR(self->_local_reserved_words);
    Py_CLEAR(self->_dispatch_table);
    Py_CLEAR(self->_precedence);
    Py_CLEAR(self->_reserved_words);
    Py_CLEAR(self->_children);
    Py_CLEAR(self->_parents);
    return 0;
}

static void
Compile_dealloc(CompileObject *self)
{
    Compile_clear(self);
    self->ob_type->tp_free((PyObject *)self);
}

static PyObject *
Compile__update_cache(CompileObject *self, PyObject *args)
{
    PyObject *iter = NULL;
    PyObject *child = NULL;
    Py_ssize_t size;
    int i;

    /* for parent in self._parents: */
    size = PyList_GET_SIZE(self->_parents);
    for (i = 0; i != size; i++) {
        CompileObject *parent = \
            (CompileObject *)PyList_GET_ITEM(self->_parents, i);
        /* self._dispatch_table.update(parent._local_dispatch_table) */
        CATCH(-1, PyDict_Update(self->_dispatch_table,
                                parent->_local_dispatch_table));
        /* self._precedence.update(parent._local_precedence) */
        CATCH(-1, PyDict_Update(self->_precedence,
                                parent->_local_precedence));
        /* self._reserved_words.update(parent._local_reserved_words) */
        CATCH(-1, PyDict_Update(self->_reserved_words,
                                parent->_local_reserved_words));
    }
    /* self._dispatch_table.update(self._local_dispatch_table) */
    CATCH(-1, PyDict_Update(self->_dispatch_table,
                            self->_local_dispatch_table));
    /* self._precedence.update(self._local_precedence) */
    CATCH(-1, PyDict_Update(self->_precedence, self->_local_precedence));
    /* self._reserved_words.update(self._local_reserved_words) */
    CATCH(-1, PyDict_Update(self->_reserved_words,
                            self->_local_reserved_words));

    /* for child in self._children: */
    CATCH(NULL, iter = PyObject_GetIter(self->_children));
    while((child = PyIter_Next(iter))) {
        PyObject *tmp;

        /* child._update_cache() */
        CATCH(NULL, tmp = Compile__update_cache((CompileObject *)child, NULL));
        Py_DECREF(tmp);
        Py_DECREF(child);
    }
    if (PyErr_Occurred())
        goto error;
    Py_CLEAR(iter);

    Py_RETURN_NONE;

error:
    Py_XDECREF(child);
    Py_XDECREF(iter);
    return NULL;
}

static PyObject *
Compile_when(CompileObject *self, PyObject *types)
{
    PyObject *result = NULL;
    PyObject *module = PyImport_ImportModule("storm.expr");
    if (module) {
        PyObject *_when = PyObject_GetAttrString(module, "_when");
        if (_when) {
            result = PyObject_CallFunctionObjArgs(_when, self, types, NULL);
            Py_DECREF(_when);
        }
        Py_DECREF(module);
    }
    return result;
}

static PyObject *
Compile_add_reserved_words(CompileObject *self, PyObject *words)
{
    PyObject *lower_word = NULL;
    PyObject *iter = NULL;
    PyObject *word = NULL;
    PyObject *tmp;

    /* self._local_reserved_words.update((word.lower(), True)
                                         for word in words) */
    CATCH(NULL, iter = PyObject_GetIter(words));
    while ((word = PyIter_Next(iter))) {
        CATCH(NULL, lower_word = PyObject_CallMethod(word, "lower", NULL));
        CATCH(-1, PyDict_SetItem(self->_local_reserved_words,
                                 lower_word, Py_True));
        Py_CLEAR(lower_word);
        Py_DECREF(word);
    }
    if (PyErr_Occurred())
        goto error;
    Py_CLEAR(iter);

    /* self._update_cache() */
    CATCH(NULL, tmp = Compile__update_cache(self, NULL));
    Py_DECREF(tmp);

    Py_RETURN_NONE;

error:
    Py_XDECREF(lower_word);
    Py_XDECREF(word);
    Py_XDECREF(iter);
    return NULL;
}

static PyObject *
Compile_remove_reserved_words(CompileObject *self, PyObject *words)
{
    PyObject *lower_word = NULL;
    PyObject *word = NULL;
    PyObject *iter = NULL;
    PyObject *tmp;

    /* self._local_reserved_words.update((word.lower(), None)
                                         for word in words) */
    CATCH(NULL, iter = PyObject_GetIter(words));
    while ((word = PyIter_Next(iter))) {
        CATCH(NULL, lower_word = PyObject_CallMethod(word, "lower", NULL));
        CATCH(-1, PyDict_SetItem(self->_local_reserved_words,
                                 lower_word, Py_None));
        Py_CLEAR(lower_word);
        Py_DECREF(word);
    }
    if (PyErr_Occurred())
        goto error;
    Py_CLEAR(iter);

    /* self._update_cache() */
    CATCH(NULL, tmp = Compile__update_cache(self, NULL));
    Py_DECREF(tmp);

    Py_RETURN_NONE;

error:
    Py_XDECREF(lower_word);
    Py_XDECREF(word);
    Py_XDECREF(iter);
    return NULL;
}

static PyObject *
Compile_is_reserved_word(CompileObject *self, PyObject *word)
{
    PyObject *lower_word = NULL;
    PyObject *result = Py_False;
    PyObject *item;

    /* return self._reserved_words.get(word.lower()) is not None */
    CATCH(NULL, lower_word = PyObject_CallMethod(word, "lower", NULL));
    item = PyDict_GetItem(self->_reserved_words, lower_word);
    if (item == NULL && PyErr_Occurred()) {
        goto error;
    } else if (item != NULL && item != Py_None) {
        result = Py_True;
    }
    Py_DECREF(lower_word);
    Py_INCREF(result);
    return result;

error:
    Py_XDECREF(lower_word);
    return NULL;
}

staticforward PyTypeObject Compile_Type;

static PyObject *
Compile_create_child(CompileObject *self, PyObject *args)
{
    /* return self.__class__(self) */
    return PyObject_CallFunctionObjArgs((PyObject *)self->ob_type, self, NULL);
}

static PyObject *
Compile_get_precedence(CompileObject *self, PyObject *type)
{
    /* return self._precedence.get(type, MAX_PRECEDENCE) */
    PyObject *result = PyDict_GetItem(self->_precedence, type);
    if (result == NULL && !PyErr_Occurred()) {
        /* That should be MAX_PRECEDENCE, defined in expr.py */
        return PyInt_FromLong(1000);
    }
    Py_INCREF(result);
    return result;
}

static PyObject *
Compile_set_precedence(CompileObject *self, PyObject *args)
{
    Py_ssize_t size = PyTuple_GET_SIZE(args);
    PyObject *precedence = NULL;
    PyObject *tmp;
    int i;

    if (size < 2) {
        PyErr_SetString(PyExc_TypeError,
                        "set_precedence() takes at least 2 arguments.");
        return NULL;
    }

    /* for type in types: */
    precedence = PyTuple_GET_ITEM(args, 0);
    for (i = 1; i != size; i++) {
        PyObject *type = PyTuple_GET_ITEM(args, i);
        /* self._local_precedence[type] = precedence */
        CATCH(-1, PyDict_SetItem(self->_local_precedence, type, precedence));
    }

    /* self._update_cache() */
    CATCH(NULL, tmp = Compile__update_cache(self, NULL));
    Py_DECREF(tmp);

    Py_RETURN_NONE;
error:
    return NULL;
}

PyObject *
Compile_single(CompileObject *self,
               PyObject *expr, PyObject *state, PyObject *outer_precedence)
{
    PyObject *inner_precedence = NULL;
    PyObject *statement = NULL;

    /* cls = expr.__class__ */
    PyObject *cls = (PyObject *)expr->ob_type;

    /*
       dispatch_table = self._dispatch_table
       if cls in dispatch_table:
           handler = dispatch_table[cls]
       else:
    */
    PyObject *handler = PyDict_GetItem(self->_dispatch_table, cls);
    if (!handler) {
        PyObject *mro;
        Py_ssize_t size, i;

        if (PyErr_Occurred())
            goto error;

        /* for mro_cls in cls.__mro__: */
        mro = expr->ob_type->tp_mro;
        size = PyTuple_GET_SIZE(mro);
        for (i = 0; i != size; i++) {
            PyObject *mro_cls = PyTuple_GET_ITEM(mro, i);
            /*
               if mro_cls in dispatch_table:
                   handler = dispatch_table[mro_cls]
                   break
            */
            handler = PyDict_GetItem(self->_dispatch_table, mro_cls);
            if (handler)
                break;

            if (PyErr_Occurred())
                goto error;
        }
        /* else: */
        if (i == size) {
            /*
               raise CompileError("Don't know how to compile type %r of %r"
                                  % (expr.__class__, expr))
            */
            PyObject *repr = PyObject_Repr(expr);
            if (repr) {
                PyErr_Format(CompileError,
                             "Don't know how to compile type %s of %s",
                             expr->ob_type->tp_name, PyString_AS_STRING(repr));
                Py_DECREF(repr);
            }
            goto error;
        }
    }

    /*
       inner_precedence = state.precedence = \
                          self._precedence.get(cls, MAX_PRECEDENCE)
    */
    CATCH(NULL, inner_precedence = Compile_get_precedence(self, cls));
    CATCH(-1, PyObject_SetAttrString(state, "precedence", inner_precedence));

    /* statement = handler(self, expr, state) */
    CATCH(NULL, statement = PyObject_CallFunctionObjArgs(handler, self, expr,
                                                         state, NULL));

    /* if inner_precedence < outer_precedence: */
    if (PyObject_Compare(inner_precedence, outer_precedence) == -1) {
        PyObject *args, *tmp;

        if (PyErr_Occurred())
            goto error;

        /* return "(%s)" % statement */
        CATCH(NULL, args = PyTuple_Pack(1, statement));
        tmp = PyUnicode_Format(parenthesis_format, args);
        Py_DECREF(args);
        CATCH(NULL, tmp);
        Py_DECREF(statement);
        statement = tmp;
    }

    Py_DECREF(inner_precedence);

    return statement;

error:
    Py_XDECREF(inner_precedence);
    Py_XDECREF(statement);

    return NULL;
}

PyObject *
Compile_one_or_many(CompileObject *self, PyObject *expr, PyObject *state,
                    PyObject *join, int raw, int token)
{
    PyObject *outer_precedence = NULL;
    PyObject *compiled = NULL;
    PyObject *sequence = NULL;
    PyObject *statement = NULL;
    Py_ssize_t size, i;

    Py_INCREF(expr);

    /*
      expr_type = type(expr)
      if (expr_type is SQLRaw or
          raw and (expr_type is str or expr_type is unicode)):
          return expr
    */
    if ((PyObject *)expr->ob_type == SQLRaw ||
        (raw && (PyString_CheckExact(expr) || PyUnicode_CheckExact(expr)))) {
        /* Pass our reference on. */
        return expr;
    }

    /*
       if token and (expr_type is str or expr_type is unicode):
           expr = SQLToken(expr)
    */
    if (token && (PyString_CheckExact(expr) || PyUnicode_CheckExact(expr))) {
        PyObject *tmp;
        CATCH(NULL, tmp = PyObject_CallFunctionObjArgs(SQLToken, expr, NULL));
        Py_DECREF(expr);
        expr = tmp;
    }

    /*
       if state is None:
           state = State()
    */
    /* That's done in Compile__call__ just once. */

    /* outer_precedence = state.precedence */
    CATCH(NULL, outer_precedence = PyObject_GetAttrString(state, "precedence"));
    /* if expr_type is tuple or expr_type is list: */
    if (PyTuple_CheckExact(expr) || PyList_CheckExact(expr)) {
        /* compiled = [] */
        CATCH(NULL, compiled = PyList_New(0));

        /* for subexpr in expr: */
        sequence = PySequence_Fast(expr, "This can't actually fail! ;-)");
        size = PySequence_Fast_GET_SIZE(sequence);
        for (i = 0; i != size; i++) {
            PyObject *subexpr = PySequence_Fast_GET_ITEM(sequence, i);
            /*
               subexpr_type = type(subexpr)
               if subexpr_type is SQLRaw or raw and (subexpr_type is str or
                                                     subexpr_type is unicode):
            */
            if ((PyObject *)subexpr->ob_type == (PyObject *)SQLRaw ||
                (raw && (PyString_CheckExact(subexpr) ||
                         PyUnicode_CheckExact(subexpr)))) {
                /* statement = subexpr */
                Py_INCREF(subexpr);
                statement = subexpr;
            /* elif subexpr_type is tuple or subexpr_type is list: */
            } else if (PyTuple_CheckExact(subexpr) ||
                       PyList_CheckExact(subexpr)) {
                /* state.precedence = outer_precedence */
                CATCH(-1, PyObject_SetAttrString(state, "precedence",
                                                 outer_precedence));
                /* statement = self(subexpr, state, join, raw, token) */
                CATCH(NULL,
                      statement = Compile_one_or_many(self, subexpr, state,
                                                      join, raw, token));
            /* else: */
            } else {
                /*
                   if token and (subexpr_type is unicode or
                                 subexpr_type is str):
                */
                if (token && (PyUnicode_CheckExact(subexpr) ||
                              PyString_CheckExact(subexpr))) {
                    /* subexpr = SQLToken(subexpr) */
                    CATCH(NULL,
                          subexpr = PyObject_CallFunctionObjArgs(SQLToken,
                                                                 subexpr,
                                                                 NULL));
                } else {
                    Py_INCREF(subexpr);
                }

                /*
                   statement = self._compile_single(subexpr, state,
                                                    outer_precedence)
                */
                statement = Compile_single(self, subexpr, state,
                                           outer_precedence);
                Py_DECREF(subexpr);
                CATCH(NULL, statement);
            }

            /* compiled.append(statement) */
            CATCH(-1, PyList_Append(compiled, statement));
            Py_CLEAR(statement);
        }
        Py_CLEAR(sequence);

        /* statement = join.join(compiled) */
        CATCH(NULL, statement = PyUnicode_Join(join, compiled));
        Py_CLEAR(compiled);
    } else {
        /* statement = self._compile_single(expr, state, outer_precedence) */
        CATCH(NULL, statement = Compile_single(self, expr, state,
                                               outer_precedence));
    }

    /* state.precedence = outer_precedence */
    CATCH(-1, PyObject_SetAttrString(state, "precedence", outer_precedence));
    Py_CLEAR(outer_precedence);

    Py_DECREF(expr);

    return statement;

error:
    Py_XDECREF(expr);
    Py_XDECREF(outer_precedence);
    Py_XDECREF(compiled);
    Py_XDECREF(sequence);
    Py_XDECREF(statement);

    return NULL;
}

static PyObject *
Compile__call__(CompileObject *self, PyObject *args, PyObject *kwargs)
{
    static char *kwlist[] = {"expr", "state", "join", "raw", "token", NULL};
    PyObject *expr = NULL;
    PyObject *state = Py_None;
    PyObject *join;
    char raw = 0;
    char token = 0;

    PyObject *result = NULL;

    if (!initialize_globals())
        return NULL;

    join = default_compile_join;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "O|OSbb", kwlist,
                                     &expr, &state, &join, &raw, &token)) {
        return NULL;
    }

    if (state == Py_None) {
        state = PyObject_CallFunctionObjArgs(State, NULL);
    } else {
        Py_INCREF(state);
    }
    if (state) {
        result = Compile_one_or_many(self, expr, state, join, raw, token);
        Py_DECREF(state);
    }
    return result;
}


static PyMethodDef Compile_methods[] = {
    {"_update_cache", (PyCFunction)Compile__update_cache, METH_NOARGS, NULL},
    {"when", (PyCFunction)Compile_when, METH_VARARGS, NULL},
    {"add_reserved_words", (PyCFunction)Compile_add_reserved_words,
        METH_O, NULL},
    {"remove_reserved_words", (PyCFunction)Compile_remove_reserved_words,
        METH_O, NULL},
    {"is_reserved_word", (PyCFunction)Compile_is_reserved_word, METH_O, NULL},
    {"create_child", (PyCFunction)Compile_create_child, METH_NOARGS, NULL},
    {"get_precedence", (PyCFunction)Compile_get_precedence, METH_O, NULL},
    {"set_precedence", (PyCFunction)Compile_set_precedence, METH_VARARGS, NULL},
    {NULL, NULL}
};

#define OFFSETOF(x) offsetof(CompileObject, x)
static PyMemberDef Compile_members[] = {
    {"_local_dispatch_table", T_OBJECT, OFFSETOF(_local_dispatch_table), 0, 0},
    {"_local_precedence", T_OBJECT, OFFSETOF(_local_precedence), 0, 0},
    {"_local_reserved_words", T_OBJECT, OFFSETOF(_local_reserved_words), 0, 0},
    {"_dispatch_table", T_OBJECT, OFFSETOF(_dispatch_table), 0, 0},
    {"_precedence", T_OBJECT, OFFSETOF(_precedence), 0, 0},
    {"_reserved_words", T_OBJECT, OFFSETOF(_reserved_words), 0, 0},
    {"_children", T_OBJECT, OFFSETOF(_children), 0, 0},
    {"_parents", T_OBJECT, OFFSETOF(_parents), 0, 0},
    {NULL}
};
#undef OFFSETOF

statichere PyTypeObject Compile_Type = {
    PyObject_HEAD_INIT(NULL)
    0,            /*ob_size*/
    "storm.variables.Compile",    /*tp_name*/
    sizeof(CompileObject), /*tp_basicsize*/
    0,            /*tp_itemsize*/
    (destructor)Compile_dealloc, /*tp_dealloc*/
    0,            /*tp_print*/
    0,            /*tp_getattr*/
    0,            /*tp_setattr*/
    0,            /*tp_compare*/
    0,          /*tp_repr*/
    0,            /*tp_as_number*/
    0,            /*tp_as_sequence*/
    0,            /*tp_as_mapping*/
    0,                      /*tp_hash*/
    (ternaryfunc)Compile__call__, /*tp_call*/
    0,                      /*tp_str*/
    0,                      /*tp_getattro*/
    0,                      /*tp_setattro*/
    0,                      /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC, /*tp_flags*/
    0,                      /*tp_doc*/
    (traverseproc)Compile_traverse,  /*tp_traverse*/
    (inquiry)Compile_clear,          /*tp_clear*/
    0,                      /*tp_richcompare*/
    offsetof(CompileObject, __weakreflist), /*tp_weaklistoffset*/
    0,                      /*tp_iter*/
    0,                      /*tp_iternext*/
    Compile_methods,        /*tp_methods*/
    Compile_members,        /*tp_members*/
    0,                      /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    (initproc)Compile_init, /*tp_init*/
    0,                      /*tp_alloc*/
    0,                      /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};


static PyObject *
ObjectInfo__emit_object_deleted(ObjectInfoObject *self, PyObject *args)
{
    /* self.event.emit("object-deleted") */
    return PyObject_CallMethod(self->event, "emit", "s", "object-deleted");
}

static PyMethodDef ObjectInfo_deleted_callback =
    {"_emit_object_deleted", (PyCFunction)ObjectInfo__emit_object_deleted,
        METH_O, NULL};

static int
ObjectInfo_init(ObjectInfoObject *self, PyObject *args)
{
    PyObject *self_get_obj = NULL;
    PyObject *empty_args = NULL;
    PyObject *factory_kwargs = NULL;
    PyObject *columns = NULL;
    PyObject *primary_key = NULL;
    PyObject *obj;
    Py_ssize_t i;

    empty_args = PyTuple_New(0);

    CATCH(-1, PyDict_Type.tp_init((PyObject *)self, empty_args, NULL));

    CATCH(0, initialize_globals());

    if (!PyArg_ParseTuple(args, "O", &obj))
        goto error;

    /* self.cls_info = get_cls_info(type(obj)) */
    CATCH(NULL, self->cls_info = PyObject_CallFunctionObjArgs(get_cls_info,
                                                              obj->ob_type,
                                                              NULL));

    /* self.set_obj(obj) */
    CATCH(NULL, self->__obj_ref_callback =
                    PyCFunction_NewEx(&ObjectInfo_deleted_callback,
                                      (PyObject *)self, NULL));

    CATCH(NULL,
          self->__obj_ref = PyWeakref_NewRef(obj, self->__obj_ref_callback));

    /* self.event = event = EventSystem(self) */
    CATCH(NULL,
          self->event = PyObject_CallFunctionObjArgs(EventSystem, self, NULL));

    /* self->variables = variables = {} */
    CATCH(NULL, self->variables = PyDict_New());

    CATCH(NULL, self_get_obj = PyObject_GetAttrString((PyObject *)self,
                                                      "get_obj"));
    CATCH(NULL, factory_kwargs = PyDict_New());
    CATCH(-1, PyDict_SetItemString(factory_kwargs, "event", self->event));
    CATCH(-1, PyDict_SetItemString(factory_kwargs, "validator_object_factory",
                                   self_get_obj));

    /* for column in self.cls_info.columns: */
    CATCH(NULL, columns = PyObject_GetAttrString(self->cls_info, "columns"));
    for (i = 0; i != PyTuple_GET_SIZE(columns); i++) {
        /*
           variables[column] = \
               column.variable_factory(column=column,
                                       event=event,
                                       validator_object_factory=self.get_obj)
        */
        PyObject *column = PyTuple_GET_ITEM(columns, i);
        PyObject *variable, *factory;
        CATCH(-1, PyDict_SetItemString(factory_kwargs, "column", column));
        CATCH(NULL, factory = PyObject_GetAttrString(column,
                                                     "variable_factory"));
        variable = PyObject_Call(factory, empty_args, factory_kwargs);
        Py_DECREF(factory);
        CATCH(NULL, variable);
        if (PyDict_SetItem(self->variables, column, variable) == -1) {
            Py_DECREF(variable);
            goto error;
        }
        Py_DECREF(variable);
    }

    /* self.primary_vars = tuple(variables[column]
                                 for column in self.cls_info.primary_key) */
    CATCH(NULL, primary_key = PyObject_GetAttrString((PyObject *)self->cls_info,
                                                     "primary_key"));

    /* XXX Check primary_key type here. */
    CATCH(NULL,
          self->primary_vars = PyTuple_New(PyTuple_GET_SIZE(primary_key)));
    for (i = 0; i != PyTuple_GET_SIZE(primary_key); i++) {
        PyObject *column = PyTuple_GET_ITEM(primary_key, i);
        PyObject *variable = PyDict_GetItem(self->variables, column);
        Py_INCREF(variable);
        PyTuple_SET_ITEM(self->primary_vars, i, variable);
    }

    Py_DECREF(self_get_obj);
    Py_DECREF(empty_args);
    Py_DECREF(factory_kwargs);
    Py_DECREF(columns);
    Py_DECREF(primary_key);
    return 0;

error:
    Py_XDECREF(self_get_obj);
    Py_XDECREF(empty_args);
    Py_XDECREF(factory_kwargs);
    Py_XDECREF(columns);
    Py_XDECREF(primary_key);
    return -1;
}

static PyObject *
ObjectInfo_get_obj(ObjectInfoObject *self, PyObject *args)
{
    PyObject *obj = PyWeakref_GET_OBJECT(self->__obj_ref);
    Py_INCREF(obj);
    return obj;
}

static PyObject *
ObjectInfo_set_obj(ObjectInfoObject *self, PyObject *args)
{
    PyObject *obj;

    /* self._ref = ref(obj, self._emit_object_deleted) */
    if (!PyArg_ParseTuple(args, "O", &obj))
        return NULL;

    Py_DECREF(self->__obj_ref);
    self->__obj_ref = PyWeakref_NewRef(obj, self->__obj_ref_callback);
    if (!self->__obj_ref)
        return NULL;

    Py_RETURN_NONE;
}

static PyObject *
ObjectInfo_checkpoint(ObjectInfoObject *self, PyObject *args)
{
    PyObject *column, *variable, *tmp;
    Py_ssize_t i = 0;

    /* for variable in self.variables.itervalues(): */
    while (PyDict_Next(self->variables, &i, &column, &variable)) {
        /* variable.checkpoint() */
        CATCH(NULL, tmp = PyObject_CallMethod(variable, "checkpoint", NULL));
        Py_DECREF(tmp);
    }
    Py_RETURN_NONE;
error:
    return NULL;
}

static PyObject *
ObjectInfo__storm_object_info__(PyObject *self, void *closure)
{
    /* __storm_object_info__ = property(lambda self:self) */
    Py_INCREF(self);
    return self;
}

static int
ObjectInfo_traverse(ObjectInfoObject *self, visitproc visit, void *arg)
{
    Py_VISIT(self->__obj_ref);
    Py_VISIT(self->__obj_ref_callback);
    Py_VISIT(self->cls_info);
    Py_VISIT(self->event);
    Py_VISIT(self->variables);
    Py_VISIT(self->primary_vars);
    return PyDict_Type.tp_traverse((PyObject *)self, visit, arg);
}

static int
ObjectInfo_clear(ObjectInfoObject *self)
{
    Py_CLEAR(self->__obj_ref);
    Py_CLEAR(self->__obj_ref_callback);
    Py_CLEAR(self->cls_info);
    Py_CLEAR(self->event);
    Py_CLEAR(self->variables);
    Py_CLEAR(self->primary_vars);
    return PyDict_Type.tp_clear((PyObject *)self);
}

static PyObject *
ObjectInfo_richcompare(PyObject *self, PyObject *other, int op)
{
    PyObject *res;

    /* Implement equality via object identity. */
    switch (op) {
    case Py_EQ:
        res = (self == other) ? Py_True : Py_False;
        break;
    case Py_NE:
        res = (self != other) ? Py_True : Py_False;
        break;
    default:
        res = Py_NotImplemented;
    }
    Py_INCREF(res);
    return res;
}

static void
ObjectInfo_dealloc(ObjectInfoObject *self)
{
    if (self->__weakreflist)
        PyObject_ClearWeakRefs((PyObject *)self);
    Py_CLEAR(self->__obj_ref);
    Py_CLEAR(self->__obj_ref_callback);
    Py_CLEAR(self->cls_info);
    Py_CLEAR(self->event);
    Py_CLEAR(self->variables);
    Py_CLEAR(self->primary_vars);
    PyDict_Type.tp_dealloc((PyObject *)self);
}

static PyMethodDef ObjectInfo_methods[] = {
    {"_emit_object_deleted", (PyCFunction)ObjectInfo__emit_object_deleted,
        METH_O, NULL},
    {"get_obj", (PyCFunction)ObjectInfo_get_obj, METH_NOARGS, NULL},
    {"set_obj", (PyCFunction)ObjectInfo_set_obj, METH_VARARGS, NULL},
    {"checkpoint", (PyCFunction)ObjectInfo_checkpoint, METH_VARARGS, NULL},
    {NULL, NULL}
};

#define OFFSETOF(x) offsetof(ObjectInfoObject, x)
static PyMemberDef ObjectInfo_members[] = {
    {"cls_info", T_OBJECT, OFFSETOF(cls_info), 0, 0},
    {"event", T_OBJECT, OFFSETOF(event), 0, 0},
    {"variables", T_OBJECT, OFFSETOF(variables), 0, 0},
    {"primary_vars", T_OBJECT, OFFSETOF(primary_vars), 0, 0},
    {NULL}
};
#undef OFFSETOF

static PyGetSetDef ObjectInfo_getset[] = {
    {"__storm_object_info__", (getter)ObjectInfo__storm_object_info__,
        NULL, NULL},
    {NULL}
};

statichere PyTypeObject ObjectInfo_Type = {
    PyObject_HEAD_INIT(NULL)
    0,            /*ob_size*/
    "storm.info.ObjectInfo", /*tp_name*/
    sizeof(ObjectInfoObject), /*tp_basicsize*/
    0,            /*tp_itemsize*/
    (destructor)ObjectInfo_dealloc, /*tp_dealloc*/
    0,            /*tp_print*/
    0,            /*tp_getattr*/
    0,            /*tp_setattr*/
    0,            /*tp_compare*/
    0,            /*tp_repr*/
    0,            /*tp_as_number*/
    0,            /*tp_as_sequence*/
    0,            /*tp_as_mapping*/
    0,                      /*tp_hash*/
    0,                      /*tp_call*/
    0,                      /*tp_str*/
    0,                      /*tp_getattro*/
    0,                      /*tp_setattro*/
    0,                      /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT|Py_TPFLAGS_BASETYPE|Py_TPFLAGS_HAVE_GC, /*tp_flags*/
    0,                      /*tp_doc*/
    (traverseproc)ObjectInfo_traverse, /*tp_traverse*/
    (inquiry)ObjectInfo_clear, /*tp_clear*/
    ObjectInfo_richcompare, /*tp_richcompare*/
    offsetof(ObjectInfoObject, __weakreflist), /*tp_weaklistoffset*/
    0,                      /*tp_iter*/
    0,                      /*tp_iternext*/
    ObjectInfo_methods,     /*tp_methods*/
    ObjectInfo_members,     /*tp_members*/
    ObjectInfo_getset,      /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    (initproc)ObjectInfo_init, /*tp_init*/
    0,                      /*tp_alloc*/
    0,                      /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};


static PyObject *
get_obj_info(PyObject *self, PyObject *obj)
{
    PyObject *obj_info;

    if (obj->ob_type == &ObjectInfo_Type) {
        /* Much better than asking the ObjectInfo to return itself. ;-) */
        Py_INCREF(obj);
        return obj;
    }

    /* try:
          return obj.__storm_object_info__ */
    obj_info = PyObject_GetAttrString(obj, "__storm_object_info__");

    /* except AttributeError: */
    if (obj_info == NULL) {
        PyErr_Clear();

        /* obj_info = ObjectInfo(obj) */
        obj_info = PyObject_CallFunctionObjArgs((PyObject *)&ObjectInfo_Type,
                                                obj, NULL);
        if (!obj_info)
            return NULL;

        /* return obj.__dict__.setdefault("__storm_object_info__", obj_info) */
        if (PyObject_SetAttrString(obj, "__storm_object_info__",
                                   obj_info) == -1)
            return NULL;
    }

    return obj_info;
}


static PyMethodDef cextensions_methods[] = {
    {"get_obj_info", (PyCFunction)get_obj_info, METH_O, NULL},
    {NULL, NULL}
};


static int
prepare_type(PyTypeObject *type)
{
    if (!type->tp_getattro && !type->tp_getattr)
        type->tp_getattro = PyObject_GenericGetAttr;
    if (!type->tp_setattro && !type->tp_setattr)
        type->tp_setattro = PyObject_GenericSetAttr;
    if (!type->tp_alloc)
        type->tp_alloc = PyType_GenericAlloc;
    /* Don't fill in tp_new if this class has a base class */
    if (!type->tp_base && !type->tp_new)
        type->tp_new = PyType_GenericNew;
    if (!type->tp_free) {
        assert((type->tp_flags & Py_TPFLAGS_HAVE_GC) != 0);
        type->tp_free = PyObject_GC_Del;
    }
    return PyType_Ready(type);
}

DL_EXPORT(void)
initcextensions(void)
{
    PyObject *module;

    prepare_type(&EventSystem_Type);
    prepare_type(&Compile_Type);
    ObjectInfo_Type.tp_base = &PyDict_Type;
    ObjectInfo_Type.tp_hash = (hashfunc)_Py_HashPointer;
    prepare_type(&ObjectInfo_Type);
    prepare_type(&Variable_Type);

    module = Py_InitModule3("cextensions", cextensions_methods, "");
    Py_INCREF(&Variable_Type);

#define REGISTER_TYPE(name) \
    do { \
        Py_INCREF(&name##_Type); \
        PyModule_AddObject(module, #name, (PyObject*)&name##_Type); \
    } while(0)

    REGISTER_TYPE(Variable);
    REGISTER_TYPE(ObjectInfo);
    REGISTER_TYPE(Compile);
    REGISTER_TYPE(EventSystem);
}

/* vim:ts=4:sw=4:et
*/
