#!/usr/bin/python
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

"""
Role
====

Defines the basic interface for a plugin manager that also keeps track
of versions of plugins

API
===
"""


from distutils.version import StrictVersion

from yapsy.PluginInfo import PluginInfo
from yapsy.IPlugin import IPlugin
from yapsy.PluginManagerDecorator import PluginManagerDecorator


class VersionedPluginInfo(PluginInfo):
	"""
	Gather some info about a plugin such as its name, author,
	description...
	"""
	
	def __init__(self, plugin_name, plugin_path):
		"""
		Set the name and path of the plugin as well as the default
		values for other usefull variables.
		"""
		PluginInfo.__init__(self, plugin_name, plugin_path)
		# version number is now required to be a StrictVersion object
		self.version	= StrictVersion("0.0")

	def setVersion(self, vstring):
		self.version = StrictVersion(vstring)


class VersionedPluginManager(PluginManagerDecorator):
	"""
	Handle plugin versioning by making sure that when several
	versions are present for a same plugin, only the latest version is
	manipulated via the standard methods (eg for activation and
	deactivation)
	
	More precisely, for operations that must be applied on a single
	named plugin at a time (``getPluginByName``,
	``activatePluginByName``, ``deactivatePluginByName`` etc) the
	targetted plugin will always be the one with the latest version.
	
	.. note:: The older versions of a given plugin are still reachable
	          via the ``getPluginsOfCategoryFromAttic`` method.
	"""
	
	def __init__(self, 
				 decorated_manager=None,
				 categories_filter={"Default":IPlugin}, 
				 directories_list=None, 
				 plugin_info_ext="yapsy-plugin"):
		"""
		Create the plugin manager and record the ConfigParser instance
		that will be used afterwards.
		
		The ``config_change_trigger`` argument can be used to set a
		specific method to call when the configuration is
		altered. This will let the client application manage the way
		they want the configuration to be updated (e.g. write on file
		at each change or at precise time intervalls or whatever....)
		"""
		# Create the base decorator class
		PluginManagerDecorator.__init__(self,decorated_manager,
										categories_filter,
										directories_list,
										plugin_info_ext)
		self.setPluginInfoClass(VersionedPluginInfo)
		# prepare the storage for the early version of the plugins,
		# for which only the latest version is the one that will be
		# kept in the "core" plugin storage.
		self._prepareAttic()

	def _prepareAttic(self):
		"""
		Create and correctly initialize the storage where the wrong
		version of the plugins will be stored.
		"""
		self._attic = {}
		for categ in self.getCategories():
			self._attic[categ] = []
		

	def getLatestPluginsOfCategory(self,category_name):
		"""
		Return the list of all plugins belonging to a category.

		.. warning:: Deprecated ! Please consider using
		             getPluginsOfCategory instead.
		"""
		return self.getPluginsOfCategory(category_name)

	def loadPlugins(self, callback=None):
		"""
		Load the candidate plugins that have been identified through a
		previous call to locatePlugins.

		In addition to the baseclass functionality, this subclass also
		needs to find the latest version of each plugin.
		"""
		self._component.loadPlugins(callback)
		for categ in self.getCategories():
			latest_plugins = {}
			allPlugins = self.getPluginsOfCategory(categ)
			# identify the latest version of each plugin
			for plugin in allPlugins:
				name = plugin.name
				version = plugin.version
				if name in latest_plugins:
					if version > latest_plugins[name].version:
						older_plugin = latest_plugins[name]
						latest_plugins[name] = plugin
						self.removePluginFromCategory(older_plugin,categ)
						self._attic[categ].append(older_plugin)
					else:
						self.removePluginFromCategory(plugin,categ)
						self._attic[categ].append(plugin)
				else:
					latest_plugins[name] = plugin

	def getPluginsOfCategoryFromAttic(self,categ):
		"""
		Access the older version of plugins for which only the latest
		version is available through standard methods.
		"""
		return self._attic[categ]
			
