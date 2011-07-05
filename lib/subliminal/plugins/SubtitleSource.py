# -*- coding: utf-8 -*-
#
# Subliminal - Subtitles, faster than your thoughts
# Copyright (c) 2011 Antoine Bertin <diaoulael@gmail.com>
#
# Subliminal is free software; you can redistribute it and/or modify it under
# the terms of the Lesser GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# Subliminal is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Lesser GNU General Public License for more details.
#
# You should have received a copy of the Lesser GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import ConfigParser
import PluginBase
import traceback
import urllib
import urllib2
import xml.dom.minidom


class SubtitleSource(PluginBase.PluginBase):
    site_url = 'http://www.subtitlesource.org'
    site_name = 'SubtitleSource'
    server_url = 'http://www.subtitlesource.org/api/%s/3.0/xmlsearch'
    multi_languages_queries = True
    multi_filename_queries = False
    api_based = True
    _plugin_languages = {"en": "English",
            "sv": "Swedish",
            "da": "Danish",
            "fi": "Finnish",
            "no": "Norwegian",
            "fr": "French",
            "es": "Spanish",
            "is": "Icelandic"}

    def __init__(self, config_dict=None):
        super(SubtitleSource, self).__init__(self._plugin_languages, config_dict)
        if config_dict and "subtitlesource_key" in config_dict:
            self.server_url = self.server_url % config_dict["subtitlesource_key"]
        else:
            self.logger.error(u'SubtitleSource API Key is mandatory for this plugin')
            raise Exception('SubtitleSource API Key is mandatory for this plugin')

    def list(self, filenames, languages):
        """Main method to call when you want to list subtitles"""
        filepath = filenames[0]
        fname = self.getFileName(filepath)
        subs = self.query(fname, languages)
        if not subs and fname.rfind(".[") > 0:
            # Try to remove the [VTV] or [EZTV] at the end of the file
            teamless_filename = fname[0:fname.rfind(".[")]
            subs = self.query(teamless_filename, languages)
            return subs
        else:
            return subs

    def query(self, token, languages=None):
        """Makes a query on SubtitlesSource and returns info (link, lang) about found subtitles"""
        self.logger.debug(u"Local file is: %s " % token)
        sublinks = []
        if not languages:  # langs is empty of None
            languages = ["all"]
        else:  # parse each lang to generate the equivalent lang
            languages = [self._plugin_languages[l] for l in languages if l in self._plugin_languages.keys()]
        # Get the CD part of this
        metaData = self.guessFileData(token)
        multipart = metaData.get('part', None)
        part = metaData.get('part')
        if not part:  # part will return None if not found using the regex
            part = 1
        for lang in languages:
            searchurl = "%s/%s/%s/0" % (self.server_url, urllib.quote(token), lang)
            self.logger.debug(u"dl'ing %s" % searchurl)
            page = urllib2.urlopen(searchurl, timeout=self.timeout)
            xmltree = xml.dom.minidom.parse(page)
            subs = xmltree.getElementsByTagName("sub")
            for sub in subs:
                sublang = self.getRevertLanguage(self.getValue(sub, "language"))
                if languages and not sublang in languages:
                    continue  # The language of this sub is not wanted => Skip
                if multipart and not int(self.getValue(sub, 'cd')) > 1:
                    continue  # The subtitle is not a multipart
                dllink = "http://www.subtitlesource.org/download/text/%s/%s" % (self.getValue(sub, "id"), part)
                self.logger.debug(u"Link added: %s (%s)" % (dllink, sublang))
                result = {}
                result["release"] = self.getValue(sub, "releasename")
                result["link"] = dllink
                result["page"] = dllink
                result["lang"] = sublang
                releaseMetaData = self.guessFileData(result['release'])
                teams = set(metaData['teams'])
                srtTeams = set(releaseMetaData['teams'])
                self.logger.debug(u"Analyzing: %s " % result['release'])
                self.logger.debug(u"Local file has: %s " % metaData['teams'])
                self.logger.debug(u"Remote sub has: %s " % releaseMetaData['teams'])
                if result['release'].startswith(token) or (releaseMetaData['name'] == metaData['name'] and releaseMetaData['type'] == metaData['type'] and (teams.issubset(srtTeams) or srtTeams.issubset(teams))):
                    sublinks.append(result)
        return sublinks

    def download(self, subtitle):
        """Main method to call when you want to download a subtitle"""
        suburl = subtitle["link"]
        videofilename = subtitle["filename"]
        srtfilename = videofilename.rsplit(".", 1)[0] + self.getExtension(subtitle)
        self.downloadFile(suburl, srtfilename)
        return srtfilename

    def getValue(self, sub, tagName):
        for node in sub.childNodes:
            if node.nodeType == node.ELEMENT_NODE and node.tagName == tagName:
                return node.childNodes[0].nodeValue
