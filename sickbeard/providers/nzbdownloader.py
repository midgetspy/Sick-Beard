'''

@author: Guillaume
'''

class NZBDownloader(object):
    '''
    classdocs
    '''
    def __init__(self):
        self.lastRequestTime = None
        
        
class NZBSearchResult(object):

    def __init__(self, nzbdata, sizeInMegs, url):
        self.nzbdata = nzbdata
        self.sizeInMegs = sizeInMegs
        self.url = url
