import datetime
import os.path
import re

import regexes

from sickbeard import logger

class NameParser(object):
    def __init__(self, file_name=True):

        self.file_name = file_name
        self.compiled_regexes = []
        self._compile_regexes()

    def _compile_regexes(self):
        for (cur_pattern_name, cur_pattern) in regexes.ep_regexes:
            try:
                cur_regex = re.compile(cur_pattern, re.VERBOSE | re.IGNORECASE)
            except re.error, errormsg:
                logger.log(u"WARNING: Invalid episode_pattern, %s. %s" % (errormsg, cur_regex.pattern))
            else:
                self.compiled_regexes.append((cur_pattern_name, cur_regex))

    def _parse_string(self, name):
        
        if not name:
            return None
        
        for (cur_regex_name, cur_regex) in self.compiled_regexes:
            match = cur_regex.match(name)

            if not match:
                continue
            
            result = ParseResult(name)
            result.which_regex = [cur_regex_name]
            
            #print cur_regex_name, match.groupdict()
            
            named_groups = match.groupdict().keys()
            
            if 'series_name' in named_groups:
                result.series_name = match.group('series_name')
            
            if 'season_num' in named_groups:
                result.season_number = int(match.group('season_num'))
            
            if 'ep_num' in named_groups:
                ep_num = self._convert_number(match.group('ep_num'))
                if 'extra_ep_num' in named_groups and match.group('extra_ep_num'):
                    result.episode_numbers = range(ep_num, self._convert_number(match.group('extra_ep_num'))+1)
                else:
                    result.episode_numbers = [ep_num]

            if 'air_year' in named_groups and 'air_month' in named_groups and 'air_day' in named_groups:
                year = int(match.group('air_year'))
                month = int(match.group('air_month'))
                day = int(match.group('air_day'))
                
                # make an attempt to detect YYYY-DD-MM formats
                if month > 12:
                    tmp_month = month
                    month = day
                    day = tmp_month

                result.air_date = datetime.date(year, month, day)

            if 'extra_info' in named_groups:
                result.extra_info = match.group('extra_info')
            
            if 'release_group' in named_groups:
                result.release_group = match.group('release_group')
            
            return result
        
        return None

    def _combine_results(self, first, second, attr):
        # if the first doesn't exist then return the second or nothing
        if not first:
            if not second:
                return None
            else:
                return getattr(second, attr)

        # if the second doesn't exist then return the first
        if not second:
            return getattr(first, attr)
        
        a = getattr(first, attr)
        b = getattr(second, attr)
        
        # if a is good use it
        if a != None or (type(a) == list and len(a)):
            return a 
        # if not use b (if b isn't set it'll just be default)
        else:
            return b 

    def _convert_number(self, number):
        if type(number) == int:
            return number
        
        # the lazy way
        if number == 'i': return 1
        if number == 'ii': return 2
        if number == 'iii': return 3
        if number == 'iv': return 4
        if number == 'v': return 5
        if number == 'vi': return 6
        if number == 'vii': return 7
        if number == 'viii': return 8
        if number == 'ix': return 9
        if number == 'x': return 10
        if number == 'xi': return 11
        if number == 'xii': return 12
        if number == 'xiii': return 13
        if number == 'xiv': return 14
        if number == 'xv': return 15

        return int(number)

    def parse(self, name):
        
        # break it into parts if there are any (dirname, file name, extension)
        dir_name, file_name = os.path.split(name)
        ext_match = re.match('(.*)\.\w{3,4}$', file_name)
        if ext_match and self.file_name:
            base_file_name = ext_match.group(1)
        else:
            base_file_name = file_name
        
        # set up a result to use
        final_result = ParseResult(name)
        
        # try parsing the file name
        file_name_result = self._parse_string(base_file_name)
        
        # parse the dirname for extra info if needed
        dir_name_result = self._parse_string(dir_name)
        
        # build the ParseResult object
        final_result.series_name = self._combine_results(file_name_result, dir_name_result, 'series_name')
        final_result.season_number = self._combine_results(file_name_result, dir_name_result, 'season_number')
        final_result.episode_numbers = self._combine_results(file_name_result, dir_name_result, 'episode_numbers')
        final_result.extra_info = self._combine_results(file_name_result, dir_name_result, 'extra_info')
        
        # if the dirname has a release group I believe it over the filename
        final_result.release_group = self._combine_results(dir_name_result, file_name_result, 'release_group')

        final_result.which_regex = []
        if final_result == file_name_result:
            final_result.which_regex = file_name_result.which_regex
        elif final_result == dir_name_result:
            final_result.which_regex = dir_name_result.which_regex
        else:
            if file_name_result:
                final_result.which_regex += file_name_result.which_regex
            if dir_name_result:
                final_result.which_regex += dir_name_result.which_regex

        # return it
        return final_result

class ParseResult(object):
    def __init__(self,
                 original_name,
                 series_name=None,
                 season_number=None,
                 episode_numbers=None,
                 extra_info=None,
                 release_group=None,
                 air_date=None
                 ):
        self.original_name = original_name
        
        self.series_name = series_name
        self.season_number = season_number
        if not episode_numbers:
            self.episode_numbers = []
        else:
            self.episode_numbers = episode_numbers

        self.extra_info = extra_info
        self.release_group = release_group
        
        self.air_date = None
        
        self.which_regex = None
    
    def __eq__(self, other):
        if not other:
            return False
        
        if self.series_name != other.series_name:
            return False
        if self.season_number != other.season_number:
            return False
        if self.episode_numbers != other.episode_numbers:
            return False
        if self.extra_info != other.extra_info:
            return False
        if self.release_group != other.release_group:
            return False
        if self.air_date != other.air_date:
            return False
        
        return True

    def __str__(self):
        to_return = str(self.series_name) + ' - '
        if self.season_number != None:
            to_return += 'S'+str(self.season_number)
        if len(self.episode_numbers):
            for e in self.episode_numbers:
                to_return += 'E'+str(e)

        if self.season_number == None and len(self.episode_numbers) == 0 and self.air_date:
            to_return += str(self.air_date)

        if self.extra_info:
            to_return += ' - ' + self.extra_info
        if self.release_group:
            to_return += ' (' + self.release_group + ')'

        return to_return 

    def _is_air_by_date(self):
        return self.season_number == None and len(self.episode_numbers) == 0 and self.air_date
    air_by_date = property(_is_air_by_date)

class InvalidNameException(Exception):
    "The given name is not valid"