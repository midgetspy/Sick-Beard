# coding=UTF-8
# Author: Daniel Hobe <hobe@gmail.com>
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
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

import peewee
import logging

from sickbeard import logger
from sickbeard import common

peewee.logger = logging.getLogger('sickbeard')

maindb = peewee.SqliteDatabase(None, threadlocals=True)

class BaseSickbeardModel(peewee.Model):
    class Meta:
        database = maindb


class DbVersion(BaseSickbeardModel):
    db_version = peewee.IntegerField(null=True)

    class Meta:
        db_table = 'db_version'


class History(BaseSickbeardModel):
    action = peewee.IntegerField(null=True)
    date = peewee.DateTimeField(null=True)
    episode = peewee.IntegerField(null=True)
    provider = peewee.TextField(null=True)
    quality = peewee.IntegerField(null=True)
    resource = peewee.TextField(null=True)
    season = peewee.IntegerField(null=True)
    showid = peewee.IntegerField(null=True)

    class Meta:
        db_table = 'history'


class Info(BaseSickbeardModel):
    last_backlog = peewee.IntegerField(null=True)
    last_tvdb = peewee.IntegerField(null=True)

    class Meta:
        db_table = 'info'


class TvShow(BaseSickbeardModel):
    show_name = peewee.CharField(null=True)
    air_by_date = peewee.BooleanField(default=False)
    airs = peewee.CharField(null=True)
    flatten_folders = peewee.BooleanField(default=False)
    genre = peewee.CharField(null=True)
    lang = peewee.CharField(null=True)
    location = peewee.TextField(null=True)
    network = peewee.TextField(null=True)
    paused = peewee.BooleanField(default=False)
    #TODO: what should this be set to?
    quality = peewee.IntegerField(default=common.ANY)
    runtime = peewee.IntegerField(default=0)
    show_id = peewee.PrimaryKeyField()
    show_name = peewee.TextField(null=True)
    startyear = peewee.DateField(null=True)
    status = peewee.CharField(null=True)
    tvdb_id = peewee.IntegerField(null=True)
    tvr_id = peewee.IntegerField(null=True)
    tvr_name = peewee.TextField(null=True)

    class Meta:
        db_table = 'tv_shows'

    @property
    def episodes(self):
        return TvEpisode.select().where(TvEpisode.showid == self.tvdb_id)


class TvEpisode(BaseSickbeardModel):
    airdate = peewee.IntegerField(null=True)
    description = peewee.TextField(null=True)
    episode = peewee.IntegerField(null=True)
    episode_id = peewee.PrimaryKeyField()
    file_size = peewee.IntegerField(null=True)
    hasnfo = peewee.BooleanField(default=False)
    hastbn = peewee.BooleanField(default=False)
    location = peewee.TextField(null=True)
    name = peewee.TextField(null=True)
    release_name = peewee.TextField(null=True)
    season = peewee.IntegerField(null=True)
    showid = peewee.IntegerField()
    status = peewee.IntegerField(null=True)
    tvdbid = peewee.IntegerField(null=True)

    @property
    def show(self):
        return TvShow.select().where(TvShow.tvdb_id == self.showid).get()

    class Meta:
        db_table = 'tv_episodes'


cachedb = peewee.SqliteDatabase(None)

class CacheBaseModel(peewee.Model):
    class Meta:
        database = cachedb


class DbVersion(CacheBaseModel):
    db_version = peewee.IntegerField(null=True)

    class Meta:
        db_table = 'db_version'


class Lastupdate(CacheBaseModel):
    provider = peewee.TextField(null=True)
    time = peewee.IntegerField(null=True)

    class Meta:
        db_table = 'lastUpdate'


class SceneException(CacheBaseModel):
    exception_id = peewee.PrimaryKeyField()
    show_name = peewee.TextField(null=True)
    tvdb_id = peewee.IntegerField(null=True)

    class Meta:
        db_table = 'scene_exceptions'


class SceneName(CacheBaseModel):
    name = peewee.TextField(null=True)
    tvdb_id = peewee.IntegerField(null=True)

    class Meta:
        db_table = 'scene_names'


class WombleSIndex(CacheBaseModel):
    episodes = peewee.TextField(null=True)
    name = peewee.TextField(null=True)
    quality = peewee.TextField(null=True)
    season = peewee.IntegerField(null=True)
    time = peewee.IntegerField(null=True)
    tvdbid = peewee.IntegerField(null=True)
    tvrid = peewee.IntegerField(null=True)
    url = peewee.TextField(null=True)

    class Meta:
        db_table = 'womble_s_index'
