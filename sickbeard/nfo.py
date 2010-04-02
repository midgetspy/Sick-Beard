import xml.etree.cElementTree as etree

from sickbeard import XML_NSMAP, TVDB_BASE_URL
TVDB_BASE_URL = "aoeu"

def makeShowNFO(show):
    
    tvNode = etree.Element( "tvshow" )
    for ns in XML_NSMAP.keys():
        tvNode.set(ns, XML_NSMAP[ns])

    title = etree.SubElement( tvNode, "title" )
    if show.data.name != None:
        title.text = show.data.name
        
    rating = etree.SubElement( tvNode, "rating" )
    if show.data.rating != None:
        rating.text = str(show.data.rating)

    plot = etree.SubElement( tvNode, "plot" )
    if show.data.plot != None:
        plot.text = show.data.plot

    episodeguideurl = etree.SubElement( tvNode, "episodeguideurl" )
    episodeguide = etree.SubElement( tvNode, "episodeguide" )
    if show.tvdb_id != None:
        showurl = TVDB_BASE_URL + '/series/' + str(show.tvdb_id) + '/all/en.zip'
        episodeguideurl.text = showurl
        episodeguide.text = showurl
        
    mpaa = etree.SubElement( tvNode, "mpaa" )
    if show.data.contentrating != None:
        mpaa.text = show.data.contentrating

    tvdbid = etree.SubElement( tvNode, "id" )
    if show.tvdb_id != None:
        tvdbid.text = str(show.tvdb_id)
        
    genre = etree.SubElement( tvNode, "genre" )
    if show.data.genres != None:
        genre.text = " / ".join(show.data.genres)
        
    premiered = etree.SubElement( tvNode, "premiered" )
    if show.data.firstaired != None:
        premiered.text = str(show.data.firstaired)
        
    studio = etree.SubElement( tvNode, "studio" )
    if show.data.network != None:
        studio.text = show.data.network

    for actor in show.data.actors:

        cur_actor = etree.SubElement( tvNode, "actor" )

        cur_actor_name = etree.SubElement( cur_actor, "name" )
        cur_actor_name.text = actor['name']
        cur_actor_role = etree.SubElement( cur_actor, "role" )
        cur_actor_role_text = actor['role']

        if cur_actor_role_text != None:
            cur_actor_role.text = cur_actor_role_text

        cur_actor_thumb = etree.SubElement( cur_actor, "thumb" )
        cur_actor_thumb_text = actor['image']

        if cur_actor_thumb_text != None:
            cur_actor_thumb.text = cur_actor_thumb_text

    # Make it purdy
    #helpers.indentXML( tvNode )

    return tvNode

def makeEpNFO(ep):

    episode = etree.Element( "episodedetails" )

    title = etree.SubElement( episode, "title" )
    title.text = ep.name if ep.name else None

    season = etree.SubElement( episode, "season" )
    season.text = str(ep.season)

    episodenum = etree.SubElement( episode, "episode" )
    episodenum.text = str(ep.episode)
    
    aired = etree.SubElement( episode, "aired" )
    aired.text = str(ep.aired)

    plot = etree.SubElement( episode, "plot" )
    plot.text = ep.description if ep.description else None

    displayseason = etree.SubElement( episode, "displayseason" )
    displayseason.text = str(ep.displayseason) if ep.displayseason else None

    displayepisode = etree.SubElement( episode, "displayepisode" )
    displayepisode.text = str(ep.displayepisode) if ep.displayepisode else None

    thumb = etree.SubElement( episode, "thumb" )
    thumb.text = ep.thumb if ep.thumb else None

    watched = etree.SubElement( episode, "watched" )
    watched.text = 'false'

    credits = etree.SubElement( episode, "credits" )
    credits.text = ep.writer if ep.writer else None

    director = etree.SubElement( episode, "director" )
    director.text = ep.director if ep.director else None

    for actor in ep.gueststars:
        cur_actor = etree.SubElement( episode, "actor" )
        cur_actor_name = etree.SubElement( cur_actor, "name" )
        cur_actor_name.text = actor

    for actor in ep.show.actors:

        cur_actor = etree.SubElement( episode, "actor" )

        cur_actor_name = etree.SubElement( cur_actor, "name" )
        cur_actor_name.text = actor['name']
        cur_actor_role = etree.SubElement( cur_actor, "role" )
        cur_actor_role_text = actor['role']

        if cur_actor_role_text != None:
            cur_actor_role.text = cur_actor_role_text

        cur_actor_thumb = etree.SubElement( cur_actor, "thumb" )
        cur_actor_thumb_text = actor['image']

        if cur_actor_thumb_text != None:
            cur_actor_thumb.text = cur_actor_thumb_text

    # Make it purdy
    #helpers.indentXML( episode )

    return episode
