#!/usr/bin/env python
#
# This file is part of aDBa.
#
# aDBa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# aDBa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with aDBa.  If not, see <http://www.gnu.org/licenses/>.
from random import shuffle

class AniDBMaper:
    
    blacklist = ('unused','retired','reserved')
    
    def getAnimeBitsA(self,amask):
        map = self.getAnimeMapA()
        return self._getBitChain(map,amask);
    
    def getAnimeCodesA(self,aBitChain):
        amap = self.getAnimeMapA()
        return self._getCodes(amap,aBitChain);

        
    def getFileBitsF(self,fmask):
        fmap = self.getFileMapF()
        return self._getBitChain(fmap,fmask)
    
    def getFileCodesF(self,bitChainF):
        fmap = self.getFileMapF()
        return self._getCodes(fmap,bitChainF)     

       
    def getFileBitsA(self,amask):
        amap = self.getFileMapA()
        return self._getBitChain(amap,amask)
    
    def getFileCodesA(self,bitChainA):
        amap = self.getFileMapA()
        return self._getCodes(amap,bitChainA)
     
    
    def _getBitChain(self,map,wanted):
        """Return an hex string with the correct bit set corresponding to the wanted fields in the map
        """
        bit = 0        
        for index,field in enumerate(map):
            if field in wanted and not field in self.blacklist:
                bit = bit ^ (1<<len(map)-index-1)
                
        bit = str(hex(bit)).lstrip("0x").rstrip("L")
        bit = ''.join(["0" for unused in xrange(len(map)/4 - len(bit))])+bit
        return bit
    
    def _getCodes(self,map,bitChain):
        """Returns a list with the corresponding fields as set in the bitChain (hex string)
        """
        codeList=[]
        bitChain = int(bitChain,16)
        mapLength = len(map)
        for i in reversed(range(mapLength)):
            if bitChain&(2**i):
                codeList.append(map[mapLength-i-1])
        return codeList 
    
    def getAnimeMapA(self):
        # each line is one byte
        # only chnage this if the api changes
        map = ['aid','unused','year','type','related_aid_list','related_aid_type','category_list','category_weight_list',
                 'romaji_name','kanji_name','english_name','other_name','short_name_list','synonym_list','retired','retired',
                 'episodes','highest_episode_number','special_ep_count','air_date','end_date','url','picname','category_id_list',
                 'rating','vote_count','temp_rating','temp_vote_count','average_review_rating','review_count','award_list','is_18_restricted',
                 'anime_planet_id','ANN_id','allcinema_id','AnimeNfo_id','unused','unused','unused','date_record_updated',
                 'character_id_list','creator_id_list','main_creator_id_list','main_creator_name_list','unused','unused','unused','unused',
                 'specials_count','credits_count','other_count','trailer_count','parody_count','unused','unused','unused']
        return map
    
    def getFileMapF(self):
        # each line is one byte
        # only chnage this if the api changes
        map = ['unused','aid','eid','gid','mylist_id','list_other_episodes','IsDeprecated','state',
                'size','ed2k','md5','sha1','crc32','unused','unused','reserved',
                'quality','source','audio_codec_list','audio_bitrate_list','video_codec','video_bitrate','video_resolution','file_type_extension',
                'dub_language','sub_language','length_in_seconds','description','aired_date','unused','unused','anidb_file_name',
                'mylist_state','mylist_filestate','mylist_viewed','mylist_viewdate','mylist_storage','mylist_source','mylist_other','unused']
        return map    
    
    def getFileMapA(self):
        # each line is one byte
        # only chnage this if the api changes
        map = ['anime_total_episodes','highest_episode_number','year','type','related_aid_list','related_aid_type','category_list','reserved',
                'romaji_name','kanji_name','english_name','other_name','short_name_list','synonym_list','retired','retired',
                'epno','ep_name','ep_romaji_name','ep_kanji_name','episode_rating','episode_vote_count','unused','unused',
                'group_name','group_short_name','unused','unused','unused','unused','unused','date_aid_record_updated']
        return map 

    def checkMapping(self,verbos=False):
        
        print "------"
        print "File F: "+ str(self.checkMapFileF(verbos))
        print "------"
        print "File A: "+ str(self.checkMapFileA(verbos))
        
    
    def checkMapFileF(self,verbos=False):
        getGeneralMap = lambda: self.getFileMapF()
        getBits = lambda x: self.getFileBitsF(x) 
        getCodes = lambda x: self.getFileCodesF(x)
        return self._checkMapGeneral(getGeneralMap,getBits,getCodes,verbos=verbos)
   
    def checkMapFileA(self,verbos=False):
        getGeneralMap = lambda: self.getFileMapA()
        getBits = lambda x: self.getFileBitsA(x) 
        getCodes = lambda x: self.getFileCodesA(x)
        return self._checkMapGeneral(getGeneralMap,getBits,getCodes,verbos=verbos)
    
    def _checkMapGeneral(self,getGeneralMap,getBits,getCodes,verbos=False):
        map = getGeneralMap()
        shuffle(map)
        mask = [elem for elem in map if elem not in self.blacklist][:5]
        bits = getBits(mask)
        mask_re = getCodes(bits)
        bits_re = getBits(mask_re)
        if verbos:
            print mask
            print mask_re
            print bits
            print bits_re
            print "bits are:"+ str((bits_re == bits))
            print "map is :"+ str((sorted(mask_re) == sorted(mask)))
        return (bits_re == bits) and sorted(mask_re) == sorted(mask)
