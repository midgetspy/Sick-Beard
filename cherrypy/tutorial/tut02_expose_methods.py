"""
Tutorial - Multiple methods

This tutorial shows you how to link to other methods of your request
handler.
"""

import cherrypy

class HelloWorld:
    
    def index(self):
        # Let's link to another method here.
        return 'We have an <a href="showMessage">important message</a> for you!'
    index.exposed = True
    
    def showMessage(self):
        # Here's the important message!
        return "Hello world!"
    showMessage.exposed = True

cherrypy.tree.mount(HelloWorld())

if __name__ == '__main__':
    import os.path
    thisdir = os.path.dirname(__file__)
    cherrypy.quickstart(config=os.path.join(thisdir, 'tutorial.conf'))

