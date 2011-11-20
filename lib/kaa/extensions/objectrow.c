/*
 * ----------------------------------------------------------------------------
 * objectrow for pysqlite used in kaa.db
 * ----------------------------------------------------------------------------
 * $Id: objectrow.c 4069 2009-05-25 15:27:14Z tack $
 *
 * ----------------------------------------------------------------------------
 * Copyright (C) 2006-2009 Jason Tackaberry
 *
 * Please see the file AUTHORS for a complete list of authors.
 *
 * This library is free software; you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License version
 * 2.1 as published by the Free Software Foundation.
 *
 * This library is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
 * 02110-1301 USA
 *
 * ----------------------------------------------------------------------------
 */

#include "Python.h"
#include <glib.h>
#include "structmember.h"

#define ATTR_SIMPLE              0x01
#define ATTR_INDEXED             0x04
#define ATTR_IGNORE_CASE         0x08
#define ATTR_INDEXED_IGNORE_CASE (ATTR_INDEXED | ATTR_IGNORE_CASE)
#define IS_ATTR_INDEXED_IGNORE_CASE(attr) ((attr & ATTR_INDEXED_IGNORE_CASE) == ATTR_INDEXED_IGNORE_CASE)

#if PY_VERSION_HEX < 0x02050000
typedef int Py_ssize_t;
#define PY_SSIZE_T_MAX INT_MAX
#define PY_SSIZE_T_MIN INT_MIN
typedef Py_ssize_t (*lenfunc)(PyObject *);
#endif

GHashTable *queries = 0;
PyObject *cPickle_loads, *zip;


typedef struct {
    int refcount,
        pickle_idx;
    GHashTable *idxmap,
                *type_names;  // maps type id to type name
} QueryInfo;

typedef struct {
    int index,       // Index in the sql row for this attribute, or -1 if none
        pickled,     // If we need to look in the pickle for this attribute.
        flags;       // Attribute flags from kaa.Database definition.
    PyObject *type;  // Type object for this attribute
} ObjectAttribute;

typedef struct {
    PyObject_HEAD
    PyObject *desc,         // Cursor description for this row
             *row,          // Row tuple from sqlite
             *db,           // Weakref to kaa.db.Database instance
             *object_types, // Object types dict from Database instance
             *attrs,        // Dict of attributes for this type
             *type_name,    // String object of object type name
             *pickle,       // Dict of pickled attributes.
             *keys,         // Available attribute names
             *parent;       // Tuple (parent_name, parent_id)
    QueryInfo *query_info;
    int unpickled,
        has_pickle;
} ObjectRow_PyObject;


PyObject *ObjectRow_PyObject__keys(ObjectRow_PyObject *, PyObject *, PyObject *);
PyObject *ObjectRow_PyObject__items(ObjectRow_PyObject *, PyObject *, PyObject *);

int ObjectRow_PyObject__init(ObjectRow_PyObject *self, PyObject *args, PyObject *kwargs)
{
    PyObject *cursor, *row, *o_type, *pickle_dict = 0;
    if (!PyArg_ParseTuple(args, "OO|O", &cursor, &row, &pickle_dict))
        return -1;

    if (pickle_dict) {
        /* If row or cursor weren't specified, then we require the third arg
         * (pickle_dict) be a dictionary, and we basically pass behave as this
         * dict.  We do this for example from Database.add_object()
         */
        if (pickle_dict == 0 || !PyDict_Check(pickle_dict)) {
            PyErr_Format(PyExc_ValueError, "pickle dict must be specified when cursor or row is None");
            return -1;
        }
        self->pickle = pickle_dict;
        Py_INCREF(self->pickle);
        self->row = Py_None;
        Py_INCREF(self->row);
        self->desc = Py_None;
        Py_INCREF(self->desc);
        return 0;
    }

    if (PyTuple_Check(cursor)) {
        self->desc = PySequence_GetItem(cursor, 0); // new ref
        self->object_types = PySequence_GetItem(cursor, 1); // new ref
    } else if (!PyObject_HasAttrString(cursor, "_db")) {
        PyErr_Format(PyExc_ValueError, "First argument is not a Cursor or tuple object");
        return -1;
    } else {
        PyObject *weak_db = PyObject_GetAttrString(cursor, "_db"); // new ref
        PyObject *db = PyWeakref_GetObject(weak_db); // borrowed ref
        self->object_types = PyObject_GetAttrString(db, "_object_types"); // new ref
        self->desc = PyObject_GetAttrString(cursor, "description"); // new ref
        Py_XDECREF(weak_db);
    }

    self->row = row;

    self->type_name = PySequence_GetItem(row, 0); // new ref
    if (!PyString_Check(self->type_name) && !PyUnicode_Check(self->type_name)) {
        Py_XDECREF(self->desc);
        Py_XDECREF(self->object_types);
        PyErr_Format(PyExc_ValueError, "First element of row must be object type");
        return -1;
    }

    o_type = PyDict_GetItem(self->object_types, self->type_name); // borrowed ref
    self->attrs = PySequence_GetItem(o_type, 1); // new ref
    if (!self->attrs) {
        Py_XDECREF(self->desc);
        Py_XDECREF(self->object_types);
        PyErr_Format(PyExc_ValueError, "Object type '%s' not defined.", PyString_AsString(self->type_name));
        return -1;
    }

    self->query_info = g_hash_table_lookup(queries, self->desc);
    if (!self->query_info) {
        /* This is a row for a query we haven't seen before, so we need to do
         * some initial setup.  Most of what we do here is convert data stored
         * in Python objects to more native C types for faster access.
         */

        PyObject **desc_tuple = PySequence_Fast_ITEMS(self->desc);
        PyObject *key, *value;
        int i = 0;
        Py_ssize_t pos = 0;

        self->query_info = (QueryInfo *)malloc(sizeof(QueryInfo));
        self->query_info->refcount = 0;
        self->query_info->pickle_idx = -1;
        self->query_info->idxmap = g_hash_table_new_full(g_str_hash, g_str_equal, free, free);

        /* Iterate over the columns from the SQL query and keep track of
         * attribute names and their indexes within the row tuple.  Start at
         * index 2 because index 0 and 1 are internal (the object type name
         * literal and type id).
         */
        for (i = 2; i < PySequence_Length(self->desc); i++) {
            PyObject **desc_col = PySequence_Fast_ITEMS(desc_tuple[i]);
            char *skey = PyString_AsString(desc_col[0]);
            ObjectAttribute *attr = (ObjectAttribute *)malloc(sizeof(ObjectAttribute));

            attr->pickled = 0;
            attr->index = i;
            if (!strcmp(skey, "pickle"))
                self->query_info->pickle_idx = i;

            g_hash_table_insert(self->query_info->idxmap, g_strdup(skey), (void *)attr);
        }

        /* Now iterate over the kaa.db object attribute dict, storing the
         * type of each attribute, its flags, and figure out whether or not
         * we need to look in the pickle for that attribute.
         */
        while (PyDict_Next(self->attrs, &pos, &key, &value)) {
            char *skey = PyString_AsString(key);
            ObjectAttribute *attr = g_hash_table_lookup(self->query_info->idxmap, skey);

            if (!attr) {
                attr = (ObjectAttribute *)malloc(sizeof(ObjectAttribute));
                attr->index = -1;
                g_hash_table_insert(self->query_info->idxmap, g_strdup(skey), (void *)attr);
            }
            attr->type = PySequence_Fast_GET_ITEM(value, 0);
            attr->flags = PyInt_AsLong(PySequence_Fast_GET_ITEM(value, 1));
            if (IS_ATTR_INDEXED_IGNORE_CASE(attr->flags) || attr->flags & ATTR_SIMPLE)
                // attribute is set to ignore case, or it's ATTR_SIMPLE, so we
                // need to look in the pickle for this attribute.
                attr->pickled = 1;
            else
                attr->pickled = 0;

        }

        /* Create a hash table that maps object type ids to type names.
         */
        pos = 0;
        self->query_info->type_names = g_hash_table_new_full(g_direct_hash, g_direct_equal, NULL, free);
        while (PyDict_Next(self->object_types, &pos, &key, &value)) {
            PyObject *type_id = PySequence_Fast_GET_ITEM(value, 0);
            char *skey = PyString_AsString(key);
            g_hash_table_insert(self->query_info->type_names, (void *)PyInt_AsLong(type_id), g_strdup(skey));
        }
        g_hash_table_insert(queries, self->desc, self->query_info);
    }

    self->query_info->refcount++;
    if (self->query_info->pickle_idx >= 0) {
        // Pickle column included in row.  Set _pickle member to True which
        // indicates the pickle data was fetched, but just hasn't yet been
        // unpickled.
        if (PySequence_Fast_GET_ITEM(self->row, self->query_info->pickle_idx) != Py_None)
            self->has_pickle = 1;
        self->pickle = Py_True;
    } else
        self->pickle = Py_False;

    Py_INCREF(self->pickle);
    Py_INCREF(self->row);

    if (pickle_dict && pickle_dict != Py_None) {
        Py_DECREF(self->pickle);
        self->pickle = pickle_dict;
        Py_INCREF(self->pickle);
        self->has_pickle = self->unpickled = 1;
    }
    return 0;
}

void ObjectRow_PyObject__dealloc(ObjectRow_PyObject *self)
{
    if (self->query_info) {
        self->query_info->refcount--;
        if (self->query_info->refcount <= 0) {
            g_hash_table_remove(queries, self->desc);
            g_hash_table_destroy(self->query_info->idxmap);
            g_hash_table_destroy(self->query_info->type_names);
            free(self->query_info);
        }
    }
    Py_XDECREF(self->object_types);
    Py_XDECREF(self->type_name);
    Py_XDECREF(self->desc);
    Py_XDECREF(self->row);
    Py_XDECREF(self->pickle);
    Py_XDECREF(self->attrs);
    Py_XDECREF(self->keys);
    Py_XDECREF(self->parent);

    self->ob_type->tp_free((PyObject*)self);
}

int do_unpickle(ObjectRow_PyObject *self)
{
    PyObject *result;
    if (!self->has_pickle) {
        PyErr_Format(PyExc_KeyError, "Attribute exists but row pickle is not available");
        return 0;
    }
    PyObject *pickle_str = PyObject_Str(PySequence_Fast_GET_ITEM(self->row, self->query_info->pickle_idx));
    PyObject *args = Py_BuildValue("(O)", pickle_str);
    result = PyEval_CallObject(cPickle_loads, args);
    Py_DECREF(args);
    Py_DECREF(pickle_str);

    if (!result) {
        self->has_pickle = 0;
        return 0;
    }
    Py_DECREF(self->pickle);
    self->pickle = result;
    self->unpickled = 1;
    return 1;
}

static inline PyObject *
convert(ObjectRow_PyObject *self, ObjectAttribute *attr, PyObject *value)
{
    if (attr->type == (PyObject *)&PyString_Type && value != Py_None)  {
        /* Attributes of type 'str' are stored as buffers in sqlite, so we
         * convert back to str here.
         */
        return PyObject_Str(value);
    }

    Py_INCREF(value);
    return value;
}

PyObject *ObjectRow_PyObject__subscript(ObjectRow_PyObject *self, PyObject *key)
{
    char *skey = 0,
          skey2[80]; // we'll have a problem if attributes are >= 78 chars :)
    ObjectAttribute *attr = 0;
    PyObject *value;

    if (!self->query_info) {
        // If no query_info available, then we work strictly from the pickle
        // dict, which init() requires be available.
        value = PyDict_GetItem(self->pickle, key);
        if (!value) {
            PyErr_SetObject(PyExc_KeyError, key);
            return NULL;
        }
        Py_INCREF(value);
        return value;
    }

    // String is the more common case.
    if (PyString_Check(key)) {
        skey = PyString_AsString(key);

        // Handle some special case attribute names.
        if (!strcmp(skey, "type")) {
            // Returns the type name of this object.
            Py_INCREF(self->type_name);
            return self->type_name;

        } else if (!strcmp(skey, "parent")) {
            /* Returns a tuple (type_name, id) for this object's parent.  If
             * type_name can't be resolved from the parent_id, then the integer
             * value for the type is used instead.
             */

            if (!self->parent) {
                // Generate the value if it's not available.
                ObjectAttribute *type_attr, *id_attr;
                PyObject *o_type, *o_id;
                char *type_name = 0;

                // Lookup the parent_type and parent_id indexes within the
                // sql row.
                type_attr = g_hash_table_lookup(self->query_info->idxmap, "parent_type");
                id_attr = g_hash_table_lookup(self->query_info->idxmap, "parent_id");
                // If neither of these values are available in the row, raise an
                // exception.
                if (!type_attr || !id_attr || type_attr->index == -1 || id_attr->index == -1) {
                    PyErr_Format(PyExc_IndexError, "Parent attribute not available.");
                    return NULL;
                }
                // They're both available, so fetch them.
                o_type = PySequence_Fast_GET_ITEM(self->row, type_attr->index);
                o_id = PySequence_Fast_GET_ITEM(self->row, id_attr->index);
                // Resolve type id to type name.
                if (PyNumber_Check(o_type))
                    type_name = g_hash_table_lookup(self->query_info->type_names, (void *)PyLong_AsLong(o_type));
                // Construct the (name, id) tuple.
                if (type_name)
                    self->parent = Py_BuildValue("(sO)", type_name, o_id);
                else
                    self->parent = Py_BuildValue("(OO)", o_type, o_id);
            }

            Py_INCREF(self->parent);
            return self->parent;
        }
        else if (!strcmp(skey, "_row")) {
            Py_INCREF(self->row);
            return(self->row);
        }

        attr = g_hash_table_lookup(self->query_info->idxmap, skey);
    }
    // But also support referencing the sql row by index.  (Pickled attributes
    // cannot be accessed this way, though.)
    else if (PyNumber_Check(key)) {
        long index = -1;
        if (PyInt_Check(key))
            index = PyInt_AsLong(key);
        else if (PyLong_Check(key))
            index = PyLong_AsLong(key);

        if (index < 0 || index >= PySequence_Length(self->row)) {
            PyErr_Format(PyExc_IndexError, "index out of range");
            return NULL;
        }
        return PySequence_GetItem(self->row, index);
    }

    //printf("REQUEST: %s attr=%p idx=%d has_pickle=%d pickle_idx=%d\n", skey, attr, attr->index, self->has_pickle, self->query_info->pickle_idx);

    if (attr && attr->index == -1 && !self->has_pickle && self->query_info->pickle_idx != -1) {
        /* Attribute is valid and pickle column exists in sql row, but pickle
         * is None, which means this attribute was never assigned a value, so
         * return None.
         */
         Py_INCREF(Py_None);
         return Py_None;
    }

    /* Raise exception if attribute name isn't known, or if the requested
     * attribute, while valid for this object type, can't be obtained given the
     * query that was done.
     */
    if (!attr || (attr->index == -1 && !self->has_pickle && attr->pickled)) {
        PyErr_SetObject(PyExc_KeyError, key);
        return NULL;
    }

    if (!attr->pickled || (IS_ATTR_INDEXED_IGNORE_CASE(attr->flags) && attr->index >= 0 && !self->has_pickle))
        /* If the attribute isn't pickled, we return the value from the row
         * tuple.  Also, if the attribute is ATTR_INDEXED_IGNORE_CASE but we
         * don't have a pickle available, and that attribute exists in the
         * row tuple, return what we have.
         */
        return convert(self, attr, PySequence_Fast_GET_ITEM(self->row, attr->index));

    // If we need to check the pickle but haven't unpickled, do so now.
    if (!self->unpickled && !do_unpickle(self))
        return NULL;

    if (IS_ATTR_INDEXED_IGNORE_CASE(attr->flags)) {
        // ATTR_INDEXED_IGNORE_CASE, these attributes are prefixed with __ in
        // the pickled dict.
        snprintf(skey2, sizeof(skey2)-1, "__%s", skey);
        skey = skey2;
    }

    value = PyDict_GetItemString(self->pickle, skey);
    if (!value)
        // Attribute isn't stored in pickle, which means it's None.
        value = Py_None;

    return convert(self, attr, value);
}

PyObject *ObjectRow_PyObject__str(ObjectRow_PyObject *self)
{
    PyObject *dict, *items, *str;
    items = ObjectRow_PyObject__items(self, NULL, NULL);
    dict = PyDict_New();
    PyDict_MergeFromSeq2(dict, items, 1);
    str = PyObject_Str(dict);
    Py_DECREF(items);
    Py_DECREF(dict);
    return str;
}

Py_ssize_t ObjectRow_PyObject__length(ObjectRow_PyObject *self)
{
    PyObject *keys = ObjectRow_PyObject__keys(self, NULL, NULL);
    Py_DECREF(keys);
    return PySequence_Length(self->keys);
}

void attrs_iter(gpointer key, ObjectAttribute *attr, ObjectRow_PyObject *self)
{
    if (attr->index >= 0 || (attr->pickled && self->query_info->pickle_idx >= 0)) {
        PyObject *o;

        if (!strcmp(key, "pickle"))
            return;

        o = PyString_FromString(key);
        PyList_Append(self->keys, o);
        Py_DECREF(o);
    }
}


PyObject *ObjectRow_PyObject__keys(ObjectRow_PyObject *self, PyObject *args, PyObject *kwargs)
{
    PyObject *key, *parent_type, *parent_id;

    if (!self->query_info)
        // No query_info means we work just from pickle dict.
        return PyMapping_Keys(self->pickle);

    if (self->keys) {
        Py_INCREF(self->keys);
        return self->keys;
    }

    self->keys = PyList_New(0);
    key = PyString_FromString("type");
    PyList_Append(self->keys, key);
    Py_DECREF(key);

    g_hash_table_foreach(self->query_info->idxmap, (GHFunc)attrs_iter, self);

    parent_type = PyString_FromString("parent_type");
    parent_id = PyString_FromString("parent_id");
    if (PySequence_Contains(self->keys, parent_type) && PySequence_Contains(self->keys, parent_id)) {
        key = PyString_FromString("parent");
        PyList_Append(self->keys, key);
        Py_DECREF(key);
    }
    Py_DECREF(parent_type);
    Py_DECREF(parent_id);

    Py_INCREF(self->keys);
    return self->keys;
}

PyObject *ObjectRow_PyObject__values(ObjectRow_PyObject *self, PyObject *args, PyObject *kwargs)
{
    PyObject *keys, *values;
    int i;

    if (!self->query_info)
        // No query_info means we work just from pickle dict.
        return PyMapping_Values(self->pickle);

    if (self->has_pickle && !self->unpickled && !do_unpickle(self))
        PyErr_Clear();

    keys = ObjectRow_PyObject__keys(self, NULL, NULL);
    values = PyList_New(0);
    for (i = 0; i < PySequence_Length(keys); i++) {
        PyObject *key = PySequence_Fast_GET_ITEM(keys, i);
        PyObject *value = ObjectRow_PyObject__subscript(self, key);
        PyList_Append(values, value);
        Py_DECREF(value);
    }
    Py_DECREF(keys);
    return values;
}

PyObject *ObjectRow_PyObject__items(ObjectRow_PyObject *self, PyObject *args, PyObject *kwargs)
{
    PyObject *keys, *values, *zargs, *items;
    keys = ObjectRow_PyObject__keys(self, NULL, NULL);
    values = ObjectRow_PyObject__values(self, NULL, NULL);
    zargs = Py_BuildValue("(OO)", keys, values);
    items = PyEval_CallObject(zip, zargs);

    Py_DECREF(zargs);
    Py_DECREF(values);
    Py_DECREF(keys);
    return items;
}

PyObject *ObjectRow_PyObject__get(ObjectRow_PyObject *self, PyObject *args, PyObject *kwargs)
{
    PyObject *key, *value, *def = Py_None;
    if (!PyArg_ParseTuple(args, "O|O", &key, &def))
        return NULL;
    value = ObjectRow_PyObject__subscript(self, key);
    if (!value) {
        PyErr_Clear();
        Py_INCREF(def);
        return def;
    }
    return value;
}

PyObject *ObjectRow_PyObject__has_key(ObjectRow_PyObject *self, PyObject *args, PyObject *kwargs)
{
    PyObject *key, *keys;
    int has_key;
    if (!PyArg_ParseTuple(args, "O", &key))
        return NULL;
    keys = ObjectRow_PyObject__keys(self, NULL, NULL);
    has_key = PySequence_Contains(keys, key);
    Py_DECREF(keys);
    return PyBool_FromLong(has_key);
}


PyMappingMethods row_as_mapping = {
    /* mp_length        */ (lenfunc)ObjectRow_PyObject__length,
    /* mp_subscript     */ (binaryfunc)ObjectRow_PyObject__subscript,
    /* mp_ass_subscript */ (objobjargproc)0,
};

PyMethodDef ObjectRow_PyObject_methods[] = {
    {"keys", (PyCFunction) ObjectRow_PyObject__keys, METH_VARARGS },
    {"values", (PyCFunction) ObjectRow_PyObject__values, METH_VARARGS },
    {"items", (PyCFunction) ObjectRow_PyObject__items, METH_VARARGS },
    {"get", (PyCFunction) ObjectRow_PyObject__get, METH_VARARGS },
    {"has_key", (PyCFunction) ObjectRow_PyObject__has_key, METH_VARARGS },
    {NULL, NULL}
};

static PyMemberDef ObjectRow_PyObject_members[] = {
    {"_row", T_OBJECT_EX, offsetof(ObjectRow_PyObject, row), 0, "pysqlite row"},
    {"_description", T_OBJECT_EX, offsetof(ObjectRow_PyObject, desc), 0, "pysqlite cursor description"},
    {"_pickle", T_OBJECT_EX, offsetof(ObjectRow_PyObject, pickle), 0, "Unpickled dictionary"},
    {"_object_types", T_OBJECT_EX, offsetof(ObjectRow_PyObject, object_types), 0, "Database object types"},
    {NULL}
};


PyTypeObject ObjectRow_PyObject_Type = {
    PyObject_HEAD_INIT(NULL)
    0,                          /* ob_size */
    "kaa.db.ObjectRow",                /* tp_name */
    sizeof(ObjectRow_PyObject),  /* tp_basicsize */
    0,                          /* tp_itemsize */
    (destructor) ObjectRow_PyObject__dealloc,        /* tp_dealloc */
    0,                          /* tp_print */
    0,                          /* tp_getattr */
    0,                          /* tp_setattr */
    0,                          /* tp_compare */
    0,                          /* tp_repr */
    0,                          /* tp_as_number */
    0,                          /* tp_as_sequence */
    &row_as_mapping,            /* tp_as_mapping */
    0,                          /* tp_hash */
    0,                          /* tp_call */
    (reprfunc)ObjectRow_PyObject__str, /* tp_str */
    0,                          /* tp_getattro */
    0,                          /* tp_setattro */
    0,                          /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, // | Py_TPFLAGS_HAVE_GC, /* tp_flags */
    "ObjectRow Object",         /* tp_doc */
    0,                          /* tp_traverse */
    0,                          /* tp_clear */
    0,                          /* tp_richcompare */
    0,                          /* tp_weaklistoffset */
    0,                          /* tp_iter */
    0,                          /* tp_iternext */
    ObjectRow_PyObject_methods, /* tp_methods */
    ObjectRow_PyObject_members, /* tp_members */
    0,                          /* tp_getset */
    0,                          /* tp_base */
    0,                          /* tp_dict */
    0,                          /* tp_descr_get */
    0,                          /* tp_descr_set */
    0,                          /* tp_dictoffset */
    (initproc)ObjectRow_PyObject__init, /* tp_init */
    0,                          /* tp_alloc */
    PyType_GenericNew,          /* tp_new */
};

PyMethodDef objectrow_methods[] = {
    {NULL}
};

void init_objectrow(void)
{
    PyObject *m;
    m = Py_InitModule("_objectrow", objectrow_methods);

    if (PyType_Ready(&ObjectRow_PyObject_Type) >= 0) {
        Py_INCREF(&ObjectRow_PyObject_Type);
        PyModule_AddObject(m, "ObjectRow", (PyObject *)&ObjectRow_PyObject_Type);
    }
    queries = g_hash_table_new(g_direct_hash, g_direct_equal);

    m = PyImport_ImportModule("cPickle");
    cPickle_loads = PyObject_GetAttrString(m, "loads");
    Py_DECREF(m);

    m = PyImport_ImportModule("__builtin__");
    zip = PyObject_GetAttrString(m, "zip");
    Py_DECREF(m);
}
