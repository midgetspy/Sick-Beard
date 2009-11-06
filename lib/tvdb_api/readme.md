# `tvdb_api` and `tvnamer`

`tvdb_api` is an easy to use interface to [thetvdb.com][tvdb]

`tvnamer` is a utility which uses `tvdb_api` to rename files from `some.show.s01e03.blah.abc.avi` to `Some Show - [01x03] - The Episode Name.avi` (getting the episode name from `tvdb_api`)

## To install

You can easily install `tvnamer` via `easy_install`

    easy_install tvnamer

This installs the `tvnamer` command-line tool (and the `tvdb_api` module as a requirement)

You may need to use sudo, depending on your setup:

    sudo easy_install tvnamer

If you wish to only install the `tvdb_api` Python module,

    easy_install tvdb_api

# `tvnamer`

## Basic usage

From the command line, simply run:

    tvnamer the.file.s01e01.avi

For example:

    $ tvnamer scrubs.s01e01.avi
    ####################
    # Starting tvnamer
    # Processing 1 files
    # ..got tvdb mirrors
    # Starting to process files
    ####################
    # Processing scrubs (season: 1, episode 1)
    TVDB Search Results:
    1 -> Scrubs # http://thetvdb.com/?tab=series&id=76156
    Automatically selecting only result
    ####################
    Old name: scrubs.s01e01.avi
    New name: Scrubs - [01x01] - My First Day.avi
    Rename?
    ([y]/n/a/q)

Enter `y` then press `return` and the file will be renamed to "Scrubs - [01x01] - My First Day.avi". You can also simply press `return` to select the default option, denoted by the surrounding `[]`

If there are multiple shows with the same (or similar) names, you will be asked to select the correct one - "Lost" is a good example of this:

    $ python tvnamer.py lost.s01e01.avi 
    ####################
    # Starting tvnamer
    # Processing 1 files
    # ..got tvdb mirrors
    # Starting to process files
    ####################
    # Processing lost (season: 1, episode 1)
    TVDB Search Results:
    1 -> Lost # http://thetvdb.com/?tab=series&id=73739
    2 -> Lost in Space # http://thetvdb.com/?tab=series&id=72923
    [...]
    Enter choice (first number, ? for help):

To select the first result, enter `1` then `return`, to select the second enter `2` and so on. The link after `#` goes to the relevant [thetvdb.com][tvdb] page, which will contain information and images to help you select the correct series.

You can rename multiple files, or an entire directory by using the files or directories as arguments:

    $ tvnamer file1.avi file2.avi etc
    $ tvnamer .
    $ tvnamer /path/to/my/folder/
    $ tvnamer ./folder/1/ ./folder/2/

You can skip a specific file by entering `n` (no). If you enter `a` (always) `tvnamer` will rename the remaining files automatically. The suggested use of this is check the first few episodes are named correctly, then use `a` to rename the rest.

Note, tvnamer will only descend one level into directories unless the `-r` (or `--recursive`) flag is specified. For example, if you have the following directory structure:

    dir1/
        file1.avi
        dir2/
            file2.avi
            file3.avi

..then running `tvnamer dir1/` will only rename `file1.avi`, ignoring `dir2/` and its contents.

If you wish to rename all files (file1, file2 and file3), you would run:

    tvnamer --recursive dir1/

## Advanced usage

There are various flags you can use with `tvnamer`, run..

    tvnamer --help

..to see them, and a short description of each.

The most interesting are most likely `--batch`, `--selectfirst` and `--always`:

`--selectfirst` will select the first series the search found, but will not automatically rename any episodes.

`--always` will ask you select the correct series, then automatically rename all files.

`--batch` will not prompt you for anything. It automatically selects the first series search result, and automatically rename all files. Use carefully!

# `tvdb_api`

## Basic usage

    import tvdb_api
    t = tvdb_api.Tvdb()
    episode = t['My Name Is Earl'][1][3] # get season 1, episode 3 of show
    print episode['episodename'] # Print episode name

## Advanced usage

Most of the documentation is in docstrings. The examples are tested (using doctest) so will always be up to date and working.

The docstring for `Tvdb.__init__` lists all initialisation arguments, including support for non-English searches, custom "Select Series" interfaces and enabling the retrieval of banners and extended actor information. You can also override the default API key using `apikey`, recommended if you're using `tvdb_api` in a larger script or application

### Exceptions

There are several exceptions you may catch, these can be imported from `tvdb_api`:

- `tvdb_error` - this is raised when there is an error communicating with [www.thetvdb.com][tvdb] (a network error most commonly)
- `tvdb_userabort` - raised when a user aborts the Select Series dialog (by `ctrl+c`, or entering `q`)
- `tvdb_shownotfound` - raised when `t['show name']` cannot find anything
- `tvdb_seasonnotfound` - raised when the requested series (`t['show name][99]`) does not exist
- `tvdb_episodenotfound` - raised when the requested episode (`t['show name][1][99]`) does not exist.
- `tvdb_attributenotfound` - raised when the requested attribute is not found (`t['show name']['an attribute']`, `t['show name'][1]['an attribute']`, or ``t['show name'][1][1]['an attribute']``)

### Series data

All data exposed by [thetvdb.com][tvdb] is accessible via the `Show` class. A Show is retrieved by doing..

    >>> import tvdb_api
    >>> t = tvdb_api.Tvdb()
    >>> show = t['scrubs']
    >>> type(show)
    <class 'tvdb_api.Show'>

For example, to find out what network Scrubs is aired:

    >>> t['scrubs']['network']
    u'NBC|ABC'

The data is stored in an attribute named `data`, within the Show instance:

    >>> t['scrubs'].data.keys()
    ['networkid', 'rating', 'airs_dayofweek', 'contentrating', 'seriesname', 'id', 'airs_time', 'network', 'fanart', 'lastupdated', 'actors', 'overview', 'status', 'added', 'poster', 'imdb_id', 'genre', 'banner', 'seriesid', 'language', 'zap2it_id', 'addedby', 'firstaired', 'runtime']

Although each element is also accessible via `t['scrubs']` for ease-of-use:

    >>> t['scrubs']['rating']
    u'9.1'

This is the recommended way of retrieving "one-off" data (for example, if you are only interested in "seriesname"). If you wish to iterate over all data, or check if a particular show has a specific piece of data, use the `data` attribute,

    >>> 'rating' in t['scrubs'].data
    True

### Banners and actors

Since banners and actors are separate XML files, retrieving them by default is undesirable. If you wish to retrieve banners (and other fanart), use the `banners` Tvdb initialisation argument:

    >>> t = Tvdb(banners = True)

Then access the data using a `Show`'s `_banner` key:

    >>> t['scrubs']['_banners'].keys()
    ['fanart', 'poster', 'series', 'season']

The banner data structure will be improved in future versions.

Extended actor data is accessible similarly:

    >>> t = Tvdb(actors = True)
    >>> actors = t['scrubs']['_actors']
    >>> actors[0]
    >>> actors[0]
    <Actor "Zach Braff">
    >>> actors[0].keys()
    ['image', 'sortorder', 'role', 'id', 'name']
    >>> actors[0]['role']
    u'Dr. John Michael "J.D." Dorian'

Remember a simple list of actors is accessible via the default Show data:

    >>> t['scrubs']['actors']
    u'|Zach Braff|Donald Faison|Sarah Chalke|Christa Miller Lawrence|Aloma Wright|Robert Maschio|Sam Lloyd|Neil Flynn|Ken Jenkins|Judy Reyes|John C. McGinley|'

[tvdb]: http://www.thetvdb.com