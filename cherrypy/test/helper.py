"""A library of helper functions for the CherryPy test suite.

The actual script that runs the entire CP test suite is called
"test.py" (in this folder); test.py calls this module as a library.

Usage
=====
Each individual test_*.py module imports this module (helper),
usually to make an instance of CPWebCase, and then call testmain().

The CP test suite script (test.py) imports this module and calls
run_test_suite, possibly more than once. CP applications may also
import test.py (to use TestHarness), which then calls helper.py.
"""

# GREAT CARE has been taken to separate this module from test.py,
# because different consumers of each have mutually-exclusive import
# requirements. So don't go moving functions from here into test.py,
# or vice-versa, unless you *really* know what you're doing.

import datetime
import os
thisdir = os.path.abspath(os.path.dirname(__file__))
import re
import sys
import time
import warnings

import cherrypy
from cherrypy.lib import httputil, profiler
from cherrypy.test import webtest


class CPWebCase(webtest.WebCase):
    
    script_name = ""
    scheme = "http"
    
    def prefix(self):
        return self.script_name.rstrip("/")
    
    def base(self):
        if ((self.scheme == "http" and self.PORT == 80) or
            (self.scheme == "https" and self.PORT == 443)):
            port = ""
        else:
            port = ":%s" % self.PORT
        
        return "%s://%s%s%s" % (self.scheme, self.HOST, port,
                                self.script_name.rstrip("/"))
    
    def exit(self):
        sys.exit()
    
    def getPage(self, url, headers=None, method="GET", body=None, protocol=None):
        """Open the url. Return status, headers, body."""
        if self.script_name:
            url = httputil.urljoin(self.script_name, url)
        return webtest.WebCase.getPage(self, url, headers, method, body, protocol)
    
    def skip(self, msg='skipped '):
        sys.stderr.write(msg)
    
    def assertErrorPage(self, status, message=None, pattern=''):
        """Compare the response body with a built in error page.
        
        The function will optionally look for the regexp pattern,
        within the exception embedded in the error page."""
        
        # This will never contain a traceback
        page = cherrypy._cperror.get_error_page(status, message=message)
        
        # First, test the response body without checking the traceback.
        # Stick a match-all group (.*) in to grab the traceback.
        esc = re.escape
        epage = esc(page)
        epage = epage.replace(esc('<pre id="traceback"></pre>'),
                              esc('<pre id="traceback">') + '(.*)' + esc('</pre>'))
        m = re.match(epage, self.body, re.DOTALL)
        if not m:
            self._handlewebError('Error page does not match; expected:\n' + page)
            return
        
        # Now test the pattern against the traceback
        if pattern is None:
            # Special-case None to mean that there should be *no* traceback.
            if m and m.group(1):
                self._handlewebError('Error page contains traceback')
        else:
            if (m is None) or (
                not re.search(re.escape(pattern),
                              m.group(1))):
                msg = 'Error page does not contain %s in traceback'
                self._handlewebError(msg % repr(pattern))
    
    date_tolerance = 2
    
    def assertEqualDates(self, dt1, dt2, seconds=None):
        """Assert abs(dt1 - dt2) is within Y seconds."""
        if seconds is None:
            seconds = self.date_tolerance
        
        if dt1 > dt2:
            diff = dt1 - dt2
        else:
            diff = dt2 - dt1
        if not diff < datetime.timedelta(seconds=seconds):
            raise AssertionError('%r and %r are not within %r seconds.' % 
                                 (dt1, dt2, seconds))


CPTestLoader = webtest.ReloadingTestLoader()
CPTestRunner = webtest.TerseTestRunner(verbosity=2)


def run_test_suite(moduleNames, conf, supervisor):
    """Run the given test modules using the given supervisor and [global] conf.
    
    The 'supervisor' arg should be an object with 'start' and 'stop' methods.
    See test/test.py.
    """
    # The Pybots automatic testing system needs the suite to exit
    # with a non-zero value if there were any problems.
    test_success = True
    
    for testmod in moduleNames:
        cherrypy.config.reset()
        cherrypy.config.update(conf)
        setup_client(supervisor)
        
        if '.' in testmod:
            package, test_name = testmod.rsplit('.', 1)
            p = __import__(package, globals(), locals(), fromlist=[test_name])
            m = getattr(p, test_name)
        else:
            m = __import__(testmod, globals(), locals())
        suite = CPTestLoader.loadTestsFromName(testmod)
        
        setup = getattr(m, "setup_server", None)
        if setup: supervisor.start(testmod)
        try:
            result = CPTestRunner.run(suite)
            test_success &= result.wasSuccessful()
        finally:
            if setup: supervisor.stop()
    
    if test_success:
        return 0
    else:
        return 1

def setup_client(supervisor):
    """Set up the WebCase classes to match the server's socket settings."""
    webtest.WebCase.PORT = cherrypy.server.socket_port
    webtest.WebCase.HOST = cherrypy.server.socket_host
    if cherrypy.server.ssl_certificate:
        CPWebCase.scheme = 'https'

def testmain(conf=None):
    """Run __main__ as a test module, with webtest debugging."""
    # Comment me out to see ENGINE messages etc. when running a test standalone.
    cherrypy.config.update({'environment': "test_suite"})
    cherrypy.server.socket_host = '127.0.0.1'
    
    from cherrypy.test.test import LocalWSGISupervisor
    supervisor = LocalWSGISupervisor(host=cherrypy.server.socket_host,
                                     port=cherrypy.server.socket_port)
    setup_client(supervisor)
    supervisor.start('__main__')
    try:
        return webtest.main()
    finally:
        supervisor.stop()



# --------------------------- Spawning helpers --------------------------- #


class CPProcess(object):
    
    pid_file = os.path.join(thisdir, 'test.pid')
    config_file = os.path.join(thisdir, 'test.conf')
    config_template = """[global]
server.socket_host: '%(host)s'
server.socket_port: %(port)s
checker.on: False
log.screen: False
log.error_file: r'%(error_log)s'
log.access_file: r'%(access_log)s'
%(ssl)s
%(extra)s
"""
    error_log = os.path.join(thisdir, 'test.error.log')
    access_log = os.path.join(thisdir, 'test.access.log')
    
    def __init__(self, wait=False, daemonize=False, ssl=False, socket_host=None, socket_port=None):
        self.wait = wait
        self.daemonize = daemonize
        self.ssl = ssl
        self.host = socket_host or cherrypy.server.socket_host
        self.port = socket_port or cherrypy.server.socket_port
    
    def write_conf(self, extra=""):
        if self.ssl:
            serverpem = os.path.join(thisdir, 'test.pem')
            ssl = """
server.ssl_certificate: r'%s'
server.ssl_private_key: r'%s'
""" % (serverpem, serverpem)
        else:
            ssl = ""
        
        conf = self.config_template % {
            'host': self.host,
            'port': self.port,
            'error_log': self.error_log,
            'access_log': self.access_log,
            'ssl': ssl,
            'extra': extra,
            }
        f = open(self.config_file, 'wb')
        f.write(conf)
        f.close()
    
    def start(self, imports=None):
        """Start cherryd in a subprocess."""
        cherrypy._cpserver.wait_for_free_port(self.host, self.port)
        
        args = [sys.executable, os.path.join(thisdir, '..', 'cherryd'),
                '-c', self.config_file, '-p', self.pid_file]
        
        if not isinstance(imports, (list, tuple)):
            imports = [imports]
        for i in imports:
            if i:
                args.append('-i')
                args.append(i)
        
        if self.daemonize:
            args.append('-d')
        
        if self.wait:
            self.exit_code = os.spawnl(os.P_WAIT, sys.executable, *args)
        else:
            os.spawnl(os.P_NOWAIT, sys.executable, *args)
            cherrypy._cpserver.wait_for_occupied_port(self.host, self.port)
        
        # Give the engine a wee bit more time to finish STARTING
        if self.daemonize:
            time.sleep(2)
        else:
            time.sleep(1)
    
    def get_pid(self):
        return int(open(self.pid_file, 'rb').read())
    
    def join(self):
        """Wait for the process to exit."""
        try:
            try:
                # Mac, UNIX
                os.wait()
            except AttributeError:
                # Windows
                try:
                    pid = self.get_pid()
                except IOError:
                    # Assume the subprocess deleted the pidfile on shutdown.
                    pass
                else:
                    os.waitpid(pid, 0)
        except OSError, x:
            if x.args != (10, 'No child processes'):
                raise

