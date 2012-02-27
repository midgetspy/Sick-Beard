# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of Sick Beard.
#
# Sick Beard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Sick Beard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

#import cherrypy
import cherrypy.lib.auth_basic
import os.path

import sickbeard

from sickbeard import logger
from sickbeard.webserve import WebInterface

from sickbeard.helpers import create_https_certificates

def initWebServer(options = {}):
        options.setdefault('port',      8081)
        options.setdefault('host',      '0.0.0.0')
        options.setdefault('log_dir',   None)
        options.setdefault('username',    '')
        options.setdefault('password',    '')
        options.setdefault('web_root',   '/')
        assert isinstance(options['port'], int)
        assert 'data_root' in options

        def http_error_401_hander(status, message, traceback, version):
            """ Custom handler for 401 error """
            if status != "401 Unauthorized":
                logger.log(u"CherryPy caught an error: %s %s" % (status, message), logger.ERROR)
                logger.log(traceback, logger.DEBUG)
            return r'''
<html>
    <head>
        <title>%s</title>
    </head>
    <body>
        <br/>
        <font color="#0000FF">Error %s: You need to provide a valid username and password.</font>
    </body>
</html>
''' % ('Access denied', status)

        def http_error_404_hander(status, message, traceback, version):
            """ Custom handler for 404 error, redirect back to main page """
            return r'''
<html>
    <head>
        <title>404</title>
        <script type="text/javascript" charset="utf-8">
          <!--
          location.href = "%s"
          //-->
        </script>
    </head>
    <body>
        <br/>
    </body>
</html>
''' % '/'

        # cherrypy setup
        enable_https = options['enable_https']
        https_cert = options['https_cert']
        https_key = options['https_key']

        if enable_https:
            # If either the HTTPS certificate or key do not exist, make some self-signed ones.
            if not (https_cert and os.path.exists(https_cert)) or not (https_key and os.path.exists(https_key)):
                if not create_https_certificates(https_cert, https_key):
                    logger.log(u"Unable to create cert/key files, disabling HTTPS")
                    sickbeard.ENABLE_HTTPS = False
                    enable_https = False

            if not (os.path.exists(https_cert) and os.path.exists(https_key)):
                logger.log(u"Disabled HTTPS because of missing CERT and KEY files", logger.WARNING)
                sickbeard.ENABLE_HTTPS = False
                enable_https = False

        options_dict = {
                        'server.socket_port': options['port'],
                        'server.socket_host': options['host'],
                        'log.screen':         False,
                        'error_page.401':     http_error_401_hander,
                        'error_page.404':     http_error_404_hander,
        }

        if enable_https:
            options_dict['server.ssl_certificate'] = https_cert
            options_dict['server.ssl_private_key'] = https_key
            protocol = "https"
        else:
            protocol = "http"

        logger.log(u"Starting Sick Beard on "+protocol+"://" + str(options['host']) + ":" + str(options['port']) + "/")
        cherrypy.config.update(options_dict)

        # setup cherrypy logging
        if options['log_dir'] and os.path.isdir(options['log_dir']):
                cherrypy.config.update({ 'log.access_file': os.path.join(options['log_dir'], "cherrypy.log") })
                logger.log('Using %s for cherrypy log' % cherrypy.config['log.access_file'])

        conf = {
                        '/': {
                                'tools.staticdir.root': options['data_root'],
                                'tools.encode.on': True,
                                'tools.encode.encoding': 'utf-8',
                        },
                        '/images': {
                                'tools.staticdir.on':  True,
                                'tools.staticdir.dir': 'images'
                        },
                        '/js':     {
                                'tools.staticdir.on':  True,
                                'tools.staticdir.dir': 'js'
                        },
                        '/css':    {
                                'tools.staticdir.on':  True,
                                'tools.staticdir.dir': 'css'
                        },
        }
        app = cherrypy.tree.mount(WebInterface(), options['web_root'], conf)

        # auth
        if options['username'] != "" and options['password'] != "":
                checkpassword = cherrypy.lib.auth_basic.checkpassword_dict({options['username']: options['password']})
                app.merge({
                        '/': {
                                'tools.auth_basic.on':            True,
                                'tools.auth_basic.realm':         'SickBeard',
                                'tools.auth_basic.checkpassword': checkpassword
                        },
                        '/api':{
                                'tools.auth_basic.on':            False
                        },
                        '/api/builder':{
                                'tools.auth_basic.on':            True,
                                'tools.auth_basic.realm':         'SickBeard',
                                'tools.auth_basic.checkpassword': checkpassword
                        }
                })


        cherrypy.server.start()
        cherrypy.server.wait()

