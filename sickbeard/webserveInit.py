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

from sickbeard import logger
from sickbeard.webserve import WebInterface

def initWebServer(options = {}):
        options.setdefault('port',      8081)
        options.setdefault('host',      '0.0.0.0')
        options.setdefault('log_dir',   None)
        options.setdefault('username',    '')
        options.setdefault('password',    '')
        options.setdefault('web_root',   '/')
        assert isinstance(options['port'], int)
        assert 'data_root' in options

        # cherrypy setup
        cherrypy.config.update({
                'server.socket_port': options['port'],
                'server.socket_host': options['host'],
                'log.screen':         False,
        })

        #HTTP Errors
        def http_error_401_hander(status, message, traceback, version):
            import binascii
            import base64
            args = [status, message, traceback, version]

            logger.log(u"Authentication error, check cherrypy log for more details", logger.WARNING)
            logger.log(u" - IP = %s" % str(cherrypy.request.remote.ip), logger.WARNING)
            auth_header = cherrypy.request.headers.get('authorization')
            if auth_header:
                try:
                    scheme, data = auth_header.split(' ', 1)
                    username, password = base64.decodestring(data).split(':',1)
                    logger.log(u" - Username = %s" % str(username), logger.WARNING)
                except (ValueError, binascii.Error):
                    raise cherrypy.HTTPError(400, 'Bad Request')
            else:
                logger.log(u" - No authentication supplied")
            return "<html><body><h1>401 - Unauthorized</h1></body></html>"
        cherrypy.config.update({'error_page.401' : http_error_401_hander})

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
                        }
                })

        cherrypy.server.start()
        cherrypy.server.wait()

