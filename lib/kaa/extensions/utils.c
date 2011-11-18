/*
 * ----------------------------------------------------------------------------
 * Miscellaneous low-level functions
 * ----------------------------------------------------------------------------
 * $Id: utils.c 4069 2009-05-25 15:27:14Z tack $
 * ----------------------------------------------------------------------------
 * Copyright (C) 2007-2009 Jason Tackaberry
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
#include "config.h"
#ifdef HAVE_PRCTL
#include <sys/prctl.h>
#endif

/* Python 2.5 (all point releases) have a bug with listdir on POSIX systems.
 * We include the version from 2.6 here which is fixed.  See
 * http://bugs.python.org/issue1608818
 */ 
#if PY_VERSION_HEX < 0x02060000
#   include <sys/types.h>
#   include <dirent.h>
#   define NAMLEN(dirent) strlen((dirent)->d_name)
#endif // PY_VERSION_HEX < 0x02060000

extern void Py_GetArgcArgv(int *argc, char ***argv);

PyObject *set_process_name(PyObject *self, PyObject *args)
{
#ifdef HAVE_PRCTL
    int argc, limit;
    char **argv, *name;

    if (!PyArg_ParseTuple(args, "si", &name, &limit))
        return NULL;

    Py_GetArgcArgv(&argc, &argv);
    memset(argv[0], 0, limit);
    strncpy(argv[0], name, limit-1);

    // Needed for killall
    prctl(PR_SET_NAME, argv[0], 0, 0, 0);
#endif
    Py_INCREF(Py_None);
    return Py_None;
}


/* This code (until the #endif) stripped from Python 2.6
 * Modules/posixmodule.c:posix_listdir().  This code is therefore released
 * under the PSF (http://www.python.org/psf/license/) and copyrighted by
 * the Python Software Foundation.  (The PSF license is, to the best of my
 * Googling, compatible with the LGPL.)
 */
#if PY_VERSION_HEX < 0x02060000
static PyObject *
posix_error_with_allocated_filename(char* name)
{
    PyObject *rc = PyErr_SetFromErrnoWithFilename(PyExc_OSError, name);
    PyMem_Free(name);
    return rc;
}

PyObject *listdir(PyObject *self, PyObject *args)
{
    char *name = NULL;
    PyObject *d, *v;
    DIR *dirp;
    struct dirent *ep;
    int arg_is_unicode = 1;

    errno = 0;
    if (!PyArg_ParseTuple(args, "U:listdir", &v)) {
        arg_is_unicode = 0;
        PyErr_Clear();
    }
    if (!PyArg_ParseTuple(args, "et:listdir", Py_FileSystemDefaultEncoding, &name))
        return NULL;
    if ((dirp = opendir(name)) == NULL) {
        return posix_error_with_allocated_filename(name);
    }
    if ((d = PyList_New(0)) == NULL) {
        closedir(dirp);
        PyMem_Free(name);
        return NULL;
    }
    for (;;) {
        errno = 0;
        Py_BEGIN_ALLOW_THREADS
        ep = readdir(dirp);
        Py_END_ALLOW_THREADS
        if (ep == NULL) {
            if (errno == 0) {
                break;
            } else {
                closedir(dirp);
                Py_DECREF(d);
                return posix_error_with_allocated_filename(name);
            }
        }
        if (ep->d_name[0] == '.' &&
            (NAMLEN(ep) == 1 ||
             (ep->d_name[1] == '.' && NAMLEN(ep) == 2)))
            continue;
        v = PyString_FromStringAndSize(ep->d_name, NAMLEN(ep));
        if (v == NULL) {
            Py_DECREF(d);
            d = NULL;
            break;
        }
#ifdef Py_USING_UNICODE
        if (arg_is_unicode) {
            PyObject *w;

            w = PyUnicode_FromEncodedObject(v,
                    Py_FileSystemDefaultEncoding,
                    "strict");
            if (w != NULL) {
                Py_DECREF(v);
                v = w;
            }
            else {
                /* fall back to the original byte string, as
                   discussed in patch #683592 */
                PyErr_Clear();
            }
        }
#endif
        if (PyList_Append(d, v) != 0) {
            Py_DECREF(v);
            Py_DECREF(d);
            d = NULL;
            break;
        }
        Py_DECREF(v);
    }
    closedir(dirp);
    PyMem_Free(name);

    return d;
}
#endif // PY_VERSION_HEX < 0x02060000

PyMethodDef utils_methods[] = {
    {"set_process_name",  set_process_name, METH_VARARGS },
#if PY_VERSION_HEX < 0x02060000
    {"listdir",  listdir, METH_VARARGS },
#endif // PY_VERSION_HEX < 0x02060000
    { NULL }
};

void init_utils(void)
{
    Py_InitModule("_utils", utils_methods);
}
