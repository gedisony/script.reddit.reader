#!/usr/bin/python
# encoding: utf-8

import sys
import os
import xbmc
import xbmcaddon
import urlparse


from resources.lib.utils import log
#this used to be a plugin. not that we're a script, we don't get free sys.argv's
#this import for the youtube_dl addon causes our addon to start slower. we'll import it when we need to playYTDLVideo
#if len(sys.argv) > 1:
#    a=['mode=playYTDLVideo','mode=autoPlay']
#    if any(x in sys.argv[1] for x in a):
#        import YDStreamExtractor      #note: you can't just add this import in code, you need to re-install the addon with <import addon="script.module.youtube.dl"        version="16.521.0"/> in addon.xml
#else:
#    pass

#YDStreamExtractor.disableDASHVideo(True) #Kodi (XBMC) only plays the video for DASH streams, so you don't want these normally. Of course these are the only 1080p streams on YouTube
reload(sys)
sys.setdefaultencoding("utf-8")

addon         = xbmcaddon.Addon()
addonID       = addon.getAddonInfo('id')  #script.reddit.reader
addon_path    = addon.getAddonInfo('path')      #where the addon resides
profile_path  = addon.getAddonInfo('profile')   #where user settings are stored

#WINDOW        = xbmcgui.Window(10000)
#technique borrowed from LazyTV.
#  WINDOW is like a mailbox for passing data from caller to callee.
#    e.g.: addLink() needs to pass "image description" to viewImage()

#https://github.com/reddit/reddit/wiki/API
reddit_userAgent = "XBMC:"+addonID+":v"+addon.getAddonInfo('version')+" (by /u/gsonide)"
reddit_clientID      ="ZEbDJ5DUrguDMA"
reddit_redirect_uri  ='http://localhost:8090/'   #specified when registering for a clientID

#opener.addheaders = [('User-Agent', reddit_userAgent)]
#API requests with a bearer token should be made to https://oauth.reddit.com, NOT www.reddit.com.
urlMain = "https://www.reddit.com"

hide_nsfw            = addon.getSetting("hide_nsfw") == "true"
domain_filter        = addon.getSetting("domain_filter")
subreddit_filter     = addon.getSetting("subreddit_filter")
comments_link_filter = addon.getSetting("comments_link_filter")

sitemsPerPage        = addon.getSetting("itemsPerPage")
try: itemsPerPage    = ["10", "25", "50", "75", "100"][ int(sitemsPerPage) ]
except ValueError: itemsPerPage = 50

#--- settings related to context menu "Show Comments"
CommentTreshold          = addon.getSetting("CommentTreshold")
try: int_CommentTreshold = int(CommentTreshold)
except ValueError: int_CommentTreshold = -1000    #if CommentTreshold can't be converted to int, show all comments

try:istreamable_quality=int(addon.getSetting("streamable_quality"))  #values 0 or 1
except ValueError:istreamable_quality=0
streamable_quality  =["full", "mobile"][istreamable_quality]       #https://streamable.com/documentation

REQUEST_TIMEOUT=(5,10) #requests.get timeout in seconds (connect timeout, read timeout) tuple.

#use_ytdl_for_unknown = addon.getSetting("use_ytdl_for_unknown") == "true"
#use_ytdl_for_unknown_in_comments= addon.getSetting("use_ytdl_for_unknown_in_comments") == "true"

addonUserDataFolder = xbmc.translatePath("special://profile/addon_data/"+addonID)
subredditsFile      = xbmc.translatePath(addonUserDataFolder+"/subreddits")
subredditsPickle    = xbmc.translatePath(addonUserDataFolder+"/subreddits.pickle")
CACHE_FILE          = xbmc.translatePath(addonUserDataFolder+"/requests_cache")

#ytdl_psites_file         = xbmc.translatePath(profile_path+"/ytdl_sites_porn")
default_ytdl_psites_file = xbmc.translatePath(  addon_path+"/resources/ytdl_sites_porn" )
#ytdl_sites_file          = xbmc.translatePath(profile_path+"/ytdl_sites")
default_ytdl_sites_file  = xbmc.translatePath(  addon_path+"/resources/ytdl_sites" )

#last slash at the end is important
ytdl_core_path=xbmc.translatePath(  addon_path+"/resources/lib/youtube_dl/" )

#if xbmcvfs.exists(ytdl_core_path):
#    xbmc.log('using ytdl core', level=xbmc.LOGNOTICE)
#else:
#    #*** it seems like the script.module.youtube_dl version gets imported if the one from resources.lib is missing
#    xbmc.log('using ytdl addon ', level=xbmc.LOGNOTICE)

if not os.path.isdir(addonUserDataFolder):
    os.mkdir(addonUserDataFolder)

#def parse_and_play(url, name, type_):
    #this mode is intended to receive links from a modified kore remote
    #i don't think this is allowed per http://forum.kodi.tv/showthread.php?tid=178881
#    pass

def parameters_string_to_dict(parameters):
    #log('   ######' + str( urlparse.parse_qsl(parameters) )  )
    return dict( urlparse.parse_qsl(parameters) )


if __name__ == '__main__':

    if len(sys.argv) > 1:
        params=parameters_string_to_dict(sys.argv[1])
        #log("sys.argv[1]="+sys.argv[1]+"  ")
    else: params={}

    mode   = params.get('mode', '')
    url    = params.get('url', '')
    type_  = params.get('type', '') #type is a python function, try not to use a variable name same as function
    name   = params.get('name', '')
    #xbmc supplies this additional parameter if our <provides> in addon.xml has more than one entry e.g.: <provides>video image</provides>
    #xbmc only does when the add-on is started. we have to pass it along on subsequent calls
    # if our plugin is called as a pictures add-on, value is 'image'. 'video' for video
    #content_type=urllib.unquote_plus(params.get('content_type', ''))
    #ctp = "&content_type="+content_type   #for the lazy
    #log("content_type:"+content_type)

    log( "----------------v" + addon.getAddonInfo('version')  + ' ' + ( mode+': '+url if mode else '' ) +'-----------------')
    #log("params="+sys.argv[1]+"  ")
#    log( repr(sys.argv))
#    log("----------------------")
#    log("params="+ str(params))
#    log("mode="+ mode)
#    log("url="+  url)
#    log("name="+ name)
#    log("type="+ type_)
#    log("-----------------------")

    from resources.lib.slideshow import autoSlideshow
    from resources.lib.autoplay import autoPlay
    from resources.lib.converthtml import readHTML
    from resources.lib.utils import addtoFilter,open_web_browser
    from resources.lib.actions import manage_subreddits, addSubreddit, editSubreddit, removeSubreddit,\
    loopedPlayback,error_message,viewImage, listAlbum, viewTallImage,update_youtube_dl_core,\
    playVideo, playYTDLVideo, playURLRVideo,searchReddits, delete_setting_file, listRelatedVideo
    from resources.lib.reddit import reddit_get_refresh_token, reddit_get_access_token, reddit_revoke_refresh_token, reddit_save
    from resources.lib.main_listing import index, listSubReddit, listLinksInComment

    if mode=='':mode='index'  #default mode is to list start page (index)
    #plugin_modes holds the mode string and the function that will be called given the mode
    plugin_modes = {'index'                 : index
                    ,'listSubReddit'        : listSubReddit
                    ,'playVideo'            : playVideo
                    ,'addSubreddit'         : addSubreddit
                    ,'editSubreddit'        : editSubreddit
                    ,'removeSubreddit'      : removeSubreddit
                    ,'addtoFilter'          : addtoFilter
                    ,'search'               : searchReddits
                    ,'autoPlay'             : autoPlay
                    ,'autoSlideshow'        : autoSlideshow
                    ,'listAlbum'            : listAlbum        #slideshowAlbum
                    ,'viewImage'            : viewImage
                    ,'viewTallImage'        : viewTallImage
                    ,'readHTML'             : readHTML
                    ,'listLinksInComment'   : listLinksInComment
                    ,'playYTDLVideo'        : playYTDLVideo
                    ,'playURLRVideo'        : playURLRVideo
                    ,'loopedPlayback'       : loopedPlayback
                    ,'error_message'        : error_message
                    ,'manage_subreddits'    : manage_subreddits
                    ,'update_youtube_dl_core':update_youtube_dl_core
                    ,'get_refresh_token'    : reddit_get_refresh_token
                    ,'get_access_token'     : reddit_get_access_token
                    ,'revoke_refresh_token' : reddit_revoke_refresh_token
                    ,'reddit_save'          : reddit_save
                    ,'delete_setting_file'  : delete_setting_file
                    ,'listRelatedVideo'     : listRelatedVideo
                    ,'openBrowser'          : open_web_browser
                    }
    plugin_modes[mode](url,name,type_)
