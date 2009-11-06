import sys
import cherrypy

if sys.version_info >= (2, 6):
    # Python 2.6: simplejson is part of the standard library
    import json
else:
    try:
        import simplejson as json
    except ImportError:
        json = None

if json is None:
    def json_decode(s):
        raise ValueError('No JSON library is available')
    def json_encode(s):
        raise ValueError('No JSON library is available')
else:
    json_decode = json.JSONDecoder().decode
    json_encode = json.JSONEncoder().iterencode

def json_in(force=True, debug=False):
    request = cherrypy.serving.request
    def json_processor(entity):
        """Read application/json data into request.json."""
        if not entity.headers.get(u"Content-Length", u""):
            raise cherrypy.HTTPError(411)
        
        body = entity.fp.read()
        try:
            request.json = json_decode(body)
        except ValueError:
            raise cherrypy.HTTPError(400, 'Invalid JSON document')
    if force:
        request.body.processors.clear()
        request.body.default_proc = cherrypy.HTTPError(
            415, 'Expected an application/json content type')
    request.body.processors[u'application/json'] = json_processor

def json_out(debug=False):
    request = cherrypy.serving.request
    response = cherrypy.serving.response
    
    real_handler = request.handler
    def json_handler(*args, **kwargs):
        response.headers['Content-Type'] = 'application/json'
        value = real_handler(*args, **kwargs)
        return json_encode(value)
    request.handler = json_handler

