"""
Tutorial - Sessions

Storing session data in CherryPy applications is very easy: cherrypy
provides a dictionary called "session" that represents the session
data for the current user. If you use RAM based sessions, you can store
any kind of object into that dictionary; otherwise, you are limited to
objects that can be pickled.
"""

import cherrypy


class HitCounter:
    
    _cp_config = {'tools.sessions.on': True}
    
    def index(self):
        # Increase the silly hit counter
        count = cherrypy.session.get('count', 0) + 1
        
        # Store the new value in the session dictionary
        cherrypy.session['count'] = count
        
        # And display a silly hit count message!
        return '''
            During your current session, you've viewed this
            page %s times! Your life is a patio of fun!
        ''' % count
    index.exposed = True


cherrypy.tree.mount(HitCounter())


if __name__ == '__main__':
    import os.path
    thisdir = os.path.dirname(__file__)
    cherrypy.quickstart(config=os.path.join(thisdir, 'tutorial.conf'))
