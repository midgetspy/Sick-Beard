"""Tests for various MIME issues, including the safe_multipart Tool."""

from cherrypy.test import test
test.prefer_parent_path()

import cherrypy


def setup_server():
    
    class Root:
        
        def multipart(self, parts):
            return repr(parts)
        multipart.exposed = True
        
        def flashupload(self, Filedata, Upload, Filename):
            return ("Upload: %r, Filename: %r, Filedata: %r" % 
                    (Upload, Filename, Filedata.file.read()))
        flashupload.exposed = True
    
    cherrypy.config.update({'server.max_request_body_size': 0})
    cherrypy.tree.mount(Root())


#                             Client-side code                             #

from cherrypy.test import helper

class MultipartTest(helper.CPWebCase):
    
    def test_multipart(self):
        text_part = u"This is the text version"
        html_part = u"""<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html>
<head>
 <meta content="text/html;charset=ISO-8859-1" http-equiv="Content-Type">
</head>
<body bgcolor="#ffffff" text="#000000">

This is the <strong>HTML</strong> version
</body>
</html>
"""
        body = '\r\n'.join([
            "--123456789",
            "Content-Type: text/plain; charset='ISO-8859-1'",
            "Content-Transfer-Encoding: 7bit",
            "",
            text_part,
            "--123456789",
            "Content-Type: text/html; charset='ISO-8859-1'",
            "",
            html_part,
            "--123456789--"])
        headers = [
            ('Content-Type', 'multipart/mixed; boundary=123456789'),
            ('Content-Length', len(body)),
            ]
        self.getPage('/multipart', headers, "POST", body)
        self.assertBody(repr([text_part, html_part]))


class SafeMultipartHandlingTest(helper.CPWebCase):
    
    def test_Flash_Upload(self):
        headers = [
            ('Accept', 'text/*'),
            ('Content-Type', 'multipart/form-data; '
                 'boundary=----------KM7Ij5cH2KM7Ef1gL6ae0ae0cH2gL6'),
            ('User-Agent', 'Shockwave Flash'),
            ('Host', 'www.example.com:8080'),
            ('Content-Length', '499'),
            ('Connection', 'Keep-Alive'),
            ('Cache-Control', 'no-cache'),
            ]
        filedata = ('<?xml version="1.0" encoding="UTF-8"?>\r\n'
                    '<projectDescription>\r\n'
                    '</projectDescription>\r\n')
        body = (
            '------------KM7Ij5cH2KM7Ef1gL6ae0ae0cH2gL6\r\n'
            'Content-Disposition: form-data; name="Filename"\r\n'
            '\r\n'
            '.project\r\n'
            '------------KM7Ij5cH2KM7Ef1gL6ae0ae0cH2gL6\r\n'
            'Content-Disposition: form-data; '
                'name="Filedata"; filename=".project"\r\n'
            'Content-Type: application/octet-stream\r\n'
            '\r\n'
            + filedata + 
            '\r\n'
            '------------KM7Ij5cH2KM7Ef1gL6ae0ae0cH2gL6\r\n'
            'Content-Disposition: form-data; name="Upload"\r\n'
            '\r\n'
            'Submit Query\r\n'
            # Flash apps omit the trailing \r\n on the last line:
            '------------KM7Ij5cH2KM7Ef1gL6ae0ae0cH2gL6--'
            )
        self.getPage('/flashupload', headers, "POST", body)
        self.assertBody("Upload: u'Submit Query', Filename: u'.project', "
                        "Filedata: %r" % filedata)


if __name__ == '__main__':
    helper.testmain()
