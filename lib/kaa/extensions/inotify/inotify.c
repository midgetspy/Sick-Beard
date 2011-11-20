/*
 * ----------------------------------------------------------------------------
 * Inotify module for Python
 * ----------------------------------------------------------------------------
 * $Id: inotify.c 4069 2009-05-25 15:27:14Z tack $
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

#include <Python.h>
#include "config.h"

#include <inttypes.h>

#ifdef USE_FALLBACK
#   include "fallback-inotify.h"
#   include "fallback-inotify-syscalls.h"
#else
#   include <sys/inotify.h>
#endif

PyObject *init(PyObject *self, PyObject *args)
{
    int fd = inotify_init();
    if (fd == -1)
	perror("inotify_init");
    return Py_BuildValue("i", fd);
}

PyObject *add_watch(PyObject *self, PyObject *args)
{
    int fd;
    uint32_t mask;
    char *name;

    if (!PyArg_ParseTuple(args, "isi", &fd, &name, &mask))
        return NULL;

    return Py_BuildValue("i", inotify_add_watch(fd, name, mask));
}

PyObject *rm_watch(PyObject *self, PyObject *args)
{
    int fd;
    uint32_t wd;

    if (!PyArg_ParseTuple(args, "ii", &fd, &wd))
        return NULL;

    return Py_BuildValue("i", inotify_rm_watch(fd, wd));
}


PyMethodDef inotify_methods[] = {
    { "init", init, METH_VARARGS },
    { "add_watch", add_watch, METH_VARARGS },
    { "rm_watch", rm_watch, METH_VARARGS },
    { NULL }
};


void init_inotify(void)
{
    PyObject *m = Py_InitModule("_inotify", inotify_methods);
    #define add_const(x) PyModule_AddObject(m, #x, PyLong_FromLong(IN_ ## x));
    add_const(ACCESS);
    add_const(MODIFY);
    add_const(ATTRIB);
    add_const(CLOSE_WRITE);
    add_const(CLOSE_NOWRITE);
    add_const(CLOSE);
    add_const(OPEN);
    add_const(MOVED_FROM);
    add_const(MOVED_TO);
    add_const(MOVE);
    add_const(CREATE);
    add_const(DELETE);
    add_const(DELETE_SELF);
    add_const(MOVE_SELF);
    add_const(UNMOUNT);
    add_const(Q_OVERFLOW);
    add_const(IGNORED);
    add_const(ISDIR);
    add_const(ONESHOT);
    add_const(ALL_EVENTS);
}
