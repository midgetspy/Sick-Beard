import sqlite3
import time
import threading
import Queue

from storm.locals import Store, create_database
from sickbeard.tvapi import proxy

import sickbeard

from sickbeard import logger

def safe_list(resultSet):
    return sickbeard.storeManager.safe_store(_safe_list, resultSet)

def _safe_list(resultSet):
    """
    Take a ResultSet object and return a list of thread-safe proxy objects instead 
    """
    return [proxy._getProxy(x) for x in resultSet]

class SafeStore():
    """
    Keeps a queue of commands to execute on the store object, executes them one
    at a time on a single store object in a single thread, and returns the results.
    """

    def __init__(self):
        self._req = 0
        
        self._queue = Queue.Queue()
        self._database = create_database("sqlite:stormtest.db")
        self._store = None
        
        self._resultDict = {}
        
        self._abort = False
        
    def _getReq(self):
        self._req += 1
        return self._req
    
    req = property(_getReq)
    
    def run(self):
        
        self._store = Store(self._database)
        
        while True:

            # get an item whenever one becomes available
            (i, f, a, k) = self._queue.get()
            
            # execute it, place the result on the queue, and then indicate that it's ready for retrieval
            try:
                self._resultDict[i] = self._exec_on_store(f, *a, **k)
            except Exception, e:
                self._resultDict[i] = e
            
            if self._abort:
                break
            
    def abort(self):
        
        # wait for all stuff to finish
        while len(self._resultDict):
            time.sleep(0.1)
        
        # stop the thread
        self._abort = True
        
        # do one last thing
        self.commit()

        sickbeard.storeThread.join(1)
    
    # perform an action on the store
    def _exec_on_store(self, func, *args, **kwargs):
        try:
            to_exec = getattr(self._store, func)
        except (AttributeError, TypeError):
            to_exec = func
        
        _atomic = True
        if '_atomic' in kwargs:
            _atomic = kwargs['_atomic']
            del kwargs['_atomic']
        
        #logger.log("calling " + str(to_exec) + " with " + repr(args), logger.DEBUG)
        result = to_exec(*args, **kwargs)
        
        if _atomic == False:
            return result
        else:
            self.end_safe_store()
            return result
    
    def end_safe_store(self):
        self._queue.task_done()
    
    def commit(self):
        try:
            if threading.currentThread().ident == sickbeard.storeThread.ident:
                self._store.commit()
            else:
                sickbeard.storeManager.safe_store("commit")
        except sqlite3.OperationalError, e:
            if str(e).startswith("cannot commit - no transaction is active"):
                pass
    
    # this function will block until an exclusive store object is available
    def safe_store(self, func, *args, **kwargs):
    
        # if we're already on the right thread don't bother with the queue
        if threading.currentThread().ident == sickbeard.storeThread.ident:
            kwargs['_atomic'] = False
            return sickbeard.storeManager._exec_on_store(func, *args, **kwargs)
    
        toWaitFor = self.req
        self._queue.put((toWaitFor, func, args, kwargs))
        logger.log("Placed req number " + str(toWaitFor) + " on the queue: "+str(func)+" w/ "+str(args)+" & "+str(kwargs), logger.DEBUG)
        
        # block until the result we want is given for us to eat
        while toWaitFor not in self._resultDict:
            time.sleep(0.01)
    
        #logger.log("a result for req number " + str(toWaitFor) + " is available, consuming and returning it: " + str(self._resultDict[toWaitFor]), logger.DEBUG)
    
        tempResult = self._resultDict[toWaitFor]

        # reset the result slot so the thread knows it can put a new result on there
        del self._resultDict[toWaitFor]
    
        if isinstance(tempResult, Exception):
            raise tempResult
    
        return tempResult