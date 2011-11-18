/****************************************************************************
 *
 * « shmmodule.c © 1997, 1998 by INRIA. All rights reserved.
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the "Software"),
 * to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense,
 * and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THIS SOFTWARE IS PROVIDED "AS IS" AND ANY WARRANTIES, EXPRESS OR IMPLIED,
 * INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
 * AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
 *
 * IN NO EVENT SHALL THE INRIA OR THE AUTHORS BE LIABLE FOR ANY DIRECT,
 * INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES,
 * INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES,
 * LOSS OF USE, DATA, OR PROFITS OR BUSINESS INTERRUPTION, HOWEVER CAUSED AND
 * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT,
 * INCLUDING NEGLIGENCE OR OTHERWISE, ARISING IN ANY WAY OUT OF THE USE OF
 * THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. »
 *
 ***************************************************************************/
/*
 *  If you have questions regarding this software, contact:
 *  Vladimir Marangozov, Vladimir.Marangozov@inrialpes.fr
 *  INRIA Rhône-Alpes, SIRAC project, 655 avenue de l'Europe
 *  38330 Montbonnot St. Martin, France.
 */


/* Python Shared Memory module */

/*
  This module provides an interface to System V shared memory IPC.


Module interface:

- shm.create_memory(int Key, int Size [,int Perm=0666]) --> object
- shm.create_semaphore(int Key [,int Value=1 [,int Perm=0666]]) --> object
- shm.error
- shm.ftok(string Path, int ProjId) --> int
- shm.getsemid(int Key) --> int
- shm.getshmid(int Key) --> int
- shm.memory(int Shmid) --> object
- shm.memory_haskey(int Key) --> int
- shm.remove_memory(int Shmid) --> None
- shm.remove_semaphore(int Semid) --> None
- shm.semaphore(int Semid) --> object
- shm.semaphore_haskey(int Key) --> int

Memory Objects:

+ Members:

- m.addr	- attachment address in the process address space
- m.attached	- 0|1
- m.cgid	- gid of creator
- m.cpid	- pid of creator
- m.cuid	- uid of creator
- m.gid		- gid of owner
- m.key		- segment key or IPC_PRIVATE (=0)
- m.lpid	- pid of last shmop
- m.nattch	- current # of attached processes
- m.perm	- operation permission
- m.shmid	- shared memory segment id
- m.size	- segment size
- m.uid		- uid of owner

+ Methods:

- m.attach([int Addr=0 [,int How=0]]) --> None
- m.detach() --> None
- m.read(int Nbytes [,int Offset=0]) --> string
- m.setgid(int Gid) --> None
- m.setperm(int Perm) --> None
- m.setuid(int Uid) --> None
- m.write(string Data [,int Offset=0]) --> None

Semaphore Objects:

+ Members:

- s.cgid	- gid of creator
- s.cuid	- uid of creator
- s.gid		- gid of owner
- s.key		- semaphore key or IPC_PRIVATE (=0)
- s.lpid	- pid of last semop
- s.ncnt	- current # of processes waiting for s.val > 0
- s.perm	- operation permission
- s.semid	- semaphore id
- s.uid		- uid of owner
- s.val		- value of the semaphore counter
- s.zcnt	- current # of processes waiting for s.val == 0

+ Methods:

- s.P() --> None		- blocks if s.val == 0; decrements s.val
- s.V() --> None		- increments s.val
- s.Z() --> None		- blocks until s.val == 0
- s.setblocking(0|1) --> None
- s.setgid(int Gid) --> None
- s.setperm(int Perm) --> None
- s.setuid(int Uid) --> None
- s.setundo(0|1) --> None
- s.setval(int Value) --> None

*/

/* Uncomment the following line if <sys/sem.h> defines "union semun" */

/* #define HAVE_UNION_SEMUN */

/* ------------------------------------------------------------------------- */
#include "Python.h"
#include "structmember.h"

#include <sys/types.h>
#include <sys/ipc.h>		/* for system's IPC_xxx definitions */
#include <sys/shm.h>		/* for shmget, shmat, shmdt, shmctl */
#include <sys/sem.h>		/* for semget, semctl, semop */

#if defined(__GLIBC__)
#define key __key
#endif /* __GLIBC__ */

/*
-- Exception type for errors detected by this module.
*/

static PyObject *PyShm_Error;

/*
-- Convenience function to raise an error according to errno.
*/

static PyObject *
PyShm_Err(void)
{
    return PyErr_SetFromErrno(PyShm_Error);
}

/*
-- The object holding a shared memory segment
*/

typedef struct {
    PyObject_HEAD
    int shmid;			/* shared memory id	*/
    int mode;			/* attachment mode	*/
    void *addr;			/* shmseg start address	*/
    struct shmid_ds ds;		/* data structure	*/
} PyShmMemoryObject;

staticforward PyTypeObject	PyShmMemory_Type;

#define PyShmObj		PyShmMemoryObject
#define PyShmMemory_Check(op)	((op)->ob_type == &PyShmMemory_Type)

/*
-- The object holding a semaphore
*/

typedef struct {
    PyObject_HEAD
    int semid;			/* semaphore id		*/
    short opflag;		/* IPC_NOWAIT, SEM_UNDO	*/
    struct semid_ds ds;		/* data structure	*/
} PyShmSemaphoreObject;

#ifndef HAVE_UNION_SEMUN
union semun {
    int val;                    /* used for SETVAL only */
    struct semid_ds *buf;       /* for IPC_STAT and IPC_SET */
    unsigned short *array;      /* used for GETALL and SETALL */
};
#endif

typedef union semun semctl_arg;

staticforward PyTypeObject	PyShmSemaphore_Type;

#define PyShmSemObj		PyShmSemaphoreObject
#define PyShmSemaphore_Check(op) ((op)->ob_type == &PyShmSemaphore_Type)

/*
-- Internal dictionaries for Python memory and semaphore objects
*/

static PyObject *shm_dict = NULL;
static PyObject *sem_dict = NULL;

/************************************************************/
/*                       Memory Objects                     */
/************************************************************/

/* This is to check the validity of a Python memory object
   (and to refresh its data status structure). Notably, we
   have to check that the real memory segment it points to
   is still in memory and hasn't changed (test its id and
   size). It could be that the segment has been removed and
   created again by someone else with the same key. This is
   fine as far as the segment (1) has the same id and size,
   and (2) is accessible via shmctl. If you have a better
   test, you're welcome :-) */

static int
check_memory_identity(
    PyShmObj *o)
{
    int new_shmid;
    int old_shmid = o->shmid;
    int old_size = o->ds.shm_segsz;
    key_t old_key = o->ds.shm_perm.key;

    /*
    -- 1. Try to get the segment identified by the old key (if not IPC_PRIVATE)
    -- 2. On failure or on mismatch of the new and the old id -> fail.
    -- 3. Try to refresh the object's status using the new id.
    -- 4. On failure (the segment cannot be accessed) -> fail.
    -- 5. Finaly, compare the old size and the one we got via the new id.
    */
    if (old_key != IPC_PRIVATE) {
	new_shmid = shmget(old_key, 0, 0);
	if (new_shmid != old_shmid)
	    return 0;
    }
    else
	new_shmid = old_shmid;
    if ((shmctl(new_shmid, IPC_STAT, &(o->ds)) != -1) &&
        (old_size == o->ds.shm_segsz) &&
	(old_key == o->ds.shm_perm.key))
        return 1;
    return 0;
}

/* Convenience macro for updating the shared memory data status structure */

#define refresh_memory_status(o)					\
    if (!check_memory_identity(o)) {					\
	PyErr_SetString(PyShm_Error,					\
			"can't access shared memory segment");		\
	return NULL;							\
    }

/*
-- attach([,address=0 [,how=0]])
*/

/* Attach the shared memory segment to the process address space */

static PyObject *
PyShmMemory_attach(
    PyShmObj *self,
    PyObject *args)
{
    unsigned long address = 0;
    int mode = 0;
    void *addr, *old_addr;

    if (!PyArg_ParseTuple(args, "|li", &address, &mode))
	return NULL;
    refresh_memory_status(self);
    /* return if already attached with the same mode to the same address */
    if ((self->addr != NULL) &&
	(self->mode == mode) &&
	((address == 0) || (self->addr == (void *)address))) {
	Py_INCREF(Py_None);
	return Py_None;
    }
    /* perform the attach */
    addr = (void *)shmat(self->shmid, (void *)address, mode);
    if (addr  == (void *)-1)
	return PyShm_Err();
    old_addr = self->addr;
    self->addr = addr;
    self->mode = mode;
    /* XXX - multiple attachments of the same shared memory segment
             to different locations of the process address space is
	     not supported. */
    shmdt(old_addr);
    Py_INCREF(Py_None);
    return Py_None;
}

/*
-- detach()
*/

/* Detach the memory object from the process address space */

static PyObject *
PyShmMemory_detach(
    PyShmObj *self,
    PyObject *args)
{
    if (!PyArg_NoArgs(args))
	return NULL;
    if (self->addr != NULL) {
	//refresh_memory_status(self);
	if (shmdt(self->addr) != 0)
	    return PyShm_Err();
	self->addr = NULL;		/* mark as detached */
    }
    Py_INCREF(Py_None);
    return Py_None;
}

/*
-- read(int Nbytes [,int Offset=0]) --> string
*/

/* Return a string of n bytes peeked from the shared memory segment */

static PyObject *
PyShmMemory_read(
    PyShmObj *self,
    PyObject *args)
{
    unsigned long n, offset = 0;
    char buf[128];
    char *addr;

    if (!PyArg_ParseTuple(args, "l|l", &n, &offset))
	return NULL;
    refresh_memory_status(self);
    if (self->addr == NULL) {
	PyErr_SetString(PyShm_Error, "R/W operation on detached memory");
  	return NULL;
    }
    if ((unsigned long)self->ds.shm_segsz < (n + offset)) {
	sprintf(buf, "read() argument%s exceed%s upper memory limit",
		offset ? "s" : "", offset ? "" : "s");
	PyErr_SetString(PyShm_Error, buf);
	return NULL;
    }
    addr = (char *)((unsigned long)self->addr + offset);
    return PyString_FromStringAndSize(addr, n);
}

/*
-- setgid(int Gid)
*/

static PyObject *
PyShmMemory_setgid(
    PyShmObj *self,
    PyObject *args)
{
    long newgid, oldgid;

    if (!PyArg_ParseTuple(args, "l", &newgid))
	return NULL;
    refresh_memory_status(self);
    oldgid = (long)self->ds.shm_perm.gid;
    self->ds.shm_perm.gid = (gid_t)newgid;
    if (shmctl(self->shmid, IPC_SET, &(self->ds)) == -1) {
	self->ds.shm_perm.gid = (gid_t)oldgid;
	return PyShm_Err();
    }
    Py_INCREF(Py_None);
    return Py_None;
}

/*
-- setperm(int Perm)
*/

static PyObject *
PyShmMemory_setperm(
    PyShmObj *self,
    PyObject *args)
{
    long newmode, oldmode;

    if (!PyArg_ParseTuple(args, "l", &newmode))
	return NULL;
    refresh_memory_status(self);
    newmode &= 0777;	/* permission bits only */
    oldmode = (mode_t)self->ds.shm_perm.mode;
    self->ds.shm_perm.mode ^= 0777;
    self->ds.shm_perm.mode |= (mode_t)newmode;
    if (shmctl(self->shmid, IPC_SET, &(self->ds)) == -1) {
	self->ds.shm_perm.mode = (mode_t)oldmode;
	return PyShm_Err();
    }
    Py_INCREF(Py_None);
    return Py_None;
}

/*
-- setuid(int Uid)
*/

static PyObject *
PyShmMemory_setuid(
    PyShmObj *self,
    PyObject *args)
{
    long newuid, olduid;

    if (!PyArg_ParseTuple(args, "l", &newuid))
	return NULL;
    refresh_memory_status(self);
    olduid = (long)self->ds.shm_perm.uid;
    self->ds.shm_perm.gid = (uid_t)newuid;
    if (shmctl(self->shmid, IPC_SET, &(self->ds)) == -1) {
	self->ds.shm_perm.uid = (uid_t)olduid;
	return PyShm_Err();
    }
    Py_INCREF(Py_None);
    return Py_None;
}

/*
-- write(string Data [, int Offset=0])
*/

/* Write a string to the shared memory segment. */

static PyObject *
PyShmMemory_write(
    PyShmObj *self,
    PyObject *args)
{
    char *data;
    unsigned long offset = 0;
    int n;
    char buf[128];
    char *addr;

    if (!PyArg_ParseTuple(args, "s#|l", &data, &n, &offset))
	return NULL;
    refresh_memory_status(self);
    if (self->addr == NULL) {
	PyErr_SetString(PyShm_Error, "R/W operation on detached memory");
  	return NULL;
    }
    if (self->mode & SHM_RDONLY) {
	PyErr_SetString(PyShm_Error,
			"can't write on read-only attached memory");
	return NULL;
    }
    if ((unsigned long)self->ds.shm_segsz < (n + offset)) {
	sprintf(buf, "write() argument%s exceed%s upper memory limit",
		offset ? "s" : "", offset ? "" : "s");
	PyErr_SetString(PyShm_Error, buf);
	return NULL;
    }
    addr = (void *)((unsigned long)self->addr + offset);
    memcpy(addr, data, n);
    Py_INCREF(Py_None);
    return Py_None;
}

/* List of methods for shared memory objects */

static PyMethodDef memory_methods[] = {
    {"attach",	(PyCFunction)PyShmMemory_attach,	1,
     "attach([int Addr=0 [,int How=0]]) --> None | except shm.error"},
    {"detach",	(PyCFunction)PyShmMemory_detach,	0,
     "detach() --> None | except shm.error"},
    {"read",	(PyCFunction)PyShmMemory_read,		1,
     "read(int Nbytes [,int Offset=0]) --> string | except shm.error"},
    {"setgid",	(PyCFunction)PyShmMemory_setgid,	1,
     "setgid(int Gid) --> None | except shm.error"},
    {"setperm",	(PyCFunction)PyShmMemory_setperm,	1,
     "setperm(int Perm) --> None | except shm.error"},
    {"setuid",	(PyCFunction)PyShmMemory_setuid,	1,
     "setuid(int Uid) --> None | except shm.error"},
    {"write",	(PyCFunction)PyShmMemory_write,		1,
     "write(string Data [,int Offset=0]) --> None | except shm.error"},
    {NULL,	NULL}		/* sentinel */
};

#define OFF(x)	offsetof(PyShmMemoryObject, x)
#define OFF1(x)	OFF(ds) + offsetof(struct shmid_ds, x)
#define OFF2(x)	OFF1(shm_perm) + offsetof(struct ipc_perm, x)

/* List of members for shared memory objects */

/* Note: member types are set in the initshm function.
   Members which need separate processing are:
   - addr --> it is not part of the shmid_ds structure
   - attached --> function depending on addr
   - nattch  --> system dependent declaration in shmid_ds (unknown type)
   - perm --> return permission (lower 9) bits only of ds.shm_perm.mode
*/

static struct memberlist memory_memberlist[] = {
    {"cgid",	T_INT,	OFF2(cgid),		RO},	/* 0  (gid_t)  */
    {"cpid",	T_INT,	OFF1(shm_cpid),		RO},	/* 1  (pid_t)  */
    {"cuid",	T_INT,	OFF2(cuid),		RO},	/* 2  (uid_t)  */
    {"key",	T_INT,	OFF2(key),		RO},	/* 3  (key_t)  */
    {"lpid",	T_INT,	OFF1(shm_lpid),		RO},	/* 4  (pid_t)  */
    {"shmid",	T_INT,	OFF(shmid),		RO},	/* 5  (int)    */
    {"size",	T_INT,	OFF1(shm_segsz),	RO},	/* 6  (int)    */
    {"gid",	T_INT,	OFF2(gid),		RO},	/* 7  (gid_t)  */
    {"uid",	T_INT,	OFF2(uid),		RO},	/* 8  (uid_t)  */
    /* The following members are implemented without this table */
    {"addr",	T_INT,	0,			RO},	/* 9  (void *) */
    {"attached",T_INT,	0,			RO},	/* 10  (int)    */
    {"nattch",	T_INT,	0,			RO},	/* 11 sys.dep. */
    {"perm",	T_INT,	0,			RO},	/* 12 (mode_t) */
    {NULL}			/* sentinel */
};

#undef OFF
#undef OFF1
#undef OFF2

static void
PyShmMemory_dealloc(
    PyShmObj *self)
{
    /* del shm_dict[key], ignore if it fails */
    if (PyDict_DelItem(shm_dict, PyInt_FromLong(self->shmid)) == -1)
	PyErr_Clear();
    /* all references in the current process to the shared
       memory segment are lost, so if attached, detach it.
       XXX: This is not true when Python is embedded.

    if (self->addr != NULL) {
	shmdt(self->addr);
    }
    */
    PyObject_DEL(self);
}

static PyObject *
PyShmMemory_getattr(
    PyShmObj *self,
    char *name)
{
    PyObject *res;

    res = Py_FindMethod(memory_methods, (PyObject *)self, name);
    if (res != NULL)
	return res;
    PyErr_Clear();
    refresh_memory_status(self);
    if (strcmp(name, "attached") == 0)
	return PyInt_FromLong((self->addr == NULL) ? 0 : 1);
    if (strcmp(name, "addr") == 0) {
	if (self->addr != NULL)
	    return PyInt_FromLong((unsigned long)self->addr);
	else {
	    Py_INCREF(Py_None);
	    return Py_None;
	}
    }
    if (strcmp(name, "nattch") == 0)
	return PyInt_FromLong(self->ds.shm_nattch);
    if (strcmp(name, "perm") == 0)
	return PyInt_FromLong(self->ds.shm_perm.mode & 0777);
    return PyMember_Get((char *)self, memory_memberlist, name);
}

static PyObject *
PyShmMemory_repr(
    PyShmObj *self,
    char *name)
{
    char buf[100];
    char buf2[20];

    refresh_memory_status(self);
    if (self->addr == NULL)
	sprintf(buf2, "None");
    else
	sprintf(buf2, "0x%p", self->addr);
    sprintf(buf, "<%s shared memory object, id=%d, size=%zd, addr=%s>",
	    (self->addr == NULL) ? "detached" : (self->mode & SHM_RDONLY) ?
	    "attached RO" : "attached R/W",
	    self->shmid,
	    self->ds.shm_segsz,
	    buf2);
    return PyString_FromString(buf);
}

/* Type object for shared memory objects */

static PyTypeObject PyShmMemory_Type = {
    PyObject_HEAD_INIT(&PyType_Type)
    0,					/*ob_size*/
    "shared memory",			/*tp_name*/
    sizeof(PyShmObj),			/*tp_size*/
    0,					/*tp_itemsize*/
    /* methods */
    (destructor)PyShmMemory_dealloc,	/*tp_dealloc*/
    0,					/*tp_print*/
    (getattrfunc)PyShmMemory_getattr,	/*tp_getattr*/
    0,					/*tp_setattr*/
    0,					/*tp_compare*/
    (reprfunc)PyShmMemory_repr,		/*tp_repr*/
    0,					/*tp_as_number*/
    0,					/*tp_as_sequence*/
    0,					/*tp_as_mapping*/
};

/************************************************************/
/*                     Semaphore Objects                    */
/************************************************************/

/* This is to check the validity of a Python semaphore object */

static int
check_semaphore_identity(
    PyShmSemObj *o)
{
    int new_semid;
    int old_semid = o->semid;
    unsigned short old_nsems = o->ds.sem_nsems;
    key_t old_key = o->ds.sem_perm.key;
    semctl_arg arg;

    if (old_key != IPC_PRIVATE) {
	new_semid = semget(old_key, 0, 0);
	if (new_semid != old_semid)
	    return 0;
    }
    else
	new_semid = old_semid;
    arg.buf = &(o->ds);
    if ((semctl(new_semid, 0, IPC_STAT, arg) != -1) &&
        (old_nsems == o->ds.sem_nsems) &&
	(old_key == o->ds.sem_perm.key))
        return 1;
    return 0;
}

/* Convenience macro for updating the semaphore data status structure */

#define refresh_semaphore_status(o)					\
    if (!check_semaphore_identity(o)) {					\
	PyErr_SetString(PyShm_Error,					\
			"can't access semaphore");			\
	return NULL;							\
    }

/*
-- P()
*/

static PyObject *
PyShmSemaphore_P(
    PyShmSemObj *self,
    PyObject *args)
{
    struct sembuf op[1];
    int res;

    op[0].sem_num = 0;
    op[0].sem_op = -1;
    op[0].sem_flg = self->opflag;

    if (!PyArg_NoArgs(args))
	return NULL;
    refresh_semaphore_status(self);
    res = semop(self->semid, op, (size_t)1);
    if (res == -1)
	return PyShm_Err();
    Py_INCREF(Py_None);
    return Py_None;
}

/*
-- V()
*/

static PyObject *
PyShmSemaphore_V(
    PyShmSemObj *self,
    PyObject *args)
{
    struct sembuf op[1];
    int res;

    op[0].sem_num = 0;
    op[0].sem_op = 1;
    op[0].sem_flg = self->opflag;

    if (!PyArg_NoArgs(args))
	return NULL;
    refresh_semaphore_status(self);
    res = semop(self->semid, op, (size_t)1);
    if (res == -1)
	return PyShm_Err();
    Py_INCREF(Py_None);
    return Py_None;
}

/*
-- Z()
*/

static PyObject *
PyShmSemaphore_Z(
    PyShmSemObj *self,
    PyObject *args)
{
    struct sembuf op[1];
    int res;

    op[0].sem_num = 0;
    op[0].sem_op = 0;
    op[0].sem_flg = self->opflag;

    if (!PyArg_NoArgs(args))
	return NULL;
    refresh_semaphore_status(self);
    res = semop(self->semid, op, (size_t)1);
    if (res == -1)
	return PyShm_Err();
    Py_INCREF(Py_None);
    return Py_None;
}

/*
-- setblocking(0|1)
*/

static PyObject *
PyShmSemaphore_setblocking(
    PyShmSemObj *self,
    PyObject *args)
{
    int block;

    if (!PyArg_ParseTuple(args, "i", &block))
	return NULL;
    refresh_semaphore_status(self);
    if (block)
	self->opflag &= ~IPC_NOWAIT;
    else
	self->opflag |= IPC_NOWAIT;
    Py_INCREF(Py_None);
    return Py_None;
}

/*
-- setgid(int Gid)
*/

static PyObject *
PyShmSemaphore_setgid(
    PyShmSemObj *self,
    PyObject *args)
{
    long newgid, oldgid;
    semctl_arg arg;

    if (!PyArg_ParseTuple(args, "l", &newgid))
	return NULL;
    refresh_semaphore_status(self);
    oldgid = (long)self->ds.sem_perm.gid;
    self->ds.sem_perm.gid = (gid_t)newgid;
    arg.buf = &(self->ds);
    if (semctl(self->semid, 0, IPC_SET, arg) == -1) {
	self->ds.sem_perm.gid = (gid_t)oldgid;
	return PyShm_Err();
    }
    Py_INCREF(Py_None);
    return Py_None;
}

/*
-- setperm(int Perm)
*/

static PyObject *
PyShmSemaphore_setperm(
    PyShmSemObj *self,
    PyObject *args)
{
    long newmode, oldmode;
    semctl_arg arg;

    if (!PyArg_ParseTuple(args, "l", &newmode))
	return NULL;
    refresh_semaphore_status(self);
    newmode &= 0777;	/* permission bits only */
    oldmode = (mode_t)self->ds.sem_perm.mode;
    self->ds.sem_perm.mode ^= 0777;
    self->ds.sem_perm.mode |= (mode_t)newmode;
    arg.buf = &(self->ds);
    if (semctl(self->semid, 0, IPC_SET, arg) == -1) {
	self->ds.sem_perm.mode = (mode_t)oldmode;
	return PyShm_Err();
    }
    Py_INCREF(Py_None);
    return Py_None;
}

/*
-- setuid(int Uid)
*/

static PyObject *
PyShmSemaphore_setuid(
    PyShmSemObj *self,
    PyObject *args)
{
    long newuid, olduid;
    semctl_arg arg;

    if (!PyArg_ParseTuple(args, "l", &newuid))
	return NULL;
    refresh_semaphore_status(self);
    olduid = (long)self->ds.sem_perm.uid;
    self->ds.sem_perm.gid = (uid_t)newuid;
    arg.buf = &(self->ds);
    if (semctl(self->semid, 0, IPC_SET, arg) == -1) {
	self->ds.sem_perm.uid = (uid_t)olduid;
	return PyShm_Err();
    }
    Py_INCREF(Py_None);
    return Py_None;
}

/*
-- setundo(0|1)
*/

static PyObject *
PyShmSemaphore_setundo(
    PyShmSemObj *self,
    PyObject *args)
{
    int undo;

    if (!PyArg_ParseTuple(args, "i", &undo))
	return NULL;
    refresh_semaphore_status(self);
    if (undo)
	self->opflag |= SEM_UNDO;
    else
	self->opflag &= ~SEM_UNDO;
    Py_INCREF(Py_None);
    return Py_None;
}

/*
-- setval(int Value)
*/

static PyObject *
PyShmSemaphore_setval(
    PyShmSemObj *self,
    PyObject *args)
{
    int value;
    semctl_arg arg;

    if (!PyArg_ParseTuple(args, "i", &value))
	return NULL;
    refresh_semaphore_status(self);
    arg.val = value;
    if (semctl(self->semid, 0, SETVAL, arg) == -1)
	return PyShm_Err();
    Py_INCREF(Py_None);
    return Py_None;
}

/* List of methods for semaphore objects */

static PyMethodDef semaphore_methods[] = {
    {"P",		(PyCFunction)PyShmSemaphore_P,			0,
     "P() --> None | except shm.error"},
    {"V",		(PyCFunction)PyShmSemaphore_V,			0,
     "V() --> None | except shm.error"},
    {"Z",		(PyCFunction)PyShmSemaphore_Z,			0,
     "Z() --> None | except shm.error"},
    {"setblocking",	(PyCFunction)PyShmSemaphore_setblocking,	1,
     "setblocking(0|1) --> None"},
    {"setgid",		(PyCFunction)PyShmSemaphore_setgid,		1,
     "setgid(int Gid) --> None | except shm.error"},
    {"setperm",		(PyCFunction)PyShmSemaphore_setperm,		1,
     "setperm(int Perm) --> None | except shm.error"},
    {"setuid",		(PyCFunction)PyShmSemaphore_setuid,		1,
     "setuid(int Uid) --> None | except shm.error"},
    {"setundo",		(PyCFunction)PyShmSemaphore_setundo,		1,
     "setundo(0|1) --> None"},
    {"setval",		(PyCFunction)PyShmSemaphore_setval,		1,
     "setval(int Value) --> None | except shm.error"},
    {NULL,	NULL}		/* sentinel */
};

#define OFF(x)	offsetof(PyShmSemaphoreObject, x)
#define OFF1(x)	OFF(ds) + offsetof(struct semid_ds, x)
#define OFF2(x)	OFF1(sem_perm) + offsetof(struct ipc_perm, x)

/* List of members for semaphore objects */

/* Note: member types are set in the initshm function.
   Members which need separate processing are:
   - val, lpid, ncnt, zcnt --> in kernel memory, not accessible from a process
   - perm --> return permission (lower 9) bits only of ds.sem_perm.mode
*/

static struct memberlist semaphore_memberlist[] = {
    {"cgid",	T_INT,	OFF2(cgid),		RO},	/* 0  (gid_t)  */
    {"cuid",	T_INT,	OFF2(cuid),		RO},	/* 1  (uid_t)  */
    {"key",	T_INT,	OFF2(key),		RO},	/* 2  (key_t)  */
    {"semid",	T_INT,	OFF(semid),		RO},	/* 3  (int)    */
    {"gid",	T_INT,	OFF2(gid),		RO},	/* 4  (gid_t)  */
    {"uid",	T_INT,	OFF2(uid),		RO},	/* 5  (uid_t)  */
    /* The following members are implemented without this table */
    {"lpid",	T_INT,	0,			RO},	/* 6  (ushort) */
    {"ncnt",	T_INT,	0,			RO},	/* 7  (ushort) */
    {"perm",	T_INT,	0,			RO},	/* 8  (mode_t) */
    {"val",	T_INT,	0,			RO},	/* 9  (ushort) */
    {"zcnt",	T_INT,	0,			RO},	/* 10 (ushort) */
    {NULL}			/* sentinel */
};

#undef OFF
#undef OFF1
#undef OFF2

static void
PyShmSemaphore_dealloc(
    PyShmSemObj *self)
{
    /* del sem_dict[key], ignore if it fails */
    if (PyDict_DelItem(sem_dict, PyInt_FromLong(self->semid)) == -1)
	PyErr_Clear();
    PyObject_DEL(self);
}

static PyObject *
PyShmSemaphore_getattr(
    PyShmSemObj *self,
    char *name)
{
    PyObject *res;

    res = Py_FindMethod(semaphore_methods, (PyObject *)self, name);
    if (res != NULL)
	return res;
    PyErr_Clear();
    refresh_semaphore_status(self);
    if (strcmp(name, "val") == 0)
	return PyInt_FromLong(semctl(self->semid, 0, GETVAL, 0));
    if (strcmp(name, "lpid") == 0)
	return PyInt_FromLong(semctl(self->semid, 0, GETPID, 0));
    if (strcmp(name, "ncnt") == 0)
	return PyInt_FromLong(semctl(self->semid, 0, GETNCNT, 0));
    if (strcmp(name, "zcnt") == 0)
	return PyInt_FromLong(semctl(self->semid, 0, GETZCNT, 0));
    if (strcmp(name, "perm") == 0)
	return PyInt_FromLong(self->ds.sem_perm.mode & 0777);
    return PyMember_Get((char *)self, semaphore_memberlist, name);
}

static PyObject *
PyShmSemaphore_repr(
    PyShmSemObj *self,
    char *name)
{
    char buf[100];

    refresh_semaphore_status(self);
    sprintf(buf, "<semaphore object, id=%d, val=%d, ncnt=%d, zcnt=%d>",
	    self->semid,
	    semctl(self->semid, 0, GETVAL, 0),
	    semctl(self->semid, 0, GETNCNT, 0),
	    semctl(self->semid, 0, GETZCNT, 0));
    return PyString_FromString(buf);
}

/* Type object for semaphore objects */

static PyTypeObject PyShmSemaphore_Type = {
    PyObject_HEAD_INIT(&PyType_Type)
    0,					/*ob_size*/
    "semaphore",			/*tp_name*/
    sizeof(PyShmSemObj),		/*tp_size*/
    0,					/*tp_itemsize*/
    /* methods */
    (destructor)PyShmSemaphore_dealloc,	/*tp_dealloc*/
    0,					/*tp_print*/
    (getattrfunc)PyShmSemaphore_getattr,/*tp_getattr*/
    0,					/*tp_setattr*/
    0,					/*tp_compare*/
    (reprfunc)PyShmSemaphore_repr,	/*tp_repr*/
    0,					/*tp_as_number*/
    0,					/*tp_as_sequence*/
    0,					/*tp_as_mapping*/
};

/************************************************************/
/*                      Module Interface                    */
/************************************************************/

/*
-- ftok(string Path, int ProjId) -> int
*/

/* Compute a key by using the system's ftok algorithm */

static PyObject *
PyShm_ftok(
    PyObject *self,
    PyObject *args)
{
    char *path;
    char id;
    key_t key;

    if (!PyArg_ParseTuple(args, "sb", &path, &id))
	return NULL;
    key = ftok(path, id);
    return PyInt_FromLong((long)key);
}

/*
-- getshmid(int Key) --> int | except KeyError
*/

/* Return a shared memory segment id from a given key */

static PyObject *
PyShm_getshmid(
    PyObject *self,
    PyObject *args)
{
    long key;
    int shmid;

    if (!PyArg_ParseTuple(args, "l", &key))
	return NULL;
    shmid = shmget((key_t)key, 0, 0);
    if (shmid == -1) {
	PyErr_SetObject(PyExc_KeyError, PyInt_FromLong(key));
	return NULL;
    }
    return PyInt_FromLong(shmid);
}

/*
-- memory_haskey(int Key) --> int
*/

/* Check whether there is a shared memory segment with the given key */

static PyObject *
PyShm_memory_haskey(
    PyObject *self,
    PyObject *args)
{
    long key;
    int shmid;

    if (!PyArg_ParseTuple(args, "l", &key))
	return NULL;
    shmid = shmget((key_t)key, 0, 0);
    return PyInt_FromLong((shmid == -1) ? 0 : 1);
}

/*
-- memory(int Shmid) --> object | except shm.error
*/

/* Get an existing shared memory segment and return it as a python object. */

static PyObject *
PyShm_memory(
    PyObject *self,
    PyObject *args)
{
    int shmid;
    PyShmObj *o;
    PyObject *keyo;

    if (!PyArg_ParseTuple(args, "i", &shmid))
	return NULL;
    keyo = PyInt_FromLong(shmid);
    /* get the object from the dictionary */
    if (PyMapping_HasKey(shm_dict, keyo)) {
	o = (PyShmObj *)PyDict_GetItem(shm_dict, keyo);
	Py_INCREF(o);
    }
    else {
	/* not found, create it */
	if ((o = PyObject_NEW(PyShmObj, &PyShmMemory_Type)) == NULL)
	    return NULL;
	o->shmid = shmid;
	o->addr = NULL;
	o->mode = 0;
	/* shm_dict[shmid] = o */
	if (PyDict_SetItem(shm_dict, keyo, (PyObject *)o) == -1) {
	    Py_DECREF(o);
	    PyErr_SetString(PyShm_Error,
			    "can't initialize shared memory object");
	    return NULL;
	}
	Py_DECREF(o);	/* the owned reference in shm_dict doesn't count! */
    }
    /* set up the status data */
    if (shmctl(o->shmid, IPC_STAT, &(o->ds)) == -1) {
	Py_DECREF(o);
	PyErr_SetString(PyShm_Error,
			"can't access shared memory segment");
	return NULL;
    }
    return (PyObject *)o;
}

/*
-- create_memory(int Key, int Size [,int Perm=0666]) --> object
*/

/* Create a new shared memory segment. */

static PyObject *
PyShm_create_memory(
    PyObject *self,
    PyObject *args)
{
    long key;
    int size, shmid;
    int perm = 0666;	/* Default permission is -rw-rw-rw- */

    if (!PyArg_ParseTuple(args, "li|i", &key, &size, &perm))
	return NULL;
    shmid = shmget((key_t)key, size, perm | IPC_CREAT | IPC_EXCL);
    if (shmid == -1)
	return PyShm_Err();
    /* return PyInt_FromLong(shmid); */
    return PyShm_memory(self, Py_BuildValue("(i)", shmid));
}

/*
-- remove_memory(int Shmid) --> None | except shm.error
*/

/* Remove an existing shared memory segment. */

static PyObject *
PyShm_remove_memory(
    PyObject *self,
    PyObject *args)
{
    int shmid, res;

    if (!PyArg_ParseTuple(args, "i", &shmid))
	return NULL;
    res = shmctl(shmid, IPC_RMID, 0);	/* remove it */
    if (res == -1)
	return PyShm_Err();
    Py_INCREF(Py_None);
    return Py_None;
}

/*
-- getsemid(int Key) --> int | except KeyError
*/

/* Return a semaphore id from a given key */

static PyObject *
PyShm_getsemid(
    PyObject *self,
    PyObject *args)
{
    long key;
    int semid;

    if (!PyArg_ParseTuple(args, "l", &key))
	return NULL;
    semid = semget((key_t)key, 0, 0);
    if (semid == -1) {
	PyErr_SetObject(PyExc_KeyError, PyInt_FromLong(key));
	return NULL;
    }
    return PyInt_FromLong(semid);
}

/*
-- semaphore_haskey(int Key) --> int
*/

/* Check whether there is a semaphore with the given key */

static PyObject *
PyShm_semaphore_haskey(
    PyObject *self,
    PyObject *args)
{
    long key;
    int semid;

    if (!PyArg_ParseTuple(args, "l", &key))
	return NULL;
    semid = semget((key_t)key, 0, 0);
    return PyInt_FromLong((semid == -1) ? 0 : 1);
}

/*
-- semaphore(int Semid) --> object
*/

/* Get an existing semaphore and return it as a python object. */

static PyObject *
PyShm_semaphore(
    PyObject *self,
    PyObject *args)
{
    int semid;
    PyShmSemObj *o;
    PyObject *keyo;
    semctl_arg arg;

    if (!PyArg_ParseTuple(args, "i", &semid))
	return NULL;
    keyo = PyInt_FromLong(semid);
    /* get the object from the dictionary */
    if (PyMapping_HasKey(sem_dict, keyo)) {
	o = (PyShmSemObj *)PyDict_GetItem(sem_dict, keyo);
	Py_INCREF(o);
    }
    else {
	/* not found, create it */
	if ((o = PyObject_NEW(PyShmSemObj, &PyShmSemaphore_Type)) == NULL)
	    return NULL;
	o->semid = semid;
	o->opflag = 0;
	/* sem_dict[semid] = o */
	if (PyDict_SetItem(sem_dict, keyo, (PyObject *)o) == -1) {
	    Py_DECREF(o);
	    PyErr_SetString(PyShm_Error,
			    "can't initialize semaphore object");
	    return NULL;
	}
	Py_DECREF(o);	/* the owned reference in sem_dict doesn't count! */
    }
    /* set up the status data */
    arg.buf = &(o->ds);
    if (semctl(o->semid, 0, IPC_STAT, arg) == -1) {
	Py_DECREF(o);
	PyErr_SetString(PyShm_Error,
			"can't access semaphore");
	return NULL;
    }
    return (PyObject *)o;
}

/*
-- create_semaphore(int Key, [,int Value=1 [,int Perm=0666]]) --> object
*/

/* Create a new semaphore. */

static PyObject *
PyShm_create_semaphore(
    PyObject *self,
    PyObject *args)
{
    long key;
    int semid;
    int value = 1;
    int perm = 0666;	/* Default permission is -rw-rw-rw- */
    semctl_arg arg;

    if (!PyArg_ParseTuple(args, "l|ii", &key, &value, &perm))
	return NULL;
    semid = semget((key_t)key, 1, perm | IPC_CREAT | IPC_EXCL);
    arg.val = value;
    if (!((semid != -1) &&
	  (semctl(semid, 0, SETVAL, arg) != -1)))
	return PyShm_Err();
    return PyShm_semaphore(self, Py_BuildValue("(i)", semid));
}

/*
-- remove_semaphore(int Semid) --> None | except shm.error
*/

/* Remove an existing semaphore. */

static PyObject *
PyShm_remove_semaphore(
    PyObject *self,
    PyObject *args)
{
    int semid, res;

    if (!PyArg_ParseTuple(args, "i", &semid))
	return NULL;
    res = semctl(semid, 0, IPC_RMID, 0);	/* remove it */
    if (res == -1)
	return PyShm_Err();
    Py_INCREF(Py_None);
    return Py_None;
}

/* List of functions exported by this module. */

static PyMethodDef PyShm_methods[] = {
    {"create_memory",		PyShm_create_memory,	1,
     "create_memory(int Key, int Size [,int Perm=0666]) --> object | except shm.error"},
    {"create_semaphore",	PyShm_create_semaphore,	1,
     "create_semaphore(int Key [,int Value=1 [,int Perm=0666]]) --> object | except shm.error"},
    {"ftok",			PyShm_ftok,		1,
     "ftok(string Path, int ProjId) --> int | except shm.error"},
    {"getsemid",		PyShm_getsemid,		1,
     "getsemid(int Key) --> int | except KeyError"},
    {"getshmid",		PyShm_getshmid,		1,
     "getshmid(int Key) --> int | except KeyError"},
    {"memory_haskey",		PyShm_memory_haskey,	1,
     "memory_haskey(int Key) --> int"},
    {"memory",			PyShm_memory,		1,
     "memory(int Shmid) --> object | except shm.error"},
    {"semaphore",		PyShm_semaphore,	1,
     "semaphore(int Semid) --> object | except shm.error"},
    {"semaphore_haskey",	PyShm_semaphore_haskey,	1,
     "semaphore_haskey(int Key) --> int"},
    {"remove_memory",		PyShm_remove_memory,	1,
     "remove_memory(int Shmid) --> None | except shm.error"},
    {"remove_semaphore",	PyShm_remove_semaphore,	1,
     "remove_semaphore(int Semid) --> None | except shm.error"},
    {NULL,			NULL}		/* Sentinel */
};


/* Initialize this module */

/* This is for inserting constants in the module's dictionary */

static void
insint(
    PyObject *d,
    char *name,
    int value)
{
	PyObject *v = PyInt_FromLong((long) value);
	if (!v || PyDict_SetItemString(d, name, v))
		Py_FatalError("can't initialize shm module");

	Py_DECREF(v);
}

/* This is to set up the type of shared memory/semaphore object members */

static void
set_member_type(
    struct memberlist *sxm_memberlist,
    int index,		/* index in memberlist */
    int typesize)	/* sizeof(member_type) */
{
    int t;

    if (typesize == sizeof(char))
	t = T_UBYTE;
    else if (typesize == sizeof(short))
	t = T_USHORT;
    else if (typesize == sizeof(int))
	t = T_UINT;
    else if (typesize == sizeof(long))
	t = T_ULONG;
    else {
	Py_FatalError("can't initialize shm module");
	return;
    }
    sxm_memberlist[index].type = t;
};

void
initshm(void)
{
    PyObject *m, *d;

    m = Py_InitModule("shm", PyShm_methods);
    d = PyModule_GetDict(m);
    PyShm_Error = PyString_FromString("shm.error");
    if (PyShm_Error == NULL ||
	PyDict_SetItemString(d, "error", PyShm_Error) != 0)
	    Py_FatalError("can't define shm.error");
    if (PyDict_SetItemString(d, "__doc__", PyString_FromString
			     ("Interface to System V shared memory IPC")) != 0)
	Py_FatalError("can't define shm.__doc__");
    if ((shm_dict = PyDict_New()) == NULL ||
	(sem_dict = PyDict_New()) == NULL)
	Py_FatalError("can't initialize shm module");

    /* initialize the machine dependent types in memory_memberlist */
    set_member_type(memory_memberlist, 0, sizeof(gid_t));	/* cgid   */
    set_member_type(memory_memberlist, 1, sizeof(pid_t));	/* cpid   */
    set_member_type(memory_memberlist, 2, sizeof(uid_t));	/* cuid   */
    set_member_type(memory_memberlist, 3, sizeof(key_t));	/* key    */
    set_member_type(memory_memberlist, 4, sizeof(pid_t));	/* lpid   */
    set_member_type(memory_memberlist, 5, sizeof(int));		/* shmid  */
    set_member_type(memory_memberlist, 6, sizeof(int));		/* size   */
    set_member_type(memory_memberlist, 7, sizeof(gid_t));	/* gid    */
    set_member_type(memory_memberlist, 8, sizeof(uid_t));	/* uid    */

    /* initialize the machine dependent types in semaphore_memberlist */
    set_member_type(semaphore_memberlist, 0, sizeof(gid_t));	/* cgid   */
    set_member_type(semaphore_memberlist, 1, sizeof(uid_t));	/* cuid   */
    set_member_type(semaphore_memberlist, 2, sizeof(key_t));	/* key    */
    set_member_type(semaphore_memberlist, 3, sizeof(int));	/* semid  */
    set_member_type(semaphore_memberlist, 4, sizeof(gid_t));	/* gid    */
    set_member_type(semaphore_memberlist, 5, sizeof(uid_t));	/* uid    */

    /* relevant constants for this module; the others are useless here */
    insint(d, "IPC_PRIVATE", IPC_PRIVATE);
    insint(d, "SHM_RDONLY", SHM_RDONLY);
    insint(d, "SHM_RND", SHM_RND);
#ifdef SHMLBA
    insint(d, "SHMLBA", SHMLBA);
#endif
#ifdef SEM_A
    insint(d, "SEM_A", SEM_A);
#endif
#ifdef SEM_R
    insint(d, "SEM_R", SEM_R);
#endif
#ifdef SHM_R
    insint(d, "SHM_R", SHM_R);
#endif
#ifdef SHM_W
    insint(d, "SHM_W", SHM_W);
#endif
}
