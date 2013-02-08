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

import logging
import sickbeard
from sickbeard import logger
from sickbeard import common
from lib import peewee
peewee.logger = logging.getLogger('sickbeard')

#maindb = peewee.SqliteDatabase(None, threadlocals=True)
#cachedb = peewee.SqliteDatabase(None, threadlocals=True)
maindb = peewee.MySQLDatabase(None, threadlocals=True)
cachedb = maindb

def createAllTables():
    with maindb.transaction():
        for t in [
            BaseDbVersion,
            Info,
            TvShow,
            TvEpisode,
            History
        ]:
            if not t.table_exists():
                t.create_table(fail_silently=False)

    with cachedb.transaction():
        for t in [
            CacheDbVersion,
            Lastupdate,
            SceneException,
            SceneName,
            ProviderCache]:
            if not t.table_exists():
                t.create_table(fail_silently=False)

def dropAllTables():
    with maindb.transaction():
        for t in [
            BaseDbVersion,
            Info,
            TvEpisode,
            History,
            TvShow,
        ]:
            if t.table_exists():
                t.drop_table(fail_silently=True)

    with cachedb.transaction():
        for t in [
            CacheDbVersion,
            Lastupdate,
            SceneException,
            SceneName,
            ProviderCache]:
            if t.table_exists():
                t.drop_table(fail_silently=True)


class BaseSickbeardModel(peewee.Model):
    def to_dict(self):
        d = {}
        for f in self._meta.get_fields():
            d[f.db_column] = self._data[f.name]
        return d

    class Meta:
        database = maindb


class CacheBaseModel(BaseSickbeardModel):
    class Meta:
        database = cachedb


class BaseDbVersion(BaseSickbeardModel):
    db_version = peewee.IntegerField(null=True)

    class Meta:
        db_table = 'base_db_version'


class Info(BaseSickbeardModel):
    last_backlog = peewee.IntegerField(null=True)
    last_tvdb = peewee.IntegerField(null=True)

    class Meta:
        db_table = 'info'


class TvShow(BaseSickbeardModel):
    air_by_date = peewee.BooleanField(default=False)
    airs = peewee.CharField(null=True)
    flatten_folders = peewee.BooleanField(default=False)
    genre = peewee.CharField(null=True)
    lang = peewee.CharField(null=True)
    location = peewee.TextField(null=True)
    network = peewee.TextField(null=True)
    paused = peewee.BooleanField(default=False)
    quality = peewee.IntegerField(default=common.ANY)
    runtime = peewee.IntegerField(default=0)
    show_id = peewee.IntegerField()
    show_name = peewee.TextField(null=True)
    startyear = peewee.DateField(null=True)
    status = peewee.CharField(null=True)
    tvdb_id = peewee.IntegerField(primary_key=True)
    tvr_id = peewee.IntegerField(null=True)
    tvr_name = peewee.TextField(null=True)

    def save(self, force_insert=False):
        #tvdb_id is the defacto unique id for shows and is used in all table
        #joins everywhere.  There is a show_id in the table as the primary key
        #though, this is a hack for now.
        if self.tvdb_id is None:
            raise ValueError('tvdb_id must be manually set')

        self.show_id = self.tvdb_id
        return super(TvShow, self).save(force_insert=force_insert)

    class Meta:
        db_table = 'tv_shows'


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
    show = peewee.ForeignKeyField(TvShow,
                                  related_name='episodes',
                                  db_column='showid'
                                 )
    status = peewee.IntegerField(default=common.WANTED, null=True)
    tvdbid = peewee.IntegerField(null=True)

    class Meta:
        db_table = 'tv_episodes'


class History(BaseSickbeardModel):
    action = peewee.IntegerField(null=True)
    date = peewee.DateTimeField(null=True)
    episode = peewee.IntegerField(null=True)
    provider = peewee.TextField(null=True)
    quality = peewee.IntegerField(null=True)
    resource = peewee.TextField(null=True)
    season = peewee.IntegerField(null=True)
    show = peewee.ForeignKeyField(TvShow,
                                  related_name='hostory',
                                  db_column='showid'
                                 )

    class Meta:
        db_table = 'history'


class CacheDbVersion(CacheBaseModel):
    db_version = peewee.IntegerField(null=True)

    class Meta:
        db_table = 'cache_db_version'


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


class ProviderCache(CacheBaseModel):
    episodes = peewee.TextField()
    provider = peewee.CharField()
    name = peewee.TextField()
    quality = peewee.IntegerField()
    season = peewee.IntegerField()
    time = peewee.IntegerField()
    tvdbid = peewee.IntegerField()
    tvrid = peewee.IntegerField(null=True)
    url = peewee.TextField()

    class Meta:
        db_table = 'provider_cache'
