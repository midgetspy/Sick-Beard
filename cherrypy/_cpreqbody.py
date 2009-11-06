"""Request body processing for CherryPy.

When an HTTP request includes an entity body, it is often desirable to
provide that information to applications in a form other than the raw bytes.
Different content types demand different approaches. Examples:

 * For a GIF file, we want the raw bytes in a stream.
 * An HTML form is better parsed into its component fields, and each text field
    decoded from bytes to unicode.
 * A JSON body should be deserialized into a Python dict or list.

When the request contains a Content-Type header, the media type is used as a
key to look up a value in the 'request.body.processors' dict. If the full media
type is not found, then the major type is tried; for example, if no processor
is found for the 'image/jpeg' type, then we look for a processor for the 'image'
types altogether. If neither the full type nor the major type has a matching
processor, then a default processor is used (self.default_proc). For most
types, this means no processing is done, and the body is left unread as a
raw byte stream. Processors are configurable in an 'on_start_resource' hook.

Some processors, especially those for the 'text' types, attempt to decode bytes
to unicode. If the Content-Type request header includes a 'charset' parameter,
this is used to decode the entity. Otherwise, one or more default charsets may
be attempted, although this decision is up to each processor. If a processor
successfully decodes an Entity or Part, it should set the 'charset' attribute
on the Entity or Part to the name of the successful charset, so that
applications can easily re-encode or transcode the value if they wish.

If the Content-Type of the request entity is of major type 'multipart', then
the above parsing process, and possibly a decoding process, is performed for
each part.

For both the full entity and multipart parts, a Content-Disposition header may
be used to fill .name and .filename attributes on the request.body or the Part.
"""

import re
import tempfile
from urllib import unquote_plus

import cherrypy
from cherrypy.lib import httputil


# -------------------------------- Processors -------------------------------- #

def process_urlencoded(entity):
    """Read application/x-www-form-urlencoded data into entity.params."""
    qs = entity.fp.read()
    for charset in entity.attempt_charsets:
        try:
            params = {}
            for aparam in qs.split('&'):
                for pair in aparam.split(';'):
                    if not pair:
                        continue
                    
                    atoms = pair.split('=', 1)
                    if len(atoms) == 1:
                        atoms.append('')
                    
                    key = unquote_plus(atoms[0]).decode(charset)
                    value = unquote_plus(atoms[1]).decode(charset)
                    
                    if key in params:
                        if not isinstance(params[key], list):
                            params[key] = [params[key]]
                        params[key].append(value)
                    else:
                        params[key] = value
        except UnicodeDecodeError:
            pass
        else:
            entity.charset = charset
            break
    else:
        raise cherrypy.HTTPError(
            400, "The request entity could not be decoded. The following "
            "charsets were attempted: %s" % repr(entity.attempt_charsets))
        
    # Now that all values have been successfully parsed and decoded,
    # apply them to the entity.params dict.
    for key, value in params.items():
        if key in entity.params:
            if not isinstance(entity.params[key], list):
                entity.params[key] = [entity.params[key]]
            entity.params[key].append(value)
        else:
            entity.params[key] = value


def process_multipart(entity):
    """Read all multipart parts into entity.parts."""
    ib = u""
    if u'boundary' in entity.content_type.params:
        # http://tools.ietf.org/html/rfc2046#section-5.1.1
        # "The grammar for parameters on the Content-type field is such that it
        # is often necessary to enclose the boundary parameter values in quotes
        # on the Content-type line"
        ib = entity.content_type.params['boundary'].strip(u'"')
    
    if not re.match(u"^[ -~]{0,200}[!-~]$", ib):
        raise ValueError(u'Invalid boundary in multipart form: %r' % (ib,))
    
    ib = (u'--' + ib).encode('ascii')
    
    # Find the first marker
    while True:
        b = entity.readline()
        if not b:
            return
        
        b = b.strip()
        if b == ib:
            break
    
    # Read all parts
    while True:
        part = entity.part_class.from_fp(entity.fp, ib)
        entity.parts.append(part)
        part.process()
        if part.fp.done:
            break

def process_multipart_form_data(entity):
    """Read all multipart/form-data parts into entity.parts or entity.params."""
    process_multipart(entity)
    
    kept_parts = []
    for part in entity.parts:
        if part.name is None:
            kept_parts.append(part)
        else:
            if part.filename is None:
                # It's a regular field
                entity.params[part.name] = part.fullvalue()
            else:
                # It's a file upload. Retain the whole part so consumer code
                # has access to its .file and .filename attributes.
                entity.params[part.name] = part
    
    entity.parts = kept_parts

def _old_process_multipart(entity):
    """The behavior of 3.2 and lower. Deprecated and will be changed in 3.3."""
    process_multipart(entity)
    
    params = entity.params
    
    for part in entity.parts:
        if part.name is None:
            key = u'parts'
        else:
            key = part.name
        
        if part.filename is None:
            # It's a regular field
            value = part.fullvalue()
        else:
            # It's a file upload. Retain the whole part so consumer code
            # has access to its .file and .filename attributes.
            value = part
        
        if key in params:
            if not isinstance(params[key], list):
                params[key] = [params[key]]
            params[key].append(value)
        else:
            params[key] = value



# --------------------------------- Entities --------------------------------- #


class Entity(object):
    """An HTTP request body, or MIME multipart body."""
    
    __metaclass__ = cherrypy._AttributeDocstrings
    
    params = None
    params__doc = u"""
    If the request Content-Type is 'application/x-www-form-urlencoded' or
    multipart, this will be a dict of the params pulled from the entity
    body; that is, it will be the portion of request.params that come
    from the message body (sometimes called "POST params", although they
    can be sent with various HTTP method verbs). This value is set between
    the 'before_request_body' and 'before_handler' hooks (assuming that
    process_request_body is True)."""
    
    default_content_type = u'application/x-www-form-urlencoded'
    # http://tools.ietf.org/html/rfc2046#section-4.1.2:
    # "The default character set, which must be assumed in the
    # absence of a charset parameter, is US-ASCII."
    # However, many browsers send data in utf-8 with no charset.
    attempt_charsets = [u'utf-8']
    processors = {u'application/x-www-form-urlencoded': process_urlencoded,
                  u'multipart/form-data': process_multipart_form_data,
                  u'multipart': process_multipart,
                  }
    
    def __init__(self, fp, headers, params=None, parts=None):
        # Make an instance-specific copy of the class processors
        # so Tools, etc. can replace them per-request.
        self.processors = self.processors.copy()
        
        self.fp = fp
        self.headers = headers
        
        if params is None:
            params = {}
        self.params = params
        
        if parts is None:
            parts = []
        self.parts = parts
        
        # Content-Type
        self.content_type = headers.elements(u'Content-Type')
        if self.content_type:
            self.content_type = self.content_type[0]
        else:
            self.content_type = httputil.HeaderElement.from_str(
                self.default_content_type)
        
        # Copy the class 'attempt_charsets', prepending any Content-Type charset
        dec = self.content_type.params.get(u"charset", None)
        if dec:
            dec = dec.decode('ISO-8859-1')
            self.attempt_charsets = [dec] + [c for c in self.attempt_charsets
                                             if c != dec]
        else:
            self.attempt_charsets = self.attempt_charsets[:]
        
        # Length
        self.length = None
        clen = headers.get(u'Content-Length', None)
        # If Transfer-Encoding is 'chunked', ignore any Content-Length.
        if clen is not None and 'chunked' not in headers.get(u'Transfer-Encoding', ''):
            try:
                self.length = int(clen)
            except ValueError:
                pass
        
        # Content-Disposition
        self.name = None
        self.filename = None
        disp = headers.elements(u'Content-Disposition')
        if disp:
            disp = disp[0]
            if 'name' in disp.params:
                self.name = disp.params['name']
                if self.name.startswith(u'"') and self.name.endswith(u'"'):
                    self.name = self.name[1:-1]
            if 'filename' in disp.params:
                self.filename = disp.params['filename']
                if self.filename.startswith(u'"') and self.filename.endswith(u'"'):
                    self.filename = self.filename[1:-1]
    
    # The 'type' attribute is deprecated in 3.2; remove it in 3.3.
    type = property(lambda self: self.content_type)
    
    def read(self, size=None, fp_out=None):
        return self.fp.read(size, fp_out)
    
    def readline(self, size=None):
        return self.fp.readline(size)
    
    def readlines(self, sizehint=None):
        return self.fp.readlines(sizehint)
    
    def __iter__(self):
        return self
    
    def next(self):
        line = self.readline()
        if not line:
            raise StopIteration
        return line
    
    def read_into_file(self, fp_out=None):
        """Read the request body into fp_out (or make_file() if None). Return fp_out."""
        if fp_out is None:
            fp_out = self.make_file()
        self.read(fp_out=fp_out)
        return fp_out
    
    def make_file(self):
        """Return a file into which the request body will be read.
        
        By default, this will return a TemporaryFile. Override as needed."""
        return tempfile.TemporaryFile()
    
    def fullvalue(self):
        """Return this entity as a string, whether stored in a file or not."""
        if self.file:
            # It was stored in a tempfile. Read it.
            self.file.seek(0)
            value = self.file.read()
            self.file.seek(0)
        else:
            value = self.value
        return value
    
    def process(self):
        """Execute the best-match processor for the given media type."""
        proc = None
        ct = self.content_type.value
        try:
            proc = self.processors[ct]
        except KeyError:
            toptype = ct.split(u'/', 1)[0]
            try:
                proc = self.processors[toptype]
            except KeyError:
                pass
        if proc is None:
            self.default_proc()
        else:
            proc(self)
    
    def default_proc(self):
        # Leave the fp alone for someone else to read. This works fine
        # for request.body, but the Part subclasses need to override this
        # so they can move on to the next part.
        pass


class Part(Entity):
    """A MIME part entity, part of a multipart entity."""
    
    default_content_type = u'text/plain'
    # "The default character set, which must be assumed in the absence of a
    # charset parameter, is US-ASCII."
    attempt_charsets = [u'us-ascii', u'utf-8']
    # This is the default in stdlib cgi. We may want to increase it.
    maxrambytes = 1000
    
    def __init__(self, fp, headers, boundary):
        Entity.__init__(self, fp, headers)
        self.boundary = boundary
        self.file = None
        self.value = None
    
    def from_fp(cls, fp, boundary):
        headers = cls.read_headers(fp)
        return cls(fp, headers, boundary)
    from_fp = classmethod(from_fp)
    
    def read_headers(cls, fp):
        headers = httputil.HeaderMap()
        while True:
            line = fp.readline()
            if not line:
                # No more data--illegal end of headers
                raise EOFError(u"Illegal end of headers.")
            
            if line == '\r\n':
                # Normal end of headers
                break
            if not line.endswith('\r\n'):
                raise ValueError(u"MIME requires CRLF terminators: %r" % line)
            
            if line[0] in ' \t':
                # It's a continuation line.
                v = line.strip().decode(u'ISO-8859-1')
            else:
                k, v = line.split(":", 1)
                k = k.strip().decode(u'ISO-8859-1')
                v = v.strip().decode(u'ISO-8859-1')
            
            existing = headers.get(k)
            if existing:
                v = u", ".join((existing, v))
            headers[k] = v
        
        return headers
    read_headers = classmethod(read_headers)
    
    def read_lines_to_boundary(self, fp_out=None):
        """Read bytes from self.fp and return or write them to a file.
        
        If the 'fp_out' argument is None (the default), all bytes read are
        returned in a single byte string.
        
        If the 'fp_out' argument is not None, it must be a file-like object that
        supports the 'write' method; all bytes read will be written to the fp,
        and that fp is returned.
        """
        endmarker = self.boundary + "--"
        delim = ""
        prev_lf = True
        lines = []
        seen = 0
        while True:
            line = self.fp.readline(1 << 16)
            if not line:
                raise EOFError(u"Illegal end of multipart body.")
            if line.startswith("--") and prev_lf:
                strippedline = line.strip()
                if strippedline == self.boundary:
                    break
                if strippedline == endmarker:
                    self.fp.finish()
                    break
            
            line = delim + line
            
            if line.endswith("\r\n"):
                delim = "\r\n"
                line = line[:-2]
                prev_lf = True
            elif line.endswith("\n"):
                delim = "\n"
                line = line[:-1]
                prev_lf = True
            else:
                delim = ""
                prev_lf = False
            
            if fp_out is None:
                lines.append(line)
                seen += len(line)
                if seen > self.maxrambytes:
                    fp_out = self.make_file()
                    for line in lines:
                        fp_out.write(line)
            else:
                fp_out.write(line)
        
        if fp_out is None:
            result = ''.join(lines)
            for charset in self.attempt_charsets:
                try:
                    result = result.decode(charset)
                except UnicodeDecodeError:
                    pass
                else:
                    self.charset = charset
                    return result
            else:
                raise cherrypy.HTTPError(
                    400, "The request entity could not be decoded. The following "
                    "charsets were attempted: %s" % repr(self.attempt_charsets))
        else:
            fp_out.seek(0)
            return fp_out
    
    def default_proc(self):
        if self.filename:
            # Always read into a file if a .filename was given.
            self.file = self.read_into_file()
        else:
            result = self.read_lines_to_boundary()
            if isinstance(result, basestring):
                self.value = result
            else:
                self.file = result
    
    def read_into_file(self, fp_out=None):
        """Read the request body into fp_out (or make_file() if None). Return fp_out."""
        if fp_out is None:
            fp_out = self.make_file()
        self.read_lines_to_boundary(fp_out=fp_out)
        return fp_out

Entity.part_class = Part


class Infinity(object):
    def __cmp__(self, other):
        return 1
    def __sub__(self, other):
        return self
inf = Infinity()


comma_separated_headers = ['Accept', 'Accept-Charset', 'Accept-Encoding',
    'Accept-Language', 'Accept-Ranges', 'Allow', 'Cache-Control', 'Connection',
    'Content-Encoding', 'Content-Language', 'Expect', 'If-Match',
    'If-None-Match', 'Pragma', 'Proxy-Authenticate', 'Te', 'Trailer',
    'Transfer-Encoding', 'Upgrade', 'Vary', 'Via', 'Warning', 'Www-Authenticate']


class SizedReader:
    
    def __init__(self, fp, length, maxbytes, bufsize=8192, has_trailers=False):
        # Wrap our fp in a buffer so peek() works
        self.fp = fp
        self.length = length
        self.maxbytes = maxbytes
        self.buffer = ''
        self.bufsize = bufsize
        self.bytes_read = 0
        self.done = False
        self.has_trailers = has_trailers
    
    def read(self, size=None, fp_out=None):
        """Read bytes from the request body and return or write them to a file.
        
        A number of bytes less than or equal to the 'size' argument are read
        off the socket. The actual number of bytes read are tracked in
        self.bytes_read. The number may be smaller than 'size' when 1) the
        client sends fewer bytes, 2) the 'Content-Length' request header
        specifies fewer bytes than requested, or 3) the number of bytes read
        exceeds self.maxbytes (in which case, 413 is raised).
        
        If the 'fp_out' argument is None (the default), all bytes read are
        returned in a single byte string.
        
        If the 'fp_out' argument is not None, it must be a file-like object that
        supports the 'write' method; all bytes read will be written to the fp,
        and None is returned.
        """
        
        if self.length is None:
            if size is None:
                remaining = inf
            else:
                remaining = size
        else:
            remaining = self.length - self.bytes_read
            if size and size < remaining:
                remaining = size
        if remaining == 0:
            self.finish()
            if fp_out is None:
                return ''
            else:
                return None
        
        chunks = []
        
        # Read bytes from the buffer.
        if self.buffer:
            if remaining is inf:
                data = self.buffer
                self.buffer = ''
            else:
                data = self.buffer[:remaining]
                self.buffer = self.buffer[remaining:]
            datalen = len(data)
            remaining -= datalen
            
            # Check lengths.
            self.bytes_read += datalen
            if self.maxbytes and self.bytes_read > self.maxbytes:
                raise cherrypy.HTTPError(413)
            
            # Store the data.
            if fp_out is None:
                chunks.append(data)
            else:
                fp_out.write(data)
        
        # Read bytes from the socket.
        while remaining > 0:
            chunksize = min(remaining, self.bufsize)
            try:
                data = self.fp.read(chunksize)
            except Exception, e:
                if e.__class__.__name__ == 'MaxSizeExceeded':
                    # Post data is too big
                    raise cherrypy.HTTPError(
                        413, "Maximum request length: %r" % e.args[1])
                else:
                    raise
            if not data:
                self.finish()
                break
            datalen = len(data)
            remaining -= datalen
            
            # Check lengths.
            self.bytes_read += datalen
            if self.maxbytes and self.bytes_read > self.maxbytes:
                raise cherrypy.HTTPError(413)
            
            # Store the data.
            if fp_out is None:
                chunks.append(data)
            else:
                fp_out.write(data)
        
        if fp_out is None:
            return ''.join(chunks)
    
    def readline(self, size=None):
        """Read a line from the request body and return it."""
        chunks = []
        while size is None or size > 0:
            chunksize = self.bufsize
            if size is not None and size < self.bufsize:
                chunksize = size
            data = self.read(chunksize)
            if not data:
                break
            pos = data.find('\n') + 1
            if pos:
                chunks.append(data[:pos])
                remainder = data[pos:]
                self.buffer += remainder
                self.bytes_read -= len(remainder)
                break
            else:
                chunks.append(data)
        return ''.join(chunks)
    
    def readlines(self, sizehint=None):
        """Read lines from the request body and return them."""
        if self.length is not None:
            if sizehint is None:
                sizehint = self.length - self.bytes_read
            else:
                sizehint = min(sizehint, self.length - self.bytes_read)
        
        lines = []
        seen = 0
        while True:
            line = self.readline()
            if not line:
                break
            lines.append(line)
            seen += len(line)
            if seen >= sizehint:
                break
        return lines
    
    def finish(self):
        self.done = True
        if self.has_trailers and hasattr(self.fp, 'read_trailer_lines'):
            self.trailers = {}
            
            try:
                for line in self.fp.read_trailer_lines():
                    if line[0] in ' \t':
                        # It's a continuation line.
                        v = line.strip()
                    else:
                        try:
                            k, v = line.split(":", 1)
                        except ValueError:
                            raise ValueError("Illegal header line.")
                        k = k.strip().title()
                        v = v.strip()
                    
                    if k in comma_separated_headers:
                        existing = self.trailers.get(envname)
                        if existing:
                            v = ", ".join((existing, v))
                    self.trailers[k] = v
            except Exception, e:
                if e.__class__.__name__ == 'MaxSizeExceeded':
                    # Post data is too big
                    raise cherrypy.HTTPError(
                        413, "Maximum request length: %r" % e.args[1])
                else:
                    raise


class RequestBody(Entity):
    
    # Don't parse the request body at all if the client didn't provide
    # a Content-Type header. See http://www.cherrypy.org/ticket/790
    default_content_type = u''
    
    bufsize = 8 * 1024
    maxbytes = None
    
    def __init__(self, fp, headers, params=None, request_params=None):
        Entity.__init__(self, fp, headers, params)
        
        # http://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.7.1
        # When no explicit charset parameter is provided by the
        # sender, media subtypes of the "text" type are defined
        # to have a default charset value of "ISO-8859-1" when
        # received via HTTP.
        if self.content_type.value.startswith('text/'):
            for c in (u'ISO-8859-1', u'iso-8859-1', u'Latin-1', u'latin-1'):
                if c in self.attempt_charsets:
                    break
            else:
                self.attempt_charsets.append(u'ISO-8859-1')
        
        # Temporary fix while deprecating passing .parts as .params.
        self.processors[u'multipart'] = _old_process_multipart
        
        if request_params is None:
            request_params = {}
        self.request_params = request_params
    
    def process(self):
        """Include body params in request params."""
        # "The presence of a message-body in a request is signaled by the
        # inclusion of a Content-Length or Transfer-Encoding header field in
        # the request's message-headers."
        # It is possible to send a POST request with no body, for example;
        # however, app developers are responsible in that case to set
        # cherrypy.request.process_body to False so this method isn't called.
        h = cherrypy.serving.request.headers
        if u'Content-Length' not in h and u'Transfer-Encoding' not in h:
            raise cherrypy.HTTPError(411)
        
        self.fp = SizedReader(self.fp, self.length,
                              self.maxbytes, bufsize=self.bufsize,
                              has_trailers='Trailer' in h)
        super(RequestBody, self).process()
        
        # Body params should also be a part of the request_params
        # add them in here.
        request_params = self.request_params
        for key, value in self.params.items():
            # Python 2 only: keyword arguments must be byte strings (type 'str').
            if isinstance(key, unicode):
                key = key.encode('ISO-8859-1')
            
            if key in request_params:
                if not isinstance(request_params[key], list):
                    request_params[key] = [request_params[key]]
                request_params[key].append(value)
            else:
                request_params[key] = value

