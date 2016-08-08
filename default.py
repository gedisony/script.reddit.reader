#!/usr/bin/python
# encoding: utf-8
import urllib
import urllib2
import socket
import sys
import re
import os
import json
import sqlite3
import random
import datetime
import time
import xbmc
import xbmcplugin
import xbmcgui
import xbmcaddon
import urlparse

import SimpleDownloader
import requests

import shelve
import shutil

#from email import Message

#this used to be a plugin. not that we're a script, we don't get free sys.argv's
if len(sys.argv) > 1:
    #this import for the youtube_dl addon causes our addon to start slower. we'll import it when we need to playYTDLVideo  
    if 'mode=playYTDLVideo' in sys.argv[1] :
        import YDStreamExtractor      #note: you can't just add this import in code, you need to re-install the addon with <import addon="script.module.youtube.dl"        version="16.521.0"/> in addon.xml
else:
    pass 

pluginhandle  = 10  #int(sys.argv[1])
    

#YDStreamExtractor.disableDASHVideo(True) #Kodi (XBMC) only plays the video for DASH streams, so you don't want these normally. Of course these are the only 1080p streams on YouTube
from urllib import urlencode
reload(sys)
sys.setdefaultencoding("utf-8")


addon         = xbmcaddon.Addon()
addonID       = addon.getAddonInfo('id')  #script.reddit.reader
addon_path    = addon.getAddonInfo('path')     #where the addon resides
profile_path  = addon.getAddonInfo('profile')   #where user settings are stored

WINDOW        = xbmcgui.Window(10000)
#technique borrowed from LazyTV. 
#  WINDOW is like a mailbox for passing data from caller to callee. 
#    e.g.: addLink() needs to pass "image description" to playSlideshow()

osWin         = xbmc.getCondVisibility('system.platform.windows')
osOsx         = xbmc.getCondVisibility('system.platform.osx')
osLinux       = xbmc.getCondVisibility('system.platform.linux')

if osWin:
    fd="\\"
else:
    fd="/"

socket.setdefaulttimeout(30)
opener = urllib2.build_opener()
#opener = urllib2.build_opener(urllib2.HTTPHandler(debuglevel=1))

#https://github.com/reddit/reddit/wiki/API
userAgent = "XBMC:"+addonID+":v"+addon.getAddonInfo('version')+" (by /u/gsonide)"
reddit_clientID      ="ZEbDJ5DUrguDMA"    
reddit_redirect_uri  ='http://localhost:8090/'   #specified when registering for a clientID
reddit_refresh_token =addon.getSetting("reddit_refresh_token")
reddit_access_token  =addon.getSetting("reddit_access_token") #1hour token

#test1 line

opener.addheaders = [('User-Agent', userAgent)]
#API requests with a bearer token should be made to https://oauth.reddit.com, NOT www.reddit.com.
urlMain = "https://www.reddit.com"


#filter           = addon.getSetting("filter") == "true"
#filterRating     = int(addon.getSetting("filterRating"))
#filterThreshold  = int(addon.getSetting("filterThreshold"))

# settings for automatically play videos
# showAll              = addon.getSetting("showAll") == "true"
# showUnwatched        = addon.getSetting("showUnwatched") == "true"
# showUnfinished       = addon.getSetting("showUnfinished") == "true"
# showAllNewest        = addon.getSetting("showAllNewest") == "true"
# showUnwatchedNewest  = addon.getSetting("showUnwatchedNewest") == "true"
# showUnfinishedNewest = addon.getSetting("showUnfinishedNewest") == "true"

default_frontpage    = addon.getSetting("default_frontpage") 
no_index_page        = addon.getSetting("no_index_page") == "true"

forceViewMode        = addon.getSetting("forceViewMode") == "true"
viewMode             = str(addon.getSetting("viewMode"))
comments_viewMode    = str(addon.getSetting("comments_viewMode"))
album_viewMode       = str(addon.getSetting("album_viewMode"))

show_nsfw            = addon.getSetting("show_nsfw") == "true"


r_AccessToken         = addon.getSetting("r_AccessToken") 

sitemsPerPage        = addon.getSetting("itemsPerPage")
try: itemsPerPage = int(sitemsPerPage)
except: itemsPerPage = 50    

itemsPerPage          = ["10", "25", "50", "75", "100"][itemsPerPage]
TitleAddtlInfo        = addon.getSetting("TitleAddtlInfo") == "true"   #Show additional post info on title</string>
HideImagePostsOnVideo = addon.getSetting("HideImagePostsOnVideo") == 'true' #<string id="30204">Hide image posts on video addon</string>
setting_hide_images = False

# searchSort = int(addon.getSetting("searchSort"))
# searchSort = ["ask", "relevance", "new", "hot", "top", "comments"][searchSort]
# searchTime = int(addon.getSetting("searchTime"))
# searchTime = ["ask", "hour", "day", "week", "month", "year", "all"][searchTime]

#--- settings related to context menu "Show Comments"
CommentTreshold          = addon.getSetting("CommentTreshold") 
try: int_CommentTreshold = int(CommentTreshold)
except: int_CommentTreshold = -1000    #if CommentTreshold can't be converted to int, show all comments 

#showBrowser     = addon.getSetting("showBrowser") == "true"
#browser_win     = int(addon.getSetting("browser_win"))
#browser_wb_zoom = str(addon.getSetting("browser_wb_zoom"))

ll_qualiy  = int(addon.getSetting("ll_qualiy"))
ll_qualiy  = ["480p", "720p"][ll_qualiy]
ll_downDir = str(addon.getSetting("ll_downDir"))

istreamable_quality =int(addon.getSetting("streamable_quality"))  #values 0 or 1
streamable_quality  =["full", "mobile"][istreamable_quality]       #https://streamable.com/documentation

gfy_downDir = str(addon.getSetting("gfy_downDir"))



addonUserDataFolder = xbmc.translatePath("special://profile/addon_data/"+addonID)
subredditsFile      = xbmc.translatePath("special://profile/addon_data/"+addonID+"/subreddits")
nsfwFile            = xbmc.translatePath("special://profile/addon_data/"+addonID+"/nsfw")

ytdl_psites_file         = xbmc.translatePath(profile_path+"/ytdl_sites_porn")
default_ytdl_psites_file = xbmc.translatePath(  addon_path+"/ytdl_sites_porn" )
ytdl_sites_file          = xbmc.translatePath(profile_path+"/ytdl_sites")
default_ytdl_sites_file  = xbmc.translatePath(  addon_path+"/ytdl_sites" )



#C:\Users\myusername\AppData\Roaming\Kodi\userdata\addon_data\plugin.video.reddit_viewer
#SlideshowCacheFolder    = xbmc.translatePath("special://profile/addon_data/"+addonID+"/slideshowcache") #will use this to cache images for slideshow in video mode

if not os.path.isdir(addonUserDataFolder):
    os.mkdir(addonUserDataFolder)

#if not os.path.isdir(SlideshowCacheFolder):
#    os.mkdir(SlideshowCacheFolder)


if show_nsfw:
    nsfw = ""
else:
    nsfw = "nsfw:no+"


def getDbPath():
    path = xbmc.translatePath("special://userdata/Database")
    files = os.listdir(path)
    latest = ""
    for file in files:
        if file[:8] == 'MyVideos' and file[-3:] == '.db':
            if file > latest:
                latest = file
    if latest:
        return os.path.join(path, latest)
    else:
        return ""
    
def getPlayCount(url):
    if dbPath:
        c.execute('SELECT playCount FROM files WHERE strFilename=?', [url])
        result = c.fetchone()
        if result:
            result = result[0]
            if result:
                return int(result)
            return 0
    return -1

def format_multihub(multihub):
#properly format a multihub string
#make sure input is a valid multihub 
    t = multihub
    #t='User/sallyyy19/M/video'
    ls = t.split('/')

    for idx, word in enumerate(ls):
        if word.lower()=='user':ls[idx]='user'
        if word.lower()=='m'   :ls[idx]='m'
    #xbmc.log ("/".join(ls))            
    return "/".join(ls)
    
    
#MODE addSubreddit      - name, type not used

def manage_subreddits(subreddit, name, type):
    log('manage_subreddits(%s, %s, %s)' %(subreddit, name, type) )
    #this funciton is called by the listSubRedditGUI when user presses left button when on the subreddits list 
    
    #http://forum.kodi.tv/showthread.php?tid=148568
    dialog = xbmcgui.Dialog()
    #funcs = (        addSubreddit,        editSubreddit,        removeSubreddit,    )
    #elected_index = dialog.select(subreddit, ['add new subreddi', 'edit   subreddit', 'remove subreddit'])
    selected_index = dialog.select(subreddit, [translation(32001), translation(32003), translation(32002)])

    #the if statements below is not as elegant as autoselecting the func from funcs but more flexible in the case with add subreddit where we should not send a subreddit parameter
    #    func = funcs[selected_index]
    #     #assign item from funcs to func
    #    func(subreddit, name, type)    
    log('selected_index ' + str(selected_index))
    if selected_index == 0:       # 0->first item
        addSubreddit('','','')
        pass
    elif selected_index == 1:     # 1->second item
        editSubreddit(subreddit,'','')
        pass
    elif selected_index == 2:     # 2-> third item
        removeSubreddit(subreddit,'','')
        pass
    else:                         #-1 -> escape pressed or [cancel] 
        pass
    
    xbmc.executebuiltin( "Dialog.Close(busydialog)" )
    #this is a hack to force the subreddit listing to refresh.
    #   the calling gui needs to close after calling this function 
    #   after we are done editing the subreddits file, we call index() (the start of program) again. 
    index("","","")

    
def addSubreddit(subreddit, name, type):
    log( 'addSubreddit ' + subreddit)
    alreadyIn = False
    fh = open(subredditsFile, 'r')
    content = fh.readlines()
    fh.close()
    
    if subreddit:
        for line in content:
            #log('line=['+line+']toadd=['+subreddit+']')
            if line.strip()==subreddit.strip():
                #log('  MATCH '+line+'='+subreddit)
                alreadyIn = True
        if not alreadyIn:
            fh = open(subredditsFile, 'a')
            fh.write(subreddit+'\n')
            fh.close()
    else:
        #dialog = xbmcgui.Dialog()
        #ok = dialog.ok('Add subreddit', 'Add a subreddit (videos)','or  Multiple subreddits (music+listentothis)','or  Multireddit (/user/.../m/video)')
        #would be great to have some sort of help to show first time user here
        
        keyboard = xbmc.Keyboard('', translation(30001))
        keyboard.doModal()
        if keyboard.isConfirmed() and keyboard.getText():
            subreddit = keyboard.getText()

            #cleanup user input. make sure /user/ and /m/ is lowercase
            if this_is_a_multihub(subreddit):
                subreddit = format_multihub(subreddit)
            
            for line in content:
                if line.lower()==subreddit.lower()+"\n":
                    alreadyIn = True
            if not alreadyIn:
                fh = open(subredditsFile, 'a')
                fh.write(subreddit+'\n')
                fh.close()
        xbmc.executebuiltin("Container.Refresh")

#MODE removeSubreddit      - name, type not used
def removeSubreddit(subreddit, name, type):
    log( 'removeSubreddit ' + subreddit)
     
    fh = open(subredditsFile, 'r')
    content = fh.readlines()
    fh.close()
    contentNew = ""
    for line in content:
        if line!=subreddit+'\n':
            #log('line='+line+'toremove='+subreddit)
            contentNew+=line
    fh = open(subredditsFile, 'w')
    fh.write(contentNew)
    fh.close()
    xbmc.executebuiltin("Container.Refresh")

def editSubreddit(subreddit, name, type):
    log( 'editSubreddit ' + subreddit)
     
    fh = open(subredditsFile, 'r')
    content = fh.readlines()
    fh.close()
    contentNew = ""

    keyboard = xbmc.Keyboard(subreddit, translation(30003))
    keyboard.doModal()
    if keyboard.isConfirmed() and keyboard.getText():
        newsubreddit = keyboard.getText()
        #cleanup user input. make sure /user/ and /m/ is lowercase
        if this_is_a_multihub(newsubreddit):
            newsubreddit = format_multihub(newsubreddit)
        
        for line in content:
            if line.strip()==subreddit.strip() :      #if matches the old subreddit,
                #log("adding: %s  %s  %s" %(line, subreddit, newsubreddit)  )
                contentNew+=newsubreddit+'\n'
            else:
                contentNew+=line

        fh = open(subredditsFile, 'w')
        fh.write(contentNew)
        fh.close()
            
        xbmc.executebuiltin("Container.Refresh")    

def this_is_a_multihub(subreddit):
    #subreddits and multihub are stored in the same file
    #i think we can get away with just testing for user/ to determine multihub
    if subreddit.lower().startswith('user/') or subreddit.lower().startswith('/user/'): #user can enter multihub with or without the / in the beginning
        return True
    else:
        return False

def assemble_reddit_filter_string(search_string, subreddit, skip_site_filters="", domain="" ):
    #skip_site_filters -not adding a search query makes your results more like the reddit website 
    #search_string will not be used anymore, replaced by domain. leaving it here for now.
    #    using search string to filter by domain returns the same result everyday 
    
    url = urlMain      # global variable urlMain = "http://www.reddit.com"

    a=[':','/domain/']
    if any(x in subreddit for x in a):  #search for ':' or '/domain/'
        #log("domain "+ subreddit)
        domain=re.findall(r'(?::|\/domain\/)(.+)',subreddit)[0]
        #log("domain "+ str(domain))
        

    if domain:
        # put '/?' at the end. looks ugly but works fine.
        #https://www.reddit.com/domain/vimeo.com/?&limit=5
        url+= "/domain/%s/.json?" %(domain)   #/domain doesn't work with /search?q=
    else:
        if this_is_a_multihub(subreddit):
            #e.g: https://www.reddit.com/user/sallyyy19/m/video/search?q=multihub&restrict_sr=on&sort=relevance&t=all
            #https://www.reddit.com/user/sallyyy19/m/video
            #url+='/user/sallyyy19/m/video'     
            #format_multihub(subreddit)
            if subreddit.startswith('/'):
                #log("startswith/") 
                url+=subreddit  #user can enter multihub with or without the / in the beginning
            else: url+='/'+subreddit
        else:
            if subreddit: 
                url+= "/r/"+subreddit
            #else: 
                #default to front page instead of r/all
                #url+= "/r/all"
            #   pass
 
        site_filter=""
        if search_string:  #search string overrides our supported sites filter
            search_string = urllib.unquote_plus(search_string)
            url+= "/search.json?q=" + urllib.quote_plus(search_string)
        elif skip_site_filters: 
            url+= "/.json?"
        else:
            #no more supported_sites filter OR... OR... OR...
            url+= "/.json?"
            pass            

    url+= "&"+nsfw       #nsfw = "nsfw:no+"
    
    url += "&limit="+str(itemsPerPage)
    #url += "&limit=12"
    #log("assemble_reddit_filter_string="+url)
    return url

def site_filter_for_reddit_search():
    #go through the supported sites list and assemble the reddit search filter for them
    #except youtube_dl sites (too many)
    
    #this is only used for "search reddit" list item 
    site_filter=""
    
    for site in supported_sites :
        if site[0] and site[5]:  #site[0]  is the show_youtube/show_vimeo/show_dailymotion/... global variables taken from settings file
            site_filter += site[5] + " OR "
    #remove the last ' OR '
    if site_filter.endswith(" OR "):  site_filter = site_filter[:-4]

    #url+= "/search.json?q=" + urllib.quote_plus(site_filter)
    
    return urllib.quote_plus(site_filter)   #str( sites_filter )

def parse_subreddit_entry(subreddit_entry_from_file):
    #returns subreddit, [alias] and description. also populates WINDOW mailbox for custom view id of subreddit
    #  description= a friendly description of the 'subreddit shortcut' on the first page of addon 
    #    used for skins that display them

    subreddit, alias, viewid = subreddit_alias( subreddit_entry_from_file )

    description=subreddit
    #check for domain filter
    a=[':','/domain/']
    if any(x in subreddit for x in a):  #search for ':' or '/domain/'
        #log("domain "+ subreddit)
        domain=re.findall(r'(?::|\/domain\/)(.+)',subreddit)[0]
        description=translation(32008) % domain            #"Show posts from"
    
    #describe combined subreddits    
    if '+' in subreddit:
        description=subreddit.replace('+','[CR]')

    #describe multireddit or multihub
    if this_is_a_multihub(subreddit):
        description=translation(32007)  #"Custom Multireddit"

    #save that view id in our global mailbox (retrieved by listSubReddit)
    #WINDOW.setProperty('viewid-'+subreddit, viewid)

    return subreddit, alias, description

def subreddit_alias( subreddit_entry_from_file ):
    #users can specify an alias for the subredit and it is stored in the file as a regular string  e.g. diy[do it yourself]  
    #this function returns the subreddit without the alias identifier and alias if any or alias=subreddit if none
    ## in addition, users can specify custom viewID for a subreddit by encapsulating the viewid in ()'s
    
    a=re.compile(r"(\[[^\]]*\])") #this regex only catches the [] 
    #a=re.compile(r"(\[[^\]]*\])?(\(\d+\))?") #this regex catches the [] and ()'s
    alias=""
    viewid=""
    #return the subreddit without the alias. but (viewid), if present, is still there
    subreddit = a.sub("",subreddit_entry_from_file).strip()
    #log( "  re:" +  subreddit )
    
    #get the viewID
    try:viewid= subreddit[subreddit.index("(") + 1:subreddit.rindex(")")]
    except:viewid=""
    #log( "viewID=%s for r/%s" %( viewid, subreddit ) )
    
    if viewid:
        #remove the (viewID) string from subreddit 
        subreddit=subreddit.replace( "(%s)"%viewid, "" )

    #get the [alias]
    a= a.findall(subreddit_entry_from_file)
    if a:
        alias=a[0]
        #log( "      alias:" + alias )
    else:
        alias = subreddit
    
    return subreddit, alias, viewid

def create_default_subreddits():
    #create a default file and sites
    fh = open(subredditsFile, 'a')
    #fh.write('/user/gummywormsyum/m/videoswithsubstance\n')
    fh.write('/user/sallyyy19/m/video[%s]\n' %(translation(32006)))  # user   http://forum.kodi.tv/member.php?action=profile&uid=134499
    fh.write('Documentaries+ArtisanVideos+lectures+LearnUselessTalents\n')
    fh.write('Stop_Motion+FrameByFrame+Brickfilms+Animation\n')
    #fh.write('SlowMotion+timelapse+PerfectTiming\n')
    fh.write('all\n')
    fh.write('aww+funny+Nickelodeons\n')
    fh.write('music+listentothis+musicvideos\n')
    fh.write('site:youtube.com\n')
    fh.write('videos\n')
    #fh.write('videos/new\n')
    fh.write('woahdude+interestingasfuck+shittyrobots\n')
    fh.close()
    #justiceporn

            

def index(url,name,type):
    ## this is where the __main screen is created

    from resources.guis import indexGui
    li=[]

    #ui = cGUI('DialogSelect.xml' , addon_path, defaultSkin='Default', defaultRes='1080i', listing=li, id=55)
    #ui.show()
    #xbmc.sleep(2000)

#     log( "sys.argv[0]="+ sys.argv[0] ) #plugin://plugin.video.reddit_viewer/
#     log( "addonID=" + addonID )     #plugin.video.reddit_viewer
#     log( "path=" + addon.getAddonInfo('path') )
#     log( "profile=" + addon.getAddonInfo('profile') )

    #testing code
    #h="as asd [S]asdasd[/S] asdas "
    #log(markdown_to_bbcode(h))
    #addDir('test', "url", "next_mode", "", "subreddit" )
    if not os.path.exists(subredditsFile):
        create_default_subreddits()

    #log( "  show_nsfw  "+str(show_nsfw) + "  [" + nsfw+"]")

    #log( "--------------------"+ addon.getAddonInfo('path') )
    #log( "--------------------"+ addon.getAddonInfo('profile') )
     
        
    #this part errors on android. comment out until feature is implemented
#     if not os.path.exists(ytdl_psites_file): 
#         #copy over default file
#         #there is no os.copy() command. have to use shutil or just read and write to file ourself
#         #open(ytdl_psites_file, "w").write(open( default_ytdl_psites_file ).read())
#         log( "default ytdl_sites file not found. copying from addon installation.")
#         shutil.copy(default_ytdl_psites_file, ytdl_psites_file)
# 
#     if not os.path.exists(ytdl_sites_file): 
#         log( "default ytdl_sites file not found. copying from addon installation.")
#         shutil.copy(default_ytdl_sites_file, ytdl_sites_file)

    if no_index_page:   
        log( "   default_frontpage " +default_frontpage )
        if default_frontpage:
            #log( "   ssssssss " + assemble_reddit_filter_string("","")  )
            listSubReddit( assemble_reddit_filter_string("",default_frontpage) , default_frontpage, "") 
        else:
            listSubReddit( assemble_reddit_filter_string("","") , "Reddit-Frontpage", "") #https://www.reddit.com/.json?&&limit=10
    else:
        #subredditsFile loaded in gui    
        ui = indexGui('view_461_comments.xml' , addon_path, defaultSkin='Default', defaultRes='1080i', subreddits_file=subredditsFile, id=55)
        ui.title_bar_text="Reddit Reader"
        ui.include_parent_directory_entry=False
    
        ui.doModal()
        del ui
    
    return
    
def build_script( mode, url, name="", type="", script_to_call=addonID):
    #builds the parameter for xbmc.executebuiltin   --> 'RunAddon(script.reddit.reader, ... )'
    return "RunAddon(%s,%s)" %(addonID, "?mode="+ mode+"&url="+urllib.quote_plus(url)+"&name="+str(name)+"&type="+str(type) )

def build_playable_param( mode, url, name="", type="", script_to_call=addonID):
    #builds the  di_url for  pl = xbmc.PlayList(xbmc.PLAYLIST_VIDEO); pl.clear();  pl.add(di_url, item) ; xbmc.Player().play(pl, windowed=True)
    return "plugin://" +script_to_call+"?mode="+ mode+"&url="+urllib.quote_plus(url)+"&name="+str(name)+"&type="+str(type)

#MODE listSubReddit(url, name, type)    --name not used
def listSubReddit(url, title_bar_name, type):
    from resources.domains import parse_filename_and_ext_from_url
    #url=r'https://www.reddit.com/r/videos/search.json?q=nsfw:yes+site%3Ayoutu.be+OR+site%3Ayoutube.com+OR+site%3Avimeo.com+OR+site%3Aliveleak.com+OR+site%3Adailymotion.com+OR+site%3Agfycat.com&sort=relevance&restrict_sr=on&limit=5&t=week'
    #url='https://www.reddit.com/search.json?q=site%3Adailymotion&restrict_sr=&sort=relevance&t=week'
    #url='https://www.reddit.com/search.json?q=site%3A4tube&sort=relevance&t=all'
    #url="https://www.reddit.com/domain/tumblr.com.json"
    #url="https://www.reddit.com/r/wiiu.json?&nsfw:no+&limit=13"

    #show_listSubReddit_debug=False
    show_listSubReddit_debug=True
    credate = ""
    is_a_video=False
    title_line2=""

    thumb_w=0
    thumb_h=0

    #the +'s got removed by url conversion 
    title_bar_name=title_bar_name.replace(' ','+')
    #log("  title_bar_name %s " %(title_bar_name) )

    log("listSubReddit subreddit=%s url=%s" %(title_bar_name,url) )
    t_on = translation(30071)  #"on"
    #t_pts = u"\U0001F4AC"  # translation(30072) #"cmnts"  comment bubble symbol. doesn't work
    t_pts = u"\U00002709"  # translation(30072)   envelope symbol
    
    li=[]

    currentUrl = url
        
    content = reddit_request(url)  #content = opener.open(url).read()
    
    if not content:
        return

#     info_label={ "plot": translation(30013) }  #Automatically play videos
#     if showAllNewest:
#         addDir("[B]- "+translation(30016)+"[/B]", url, 'autoPlay', "", "ALL_NEW", info_label)
#     if showUnwatchedNewest:
#         addDir("[B]- "+translation(30017)+"[/B]", url, 'autoPlay', "", "UNWATCHED_NEW", info_label)
#     if showUnfinishedNewest:
#         addDir("[B]- "+translation(30018)+"[/B]", url, 'autoPlay', "", "UNFINISHED_NEW", info_label)
#     if showAll:
#         addDir("[B]- "+translation(30012)+"[/B]", url, 'autoPlay', "", "ALL_RANDOM", info_label)
#     if showUnwatched:
#         addDir("[B]- "+translation(30014)+"[/B]", url, 'autoPlay', "", "UNWATCHED_RANDOM", info_label)
#     if showUnfinished:
#         addDir("[B]- "+translation(30015)+"[/B]", url, 'autoPlay', "", "UNFINISHED_RANDOM", info_label)

    
    #7-15-2016  removed the "replace(..." statement below cause it was causing error
    #content = json.loads(content.replace('\\"', '\''))
    content = json.loads(content) 
    
    #log("query returned %d items " % len(content['data']['children']) )
    posts_count=len(content['data']['children'])
    
    hms = has_multiple_subreddits(content['data']['children'])
    
    for idx, entry in enumerate(content['data']['children']):
        try:
            title = cleanTitle(entry['data']['title'].encode('utf-8'))
            is_a_video = determine_if_video_media_from_reddit_json(entry)
            if show_listSubReddit_debug : log("  POST%cTITLE%.2d=%s" %( ("v" if is_a_video else " "), idx, title ))
            
            try:
                description = cleanTitle(entry['data']['media']['oembed']['description'].encode('utf-8'))
            except:
                description = ' '
                
            commentsUrl = urlMain+entry['data']['permalink'].encode('utf-8')
            #if show_listSubReddit_debug :log("commentsUrl"+str(idx)+"="+commentsUrl)
            
            try:
                aaa = entry['data']['created_utc']
                credate = datetime.datetime.utcfromtimestamp( aaa )
                #log("creation_date="+str(credate))
                
                ##from datetime import datetime
                #now = datetime.datetime.now()
                #log("     now_date="+str(now))
                ##from dateutil import tz
                now_utc = datetime.datetime.utcnow()
                #log("     utc_date="+str(now_utc))
                #log("  pretty_date="+pretty_datediff(now_utc, credate))
                pretty_date=pretty_datediff(now_utc, credate)
                credate = str(credate)
            except:
                credate = ""
                credateTime = ""

            subreddit=entry['data']['subreddit'].encode('utf-8')
            #if show_listSubReddit_debug :log("  SUBREDDIT"+str(idx)+"="+subreddit)
            try: author = entry['data']['author'].encode('utf-8')
            except: author = ""
            
            try: domain= entry['data']['domain'].encode('utf-8')
            except: domain = ""
            #log("     DOMAIN%.2d=%s" %(idx,domain))
            
            ups = entry['data']['score']       #downs not used anymore
            try:num_comments = entry['data']['num_comments']
            except:num_comments = 0
            
            #description = "[COLOR blue]r/"+ subreddit + "[/COLOR]  [I]" + str(ups)+" pts  |  "+str(comments)+" cmnts  |  by "+author+"[/I]\n"+description
            #description = "[COLOR blue]r/"+ subreddit + "[/COLOR]  [I]" + str(ups)+" pts.  |  by "+author+"[/I]\n"+description
            #description = title_line2+"\n"+description
            #if show_listSubReddit_debug :log("DESCRIPTION"+str(idx)+"=["+description+"]")
            try:
                media_url = entry['data']['url'].encode('utf-8')
            except:
                media_url = entry['data']['media']['oembed']['url'].encode('utf-8')
                
            #media_url=media_url.lower()  #!!! note: do not lowercase!!!     
            
            thumb = entry['data']['thumbnail'].encode('utf-8')
            if thumb in ['default','self']:  #reddit has a "default" thumbnail (alien holding camera with "?")
                thumb=""               

            if thumb=="":
                try: thumb = entry['data']['media']['oembed']['thumbnail_url'].encode('utf-8').replace('&amp;','&')
                except: pass
            
            
            try:
                #collect_thumbs(entry)
                preview=entry['data']['preview']['images'][0]['source']['url'].encode('utf-8').replace('&amp;','&')
                #poster = entry['data']['media']['oembed']['thumbnail_url'].encode('utf-8')
                #t=thumb.split('?')[0]
                #can't preview gif thumbnail on thumbnail view, use alternate provided by reddit
                #if t.endswith('.gif'):
                    #log('  thumb ends with .gif')
                #    thumb = entry['data']['thumbnail'].encode('utf-8')
                
                filename,ext=parse_filename_and_ext_from_url(preview.split('?')[0])
                if ext == 'gif': #we can't handle gif thumbnail
                    preview=""
                    thumb_w=0
                    thumb_h=0
                    #raise something
                try:
                    thumb_h = float( entry['data']['preview']['images'][0]['source']['height'] )
                    thumb_w = float( entry['data']['preview']['images'][0]['source']['width'] )
                except:
                    thumb_w=0
                    thumb_h=0
                pass
            except Exception as e:
                #log("   getting preview image EXCEPTION:="+ str( sys.exc_info()[0]) + "  " + str(e) )
                thumb_w=0
                thumb_h=0
                preview="" #a blank preview image will be replaced with poster_url from make_addon_url_from() for domains that support it

            try:
                over_18 = entry['data']['over_18']
            except:
                over_18 = False

            #setting: toggle showing 2-line title 
            #log("   TitleAddtlInfo "+str(idx)+"="+str(TitleAddtlInfo))
            title_line2=""
            #if TitleAddtlInfo:
            #title_line2 = "[I][COLOR dimgrey]%s by %s [COLOR darkslategrey]r/%s[/COLOR] %d pts.[/COLOR][/I]" %(pretty_date,author,subreddit,ups)
            #title_line2 = "[I][COLOR dimgrey]"+pretty_date+" by "+author+" [COLOR darkslategrey]r/"+subreddit+"[/COLOR] "+str(ups)+" pts.[/COLOR][/I]"

            title_line2 = "[I][COLOR dimgrey]%s %s [COLOR darkslategrey]r/%s[/COLOR] (%d) %s[/COLOR][/I]" %(pretty_date,t_on, subreddit,num_comments, t_pts)
            #title_line2 = "[I]"+str(idx)+". [COLOR dimgrey]"+ media_url[0:50]  +"[/COLOR][/I] "  # +"    "+" [COLOR darkslategrey]r/"+subreddit+"[/COLOR] "+str(ups)+" pts.[/COLOR][/I]"

            #if show_listSubReddit_debug :log("      OVER_18"+str(idx)+"="+str(over_18))
            #if show_listSubReddit_debug :log("   IS_A_VIDEO"+str(idx)+"="+str(is_a_video))
            #if show_listSubReddit_debug :log("        THUMB"+str(idx)+"="+thumb)
            #if show_listSubReddit_debug :log("    MediaURL%.2d=%s" % (idx,media_url) )

            #if show_listSubReddit_debug :log("       HOSTER"+str(idx)+"="+hoster)
            #log("    VIDEOID"+str(idx)+"="+videoID)
            #log( "["+description+"]1["+ str(date)+"]2["+ str( count)+"]3["+ str( commentsUrl)+"]4["+ str( subreddit)+"]5["+ video_url +"]6["+ str( over_18))+"]"
            liz=addLink(title=title, 
                    title_line2=title_line2,
                    iconimage=thumb, 
                    previewimage=preview,
                    preview_w=thumb_w,
                    preview_h=thumb_h,
                    domain=domain,
                    description=description, 
                    credate=credate, 
                    reddit_says_is_video=is_a_video, 
                    site=commentsUrl, 
                    subreddit=subreddit, 
                    link_url=media_url, 
                    over_18=over_18,
                    posted_by=author,
                    num_comments=num_comments,
                    post_index=idx,
                    post_total=posts_count,
                    many_subreddit=hms)
            
            li.append(liz)
            
        except Exception as e:
            log(" EXCEPTION:="+ str( sys.exc_info()[0]) + "  " + str(e) )
            pass
    
    #log("**reddit query returned "+ str(idx) +" items")
    #window = xbmcgui.Window(xbmcgui.getCurrentWindowId())
    #log("focusid:"+str(window.getFocusId()))

    try:
        #this part makes sure that you load the next page instead of just the first
        after=""
        after = content['data']['after']
        if after: 
            if "&after=" in currentUrl:
                nextUrl = currentUrl[:currentUrl.find("&after=")]+"&after="+after
            else:
                nextUrl = currentUrl+"&after="+after
            
            # plot shows up on estuary. etc. ( avoids the "No information available" message on description ) 
            info_label={ "plot": translation(32004) } 
             
            #addDir(translation(32004), nextUrl, 'listSubReddit', "", subreddit,info_label)   #Next Page
            
            liz = compose_list_item( translation(32004), "", "DefaultFolderNextSquare.png", "script", build_script("listSubReddit",nextUrl,title_bar_name), {'plot': translation(32004)} )
            
            li.append(liz)
        
        #if show_listSubReddit_debug :log("NEXT PAGE="+nextUrl) 
    except Exception as e:
        log(" EXCEPTzION:="+ str( sys.exc_info()[0]) + "  " + str(e) )
        
        pass
    

    #xbmcplugin.endOfDirectory(pluginhandle)
    
    from resources.guis import listSubRedditGUI    
    ui = listSubRedditGUI('view_462_listSubReddit.xml' , addon_path, defaultSkin='Default', defaultRes='1080i', listing=li, subreddits_file=subredditsFile, id=55)
    ui.title_bar_text=title_bar_name
    #ui.include_parent_directory_entry=True

    ui.doModal()
    
    #ui.show()  #<-- interesting possibilities. you have to handle the actions outside of the gui class. 
    #xbmc.sleep(8000)

def addLink(title, title_line2, iconimage, previewimage,preview_w,preview_h,domain, description, credate, reddit_says_is_video, site, subreddit, link_url, over_18, posted_by="", num_comments=0,post_index=1,post_total=1,many_subreddit=False ):
    
    videoID=""
    post_title=title
    il_description=""
    n=""  #will hold red nsfw asterisk string
    h=""  #will hold bold hoster:  string
    t_Album = translation(30073) if translation(30073) else "Album"
    t_IMG =  translation(30074) if translation(30074) else "IMG"
    #title_line2= "3 days ago on r/all 5 comments."
    
    ok = False    
    #DirectoryItem_url=""

    preview_ar=0.0
    if preview_w==0 or preview_h==0:
        preview_ar=0.0
    else:
        preview_ar=float(preview_w) / preview_h
    
    #log( "    w:%d h:%d ar:%f" %(preview_w,preview_h,preview_ar ))

    from resources.domains import make_addon_url_from
    hoster, DirectoryItem_url, videoID, mode_type, thumb_url, poster_url, isFolder,setInfo_type, property_link_type=make_addon_url_from(link_url,reddit_says_is_video )
    
    #mode=mode_type #usually 'playVideo'
    if hoster: pass
    else:hoster="---"
        
    h="[B]" + hoster + "[/B] "
    if over_18: 
        mpaa="R"
        #n = "[COLOR red]*[/COLOR] "
        #description = "[B]" + hoster + "[/B]:[COLOR red][NSFW][/COLOR] "+title+"\n" + description
        il_description = "[COLOR red][NSFW][/COLOR] "+ h+"[CR]" + "[COLOR grey]" + description + "[/COLOR]"
        title_line2 = "[COLOR red][NSFW][/COLOR] "+title_line2
    else:
        mpaa=""
        il_description = h+"[CR]" + "[COLOR grey]" + description + "[/COLOR]"

    post_title=title
    il_description=il_description
        
    il={"title": post_title, "plot": il_description, "plotoutline": il_description, "Aired": credate, "mpaa": mpaa, "Genre": "r/"+subreddit, "studio": domain, "director": posted_by }   #, "duration": 1271}   (duration uses seconds for titan skin

    log( '    reddit thumb[%s] reddit preview[%s] new-thumb[%s] poster[%s]  link_url:%s' %(iconimage,previewimage, thumb_url, poster_url, link_url ))
    if iconimage in ["","nsfw", "default"]:
        iconimage=thumb_url
    if poster_url=="":
        poster_url=iconimage
    
    #log( "  PLOT:" +il_description )
    liz=xbmcgui.ListItem(label=n+post_title
                         ,label2=title_line2
                         ,iconImage="DefaultVideo.png"
                         ,thumbnailImage=iconimage
                         ,path=DirectoryItem_url) 

    if previewimage=="":
        #log("putting preview image")
        liz.setArt({"thumb": iconimage, "poster":poster_url, "banner":poster_url, "fanart":poster_url, "landscape":poster_url   })
    else:
        liz.setArt({"thumb": iconimage, "poster":poster_url, "banner":previewimage, "fanart":poster_url, "landscape":poster_url   })
    

    #----- assign actions
    if preview_ar>0 and preview_ar <= 0.5625 and preview_h > 1090 :   #vertical image taken by 16:9 camera will have 0.5625 aspect ratio. anything narrower than that, we will zoom_n_slide
        from resources.domains import link_url_is_playable
        if link_url_is_playable(link_url):
            liz.setProperty('right_button_action', build_script('zoom_n_slide', link_url,int(preview_w),int(preview_h) ) )                      

    liz.setProperty('comments_action', build_script('listLinksInComment', site ) )        
    
    liz.setProperty('goto_subreddit_action', build_script("listSubReddit", assemble_reddit_filter_string("",subreddit), subreddit) )
    #----- assign actions
    
    liz.setInfo(type='video', infoLabels=il)

    #use clearart to indicate if link is video, album or image. here, we default to unsupported.
    liz.setArt({ "clearart": "type_unsupp.png"  }) 
    
    if DirectoryItem_url:

        if setting_hide_images==True and mode_type in ['listImgurAlbum','playSlideshow','listLinksInComment' ]:
            log('setting: hide non-video links') #and text links(reddit.com)
            return
        else:
            if mode_type in ['listImgurAlbum','playSlideshow','listLinksInComment','playTumblr','playInstagram','playFlickr' ]:
                #after all that work creating DirectoryItem_url, we parse it to get the media_url. this is used by playSlideshow as 'key' to get the image description
                #parsed = urlparse.urlparse(DirectoryItem_url)
                #media_url=urlparse.parse_qs(parsed.query)['url'][0]  #<-- this will error in openelec/linux    
                #log("   parsed media_url:" +  media_url  )
                #log("   parsed plugi_url:" +  videoID  )
                #WINDOW.setProperty(videoID, description )
                #WINDOW.setProperty(videoID, il_description )
                pass


        #use clearart to indicate if link is video, album or image 
        liz.setArt({ "clearart":"type_video.png"  })
        if mode_type in ['listImgurAlbum','listTumblrAlbum', 'listFlickrAlbum']:
            liz.setArt({ "clearart":"type_album.png"  })    #post_title='[%s] %s' %(t_Album, post_title)
        if setInfo_type=='pictures'  : 
            liz.setArt({ "clearart":"type_image.png"  })    #post_title='[%s] %s' %(t_IMG, post_title)   
        if mode_type=='listLinksInComment': 
            liz.setArt({ "clearart":"changelog.png"  })    #post_title='[reddit] '+post_title  



        
        
        #art_object
        #liz.setArt({ "poster":poster_url  })
        #liz.setArt({"thumb": iconimage, "poster":poster_url, "banner":iconimage, "fanart":poster_url, "landscape":poster_url   })

        #liz.setInfo(type=setInfo_type, infoLabels=il)

        
        entries = [] #entries for listbox for when you type 'c' or rt-click 


        if num_comments > 0:            
            #if we are using a custom gui to show comments, we need to use RunPlugin. there is a weird loading/pause if we use XBMC.Container.Update. i think xbmc expects us to use addDirectoryItem
            #  if we have xbmc manage the gui(addDirectoryItem), we need to use XBMC.Container.Update. otherwise we'll get the dreaded "Attempt to use invalid handle -1" error

            if comments_viewMode=='461':  #461 is my trigger to use a custom gui for showing comments. it is just an arbitrary number. i'm hoping there no skin will use the same viewid
                entries.append( ( translation(30050) + " (c)",  #Show comments
                              "XBMC.RunPlugin(%s?path=%s?prl=zaza&mode=listLinksInComment&url=%s)" % ( sys.argv[0], sys.argv[0], urllib.quote_plus(site) ) ) )            
                entries.append( ( translation(30052) , #Show comment links 
                              "XBMC.Container.Update(%s?path=%s?prl=zaza&mode=listLinksInComment&url=%s&type=linksOnly)" % ( sys.argv[0], sys.argv[0], urllib.quote_plus(site) ) ) )            
            else:  
                entries.append( ( translation(30052) , #Show comment links 
                              "XBMC.Container.Update(%s?path=%s?prl=zaza&mode=listLinksInComment&url=%s&type=linksOnly)" % ( sys.argv[0], sys.argv[0], urllib.quote_plus(site) ) ) )            
                entries.append( ( translation(30050) ,  #Show comments
                              "XBMC.Container.Update(%s?path=%s?prl=zaza&mode=listLinksInComment&url=%s)" % ( sys.argv[0], sys.argv[0], urllib.quote_plus(site) ) ) )            

            #entries.append( ( translation(30050) + " (ActivateWindow)",  #Show comments
            #              "XBMC.ActivateWindow(Video, %s?mode=listLinksInComment&url=%s)" % (  sys.argv[0], urllib.quote_plus(site) ) ) )      #***  ActivateWindow is for the standard xbmc window     
        else:
            entries.append( ( translation(30053) ,  #No comments
                          "xbmc.executebuiltin('Action(Close)')" ) )            

                
        #no need to show the "go to other subreddits" if the entire list is from one subreddit        
        if many_subreddit:
            #sys.argv[0] is plugin://plugin.video.reddit_viewer/
            #prl=zaza is just a dummy: during testing the first argument is ignored... possible bug?
            entries.append( ( translation(30051)+" r/%s" %subreddit , 
                              "XBMC.Container.Update(%s?path=%s?prl=zaza&mode=listSubReddit&url=%s)" % ( sys.argv[0], sys.argv[0],urllib.quote_plus(assemble_reddit_filter_string("",subreddit,True)  ) ) ) )
        else:
            entries.append( ( translation(30051)+" r/%s" %subreddit , 
                              "XBMC.Container.Update(%s?path=%s?prl=zaza&mode=listSubReddit&url=%s)" % ( sys.argv[0], sys.argv[0],urllib.quote_plus(assemble_reddit_filter_string("",subreddit+'/new',True)  ) ) ) )


        #favEntry = '<favourite name="'+title+'" url="'+DirectoryItem_url+'" description="'+description+'" thumb="'+iconimage+'" date="'+credate+'" site="'+site+'" />'
        #entries.append((translation(30022), 'RunPlugin(plugin://'+addonID+'/?mode=addToFavs&url='+urllib.quote_plus(favEntry)+'&type='+urllib.quote_plus(subreddit)+')',))
        
        #if showBrowser and (osWin or osOsx or osLinux):
        #    if osWin and browser_win==0:
        #        entries.append((translation(30021), 'RunPlugin(plugin://plugin.program.webbrowser/?url='+urllib.quote_plus(site)+'&mode=showSite&zoom='+browser_wb_zoom+'&stopPlayback=no&showPopups=no&showScrollbar=no)',))
        #    else:
        #        entries.append((translation(30021), 'RunPlugin(plugin://plugin.program.chrome.launcher/?url='+urllib.quote_plus(site)+'&mode=showSite)',))
        liz.addContextMenuItems(entries)

        #xbmcplugin.addDirectoryItem(pluginhandle, DirectoryItem_url, listitem=liz, isFolder=isFolder, totalItems=post_total)
        liz.setProperty('item_type',property_link_type)
        liz.setProperty('onClick_action',DirectoryItem_url)
        
        
    else:
        #unsupported type here:
        pass

    return liz
#MODE listFavourites -  name, type not used
# def listFavourites(subreddit, name, type):
#     xbmcplugin.setContent(pluginhandle, "episodes")
#     file = os.path.join(addonUserDataFolder, subreddit+".fav")
#     xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)
#     if os.path.exists(file):
#         fh = open(file, 'r')
#         content = fh.read()
#         fh.close()
#         match = re.compile('<favourite name="(.+?)" url="(.+?)" description="(.+?)" thumb="(.+?)" date="(.+?)" site="(.+?)" />', re.DOTALL).findall(content)
#         for name, url, desc, thumb, date, site in match:
#             addFavLink(name, url, "playVideo", thumb, desc.replace("<br>","\n"), date, site, subreddit)
#     if forceViewMode:
#         xbmc.executebuiltin('Container.SetViewMode('+viewMode+')')
#     xbmcplugin.endOfDirectory(pluginhandle)

#MODE autoPlay        - name not used
def autoPlay(url, name, type):
    from resources.domains import make_addon_url_from
    #collect a list of title and urls as entries[] from the j_entries obtained from reddit
    #then create a playlist from those entries
    #then play the playlist

    entries = []
    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    playlist.clear()
    log("**********autoPlay*************")
    #content = opener.open(url).read()
    content = reddit_request(url)        
    if not content: return

    content = json.loads(content.replace('\\"', '\''))
    
    log("Autoplay %s - Parsing %d items" %( type, len(content['data']['children']) )    )
    
    for j_entry in content['data']['children']:
        try:
            #title = cleanTitle(entry['data']['media']['oembed']['title'].encode('utf-8'))
            title = cleanTitle(j_entry['data']['title'].encode('utf-8'))

            try:
                media_url = j_entry['data']['url']
            except:
                media_url = j_entry['data']['media']['oembed']['url']

            is_a_video = determine_if_video_media_from_reddit_json(j_entry) 

            #log("  Title:%s -%c"  %( title, ("v" if is_a_video else " ") ) )              
            hoster, DirectoryItem_url, videoID, mode_type, thumb_url,poster_url, isFolder,setInfo_type, IsPlayable=make_addon_url_from(media_url,is_a_video)

            if DirectoryItem_url:
                if isFolder:  #imgur albums are 'isFolder'
                    #log('      skipping isFolder ')
                    continue
                if setInfo_type=='pictures': #we also skip images in autoplay
                    #log('      skipping setInfo_type==pictures ')
                    continue
                
                if setting_hide_images==True and mode_type in ['listImgurAlbum','playSlideshow','listLinksInComment' ]:
                    #log("      skipping 'listImgurAlbum','playSlideshow','listLinksInComment' ")
                    continue                
                
                if type.startswith("ALL_"):
                    #log("      ALL_" )
                    entries.append([title, DirectoryItem_url])
                elif type.startswith("UNWATCHED_") and getPlayCount(url) < 0:
                    #log("      UNWATCHED_" )
                    entries.append([title, DirectoryItem_url])
                elif type.startswith("UNFINISHED_") and getPlayCount(url) == 0:
                    #log("      UNFINISHED_" )
                    entries.append([title, DirectoryItem_url])
        except:
            pass
    
    if type.endswith("_RANDOM"):
        random.shuffle(entries)

    #for title, url in entries:
    #    log("  added to playlist:"+ title + "  " + urllib.unquote_plus(url) )
    for title, url in entries:
        listitem = xbmcgui.ListItem(title)
        playlist.add(url, listitem)
    xbmc.Player().play(playlist)

def collect_thumbs( entry ):
    #collect the thumbs from reddit json
    dictList = []
    keys=['thumb','width','height']
    e=[]
    
    try:
        e=[ entry['data']['media']['oembed']['thumbnail_url'].encode('utf-8')
           ,entry['data']['media']['oembed']['thumbnail_width']
           ,entry['data']['media']['oembed']['thumbnail_height']
           ]
        #log('  got 1')
        dictList.append(dict(zip(keys, e)))
    except Exception as e:
        #log( "zz   " + str(e) ) 
        pass
    
    try:
        e=[ entry['data']['preview']['images'][0]['source']['url'].encode('utf-8')
           ,entry['data']['preview']['images'][0]['source']['width']
           ,entry['data']['preview']['images'][0]['source']['height']
           ]
        #log('  got 2')
        dictList.append(dict(zip(keys, e)))
    except: pass
    
    try:
        e=[ entry['data']['thumbnail'].encode('utf-8')        #thumbnail is always in 140px wide (?)
           ,140
           ,0
           ]
        #log('  got 3')
        dictList.append(dict(zip(keys, e)))
    except: pass
        
    #log( json.dumps(dictList, indent=4)  )
    #log( str(dictList)  )
    
    return 

def determine_if_video_media_from_reddit_json( entry ):
    #reads the reddit json and determines if link is a video
    is_a_video=False
    
    try:
        media_url = entry['data']['media']['oembed']['url']   #+'"'
    except:
        media_url = entry['data']['url']   #+'"'


    # also check  "post_hint" : "rich:video"
    
    media_url=media_url.split('?')[0] #get rid of the query string
    try:
        zzz = entry['data']['media']['oembed']['type']
        #log("    zzz"+str(idx)+"="+str(zzz))
        if zzz == None:   #usually, entry['data']['media'] is null for not videos but it is also null for gifv especially nsfw
            if ".gifv" in media_url.lower():  #special case for imgur
                is_a_video=True
            else:
                is_a_video=False
        elif zzz == 'video':  
            is_a_video=True
        else:
            is_a_video=False
    except:
        is_a_video=False

    return is_a_video

def has_multiple_subreddits(content_data_children):
    #check if content['data']['children'] returned by reddit contains a single subreddit or not
    s=""
    #compare the first subreddit with the rest of the list. 
    for entry in content_data_children:
        if s:
            if s!=entry['data']['subreddit'].encode('utf-8'):
                #log("  multiple subreddit")
                return True
        else:
            s=entry['data']['subreddit'].encode('utf-8')
    
    #log("  single subreddit")
    return False


def getLiveLeakStreamUrl(id):
    #log("getLiveLeakStreamUrl ID="+str(id) )
    #sometimes liveleak items are news articles and not video. 
    url=None
    content = opener.open("http://www.liveleak.com/view?i="+id).read()
    matchHD = re.compile('hd_file_url=(.+?)&', re.DOTALL).findall(content)
    matchSD = re.compile('file: "(.+?)"', re.DOTALL).findall(content)
    if matchHD and ll_qualiy=="720p":
        url = urllib.unquote_plus(matchHD[0])
    elif matchSD:
        url = matchSD[0]
    #log("**********getLiveLeakStreamUrl hd_file_url="+url)
    return url

#MODE playVideo       - name, type not used
def playVideo(url, name, type):
    xbmc.executebuiltin( "Dialog.Close(busydialog)" )
    #log("playVideo:"+url)
    if url :
        xbmc.Player().play(url, windowed=False)  #scripts play video like this.

        #listitem = xbmcgui.ListItem(path=url)   #plugins play video like this.
        #xbmcplugin.setResolvedUrl(pluginhandle, True, listitem) 
    else:
        log("playVideo(url) url is blank")
        
        
        
def playYTDLVideo(url, name, type):
    #url = "http://www.youtube.com/watch?v=_yVv9dx88x0"   #a youtube ID will work as well and of course you could pass the url of another site
    log("playYTDLVideo="+url)
    #url='https://www.youtube.com/shared?ci=W8n3GMW5RCY'
    #url='http://burningcamel.com/video/waster-blonde-amateur-gets-fucked'
    #url='http://www.3sat.de/mediathek/?mode=play&obj=51264'
    #url='http://www.rappler.com/nation/141700-full-text-leila-de-lima-privilege-speech-extrajudicial-killings'
    #url='http://pinoytrending.altervista.org/watch-sen-cayetano-responded-sen-de-limas-privilage-speech-extrajudicial-killings/'
    choices = []

#these checks done in around May 2016
#does not work:  yourlust  porntube xpornvid.com porndig.com  thumbzilla.com eporner.com yuvutu.com porn.com pornerbros.com fux.com flyflv.com xstigma.com sexu.com 5min.com alphaporno.com
# stickyxtube.com xxxbunker.com bdsmstreak.com  jizzxman.com pornwebms.com pornurl.pw porness.tv openload.online pornworms.com fapgod.com porness.tv hvdporn.com pornmax.xyz xfig.net yobt.com
# eroshare.com kalporn.com hdvideos.porn dailygirlscute.com desianalporn.com indianxxxhd.com onlypron.com sherloxxx.com hdvideos.porn x1xporn.com pornhvd.com lxxlx.com xrhub.com shooshtime.com
# pornvil.com lxxlx.com redclip.xyz younow.com aniboom.com  gotporn.com  virtualtaboo.com 18porn.xyz vidshort.net fapxl.com vidmega.net freudbox.com bigtits.com xfapzap.com orgasm.com
# userporn.com hdpornstar.com moviesand.com chumleaf.com fucktube.com fookgle.com pornative.com dailee.com pornsharia.com fux.com sluttyred.com pk5.net kuntfutube.com youpunish.com
# vidxnet.com jizzbox.com bondagetube.tv spankingtube.tv pornheed.com pornwaiter.com lubetube.com porncor.com maxjizztube.com asianxtv.com analxtv.com yteenporn.com nurglestube.com yporn.tv
# asiantubesex.com zuzandra.com moviesguy.com bustnow.com dirtydirtyangels.com yazum.com watchersweb.com voyeurweb.com zoig.com flingtube.com yourfreeporn.us foxgay.com goshgay.com
# player.moviefap.com(www.moviefap.com works) nosvideo.com

# also does not work (non porn)
# rutube.ru  mail.ru  afreeca.com nicovideo.jp  videos.sapo.pt(many but not all) sciencestage.com vidoosh.tv metacafe.com vzaar.com videojug.com trilulilu.ro tudou.com video.yahoo.com blinkx.com blip.tv
# blogtv.com  brainpop.com crackle.com engagemedia.org expotv.com flickr.com fotki.com hulu.com lafango.com  mefeedia.com motionpictur.com izlesene.com sevenload.com patas.in myvideo.de
# vbox7.com 1tv.ru 1up.com 220.ro 24video.xxx 3sat.de 56.com adultswim.com atresplayer.com techchannel.att.com v.baidu.com azubu.tv www.bbc.co.uk/iplayer bet.com biobiochile.cl biqle.com
# bloomberg.com/news/videos bpb.de bravotv.com byutv.org cbc.ca chirbit.com cloudtime.to(almost) cloudyvideos.com cracked.com crackle.com criterion.com ctv.ca culturebox.francetvinfo.fr
# cultureunplugged.com cwtv.com daum.net dctp.tv democracynow.org douyutv.com dumpert.nl eitb.tv ex.fm fc-zenit.ru  ikudonsubs.com akb48ma.com Flipagram.com ft.dk Formula1.com
# fox.com/watch(few works) video.foxnews.com foxsports.com france2.fr franceculture.fr franceinter.fr francetv.fr/videos francetvinfo.fr giantbomb.com hbo.com History.com hitbox.tv
# howcast.com HowStuffWorks.com hrt.hr iconosquare.com infoq.com  ivi.ru kamcord.com/v video.kankan.com karrierevideos.at KrasView.ru hlamer.ru kuwo.cn la7.it laola1.tv le.com
# media.ccc.de metacritic.com mitele.es  moevideo.net,playreplay.net,videochart.net vidspot.net(might work, can't find recent post) movieclips.com mtv.de mtviggy.com muenchen.tv myspace.com
# myvi.ru myvideo.de myvideo.ge 163.com netzkino.de nfb.ca nicovideo.jp  videohive.net normalboots.com nowness.com ntr.nl nrk.no ntv.ru/video ocw.mit.edu odnoklassniki.ru/video 
# onet.tv onionstudios.com/videos openload.co orf.at parliamentlive.tv pbs.org

# news site (can't find sample to test) 
# bleacherreport.com crooksandliars.com DailyMail.com channel5.com Funimation.com gamersyde.com gamespot.com gazeta.pl helsinki.fi hotnewhiphop.com lemonde.fr mnet.com motorsport.com MSN.com
# n-tv.de ndr.de NDTV.com NextMedia.com noz.de


# these sites have mixed media. can handle the video in these sites: 
# 20min.ch 5min.com archive.org Allocine.fr(added) br.de bt.no  buzzfeed.com condenast.com firstpost.com gameinformer.com gputechconf.com heise.de HotStar.com(some play) lrt.lt natgeo.com
# nbcsports.com  patreon.com 
# 9c9media.com(no posts)

#ytdl plays this fine but no video?
#coub.com

#supported but is an audio only site 
#acast.com AudioBoom.com audiomack.com bandcamp.com clyp.it democracynow.org? freesound.org hark.com hearthis.at hypem.com libsyn.com mixcloud.com
#Minhateca.com.br(direct mp3) 

# 
# ytdl also supports these sites: 
# myvideo.co.za  ?
#bluegartr.com  (gif)
# behindkink.com   (not sure)
# facebook.com  (need to work capturing only videos)
# features.aol.com  (inconsistent)
# livestream.com (need to work capturing only videos)
# mail.ru inconsistent(need to work capturing only videos)
# miomio.tv(some play but most won't)
# ooyala.com(some play but most won't)
#  
    
#     extractors=[]
#     from youtube_dl.extractor import gen_extractors
#     for ie in gen_extractors():  
#         #extractors.append(ie.IE_NAME)
#         try:
#             log("[%s] %s " %(ie.IE_NAME, ie._VALID_URL) )
#         except Exception as e:
#             log( "zz   " + str(e) )

#     extractors.sort()
#     for n in extractors: log("'%s'," %n)

    #xbmc.executebuiltin("ActivateWindow(busydialog)")
    try:
        if YDStreamExtractor.mightHaveVideo(url,resolve_redirects=True):
            log('    YDStreamExtractor.mightHaveVideo[true]=' + url)
            vid = YDStreamExtractor.getVideoInfo(url,0,True)  #quality is 0=SD, 1=720p, 2=1080p and is a maximum
            if vid:
                log("      getVideoInfo playableURL="+vid.streamURL())
                if vid.hasMultipleStreams():
                    log("        vid hasMultipleStreams")
                    for s in vid.streams():
                        title = s['title']
                        log('      choices' + title  )
                        choices.append(title)
                    #index = some_function_asking_the_user_to_choose(choices)
                    vid.selectStream(0) #You can also pass in the the dict for the chosen stream
        
                stream_url = vid.streamURL()                         #This is what Kodi (XBMC) will play    

                playVideo(stream_url, name, type)
                
                #pl = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
                #pl.clear()
                #pl.add(stream_url)
                #xbmc.Player().play(stream_url, windowed=False)
                
                #plugins play video like below
                #listitem = xbmcgui.ListItem(path=stream_url)
                #xbmcplugin.setResolvedUrl(pluginhandle, True, listitem)
            else:
                #log("getVideoInfo failed==" )
                xbmc.executebuiltin('XBMC.Notification("'+ translation(30192) +'", "Youtube_dl" )' )  
    except Exception as e:
        #log( "zz   " + str(e) )
        xbmc.executebuiltin('XBMC.Notification("Youtube_dl","%s")' %str(e)  )

    #xbmc.executebuiltin( "Dialog.Close(busydialog)" )
        

#MODE playGfycatVideo       - name, type not used
def playGfycatVideo(id, name, type):
    log( "  play gfycat video " + id )
    content = opener.open("http://gfycat.com/cajax/get/"+id).read()
    content = json.loads(content.replace('\\"', '\''))
    
    
    if "gfyItem" in content and "webmUrl" in content["gfyItem"]:
        GfycatStreamUrl=content["gfyItem"]["webmUrl"]

    if GfycatStreamUrl: pass
    else:
        if "gfyItem" in content and "mp4Url" in content["gfyItem"]:
            GfycatStreamUrl=content["gfyItem"]["mp4Url"]


    playVideo(GfycatStreamUrl, name, type)

def listLinksInComment(url, name, type):
    from resources.domains import make_addon_url_from
    #called by context menu
    log('listLinksInComment:%s:%s' %(type,url) )

    #does not work for list comments coz key is the playable url (not reddit comments url)
    #msg=WINDOW.getProperty(url)
    #WINDOW.clearProperty( url )
    #log( '   msg=' + msg )

#     #for testing
#     from resources.guis import cGUI
#     #ui = cGUI('FileBrowser.xml' , addon_path, defaultSkin='Default', defaultRes='1080i', listing=li)
#     ui = cGUI('view_461_comments.xml' , addon_path, defaultSkin='Default', defaultRes='1080i')
#     
#     ui.doModal()
#     del ui
#     return

    directory_items=[]
    author=""
    ShowOnlyCommentsWithlink=False

    if type=='linksOnly':
        ShowOnlyCommentsWithlink=True
        using_custom_gui=False #for now, our custom gui cannot handle links very well. we will let kodi handle it
    else:
        using_custom_gui=True
        
    #sometimes the url has a query string. we discard it coz we add .json at the end
    #url=url.split('?', 1)[0]+'.json'

    #url='https://www.reddit.com/r/Music/comments/4k02t1/bonnie_tyler_total_eclipse_of_the_heart_80s_pop/' + '.json'
    #only get up to "https://www.reddit.com/r/Music/comments/4k02t1". 
    #   do not include                                            "/bonnie_tyler_total_eclipse_of_the_heart_80s_pop/"
    #   because we'll have problem when it looks like this: "https://www.reddit.com/r/Overwatch/comments/4nx91h/ever_get_that_feeling_dÃ©jÃ _vu/"
    
    url=re.findall(r'(.*/comments/[A-Za-z0-9]+)',url)[0] 
    url+='.json'
    #log("listLinksInComment:"+url)

    #content = opener.open(url).read()  
    
    content = reddit_request(url)        
    if not content: return
    #content = r'[{"kind": "Listing", "data": {"modhash": "s3jpm9s7w782013e26e5e0682cf496a0741908d7f8c51b8c82", "children": [{"kind": "t3", "data": {"domain": "liveleak.com", "banned_by": null, "media_embed": {"content": "&lt;iframe class=\"embedly-embed\" src=\"//cdn.embedly.com/widgets/media.html?src=http%3A%2F%2Fwww.liveleak.com%2Fll_embed%3Ff%3D66d76ef92fcf&amp;url=http%3A%2F%2Fwww.liveleak.com%2Fview%3Fi%3D3b5_1469728820&amp;image=https%3A%2F%2Fcdn.liveleak.com%2F80281E%2Fll_a_u%2Fthumbs%2F2016%2FJul%2F28%2F66d76ef92fcf_sf_7.jpg&amp;key=2aa3c4d5f3de4f5b9120b660ad850dc9&amp;type=text%2Fhtml&amp;schema=liveleak\" width=\"600\" height=\"338\" scrolling=\"no\" frameborder=\"0\" allowfullscreen&gt;&lt;/iframe&gt;", "width": 600, "scrolling": false, "height": 338}, "subreddit": "redditviewertesting", "selftext_html": null, "selftext": "", "likes": true, "suggested_sort": null, "user_reports": [], "secure_media": null, "link_flair_text": null, "id": "4v8hk9", "from_kind": null, "gilded": 0, "archived": false, "clicked": false, "report_reasons": null, "author": "gsonide", "media": {"oembed": {"provider_url": "http://www.liveleak.com/", "description": "When this man was washing his car at 2am with his brother in the car, he was nearly attacked by two armed hijackers. However, the criminals were in for a surprise when he fought both of them off using", "title": "LiveLeak.com - Driver Thwarts Carjacking at Car Wash with Hose", "type": "video", "thumbnail_width": 1024, "height": 338, "width": 600, "html": "&lt;iframe class=\"embedly-embed\" src=\"//cdn.embedly.com/widgets/media.html?src=http%3A%2F%2Fwww.liveleak.com%2Fll_embed%3Ff%3D66d76ef92fcf&amp;url=http%3A%2F%2Fwww.liveleak.com%2Fview%3Fi%3D3b5_1469728820&amp;image=https%3A%2F%2Fcdn.liveleak.com%2F80281E%2Fll_a_u%2Fthumbs%2F2016%2FJul%2F28%2F66d76ef92fcf_sf_7.jpg&amp;key=2aa3c4d5f3de4f5b9120b660ad850dc9&amp;type=text%2Fhtml&amp;schema=liveleak\" width=\"600\" height=\"338\" scrolling=\"no\" frameborder=\"0\" allowfullscreen&gt;&lt;/iframe&gt;", "version": "1.0", "provider_name": "LiveLeak.com", "thumbnail_url": "https://cdn.liveleak.com/80281E/ll_a_u/thumbs/2016/Jul/28/66d76ef92fcf_sf_7.jpg", "thumbnail_height": 432}, "type": "liveleak.com"}, "name": "t3_4v8hk9", "score": 1, "approved_by": null, "over_18": false, "hidden": false, "preview": {"images": [{"source": {"url": "https://i.redditmedia.com/VqdviP5_R14GRQ1YSVV4oBaNuX_7lBwrhxlPxRtAGrw.jpg?s=0287a1da16226199bf58c83c9f6856d4", "width": 1024, "height": 432}, "resolutions": [{"url": "https://i.redditmedia.com/VqdviP5_R14GRQ1YSVV4oBaNuX_7lBwrhxlPxRtAGrw.jpg?fit=crop&amp;crop=faces%2Centropy&amp;arh=2&amp;w=108&amp;s=eb4c7d7ddcf20711effcb1bf0fd8632a", "width": 108, "height": 45}, {"url": "https://i.redditmedia.com/VqdviP5_R14GRQ1YSVV4oBaNuX_7lBwrhxlPxRtAGrw.jpg?fit=crop&amp;crop=faces%2Centropy&amp;arh=2&amp;w=216&amp;s=2e4b6493cfc10bd470e63547fea71f65", "width": 216, "height": 91}, {"url": "https://i.redditmedia.com/VqdviP5_R14GRQ1YSVV4oBaNuX_7lBwrhxlPxRtAGrw.jpg?fit=crop&amp;crop=faces%2Centropy&amp;arh=2&amp;w=320&amp;s=d79e371f714793280e0e27f9814a77df", "width": 320, "height": 135}, {"url": "https://i.redditmedia.com/VqdviP5_R14GRQ1YSVV4oBaNuX_7lBwrhxlPxRtAGrw.jpg?fit=crop&amp;crop=faces%2Centropy&amp;arh=2&amp;w=640&amp;s=aedbf13b14e888beedc139ee68dbe1d5", "width": 640, "height": 270}, {"url": "https://i.redditmedia.com/VqdviP5_R14GRQ1YSVV4oBaNuX_7lBwrhxlPxRtAGrw.jpg?fit=crop&amp;crop=faces%2Centropy&amp;arh=2&amp;w=960&amp;s=f0e7c05d552988295183acacf70c6c01", "width": 960, "height": 405}], "variants": {}, "id": "2CuxKUAzLYIGh1jNwcszBt0Nanjz6wBZcggqVgo55KU"}]}, "thumbnail": "http://b.thumbs.redditmedia.com/swF6-vbvBHGNTfamh2vScWQ5iLwMXcZbbHEr-vbvEWQ.jpg", "subreddit_id": "t5_3fhy1", "edited": false, "link_flair_css_class": null, "author_flair_css_class": null, "downs": 0, "mod_reports": [], "secure_media_embed": {}, "saved": false, "removal_reason": null, "post_hint": "rich:video", "stickied": false, "from": null, "is_self": false, "from_id": null, "permalink": "/r/redditviewertesting/comments/4v8hk9/liveleakcom_test_1/", "locked": false, "hide_score": false, "created": 1469850739.0, "url": "http://www.liveleak.com/view?i=3b5_1469728820", "author_flair_text": null, "quarantine": false, "title": "liveleak.com test 1", "created_utc": 1469821939.0, "ups": 1, "upvote_ratio": 1.0, "num_comments": 4, "visited": false, "num_reports": null, "distinguished": null}}], "after": null, "before": null}}, {"kind": "Listing", "data": {"modhash": "s3jpm9s7w782013e26e5e0682cf496a0741908d7f8c51b8c82", "children": [{"kind": "t1", "data": {"subreddit_id": "t5_3fhy1", "banned_by": null, "removal_reason": null, "link_id": "t3_4v8hk9", "likes": true, "replies": "", "user_reports": [], "saved": false, "id": "d5y0lq8", "gilded": 0, "archived": false, "report_reasons": null, "author": "gsonide", "parent_id": "t3_4v8hk9", "score": 1, "approved_by": null, "controversiality": 0, "body": "comment 1: asdfsdf asdf asdf sadf asdf asdf asdf", "edited": false, "author_flair_css_class": null, "downs": 0, "body_html": "&lt;div class=\"md\"&gt;&lt;p&gt;comment 1: asdfsdf asdf asdf sadf asdf asdf asdf&lt;/p&gt;\n&lt;/div&gt;", "subreddit": "redditviewertesting", "name": "t1_d5y0lq8", "score_hidden": false, "stickied": false, "created": 1469970764.0, "author_flair_text": null, "created_utc": 1469941964.0, "distinguished": null, "mod_reports": [], "num_reports": null, "ups": 1}}, {"kind": "t1", "data": {"subreddit_id": "t5_3fhy1", "banned_by": null, "removal_reason": null, "link_id": "t3_4v8hk9", "likes": true, "replies": {"kind": "Listing", "data": {"modhash": "s3jpm9s7w782013e26e5e0682cf496a0741908d7f8c51b8c82", "children": [{"kind": "t1", "data": {"subreddit_id": "t5_3fhy1", "banned_by": null, "removal_reason": null, "link_id": "t3_4v8hk9", "likes": true, "replies": "", "user_reports": [], "saved": false, "id": "d5y0mh9", "gilded": 0, "archived": false, "report_reasons": null, "author": "gsonide", "parent_id": "t1_d5y0ly6", "score": 1, "approved_by": null, "controversiality": 0, "body": "comment 2-1: gsdfgsdfg  sdfgsdsdf gsdfgkl sdf dsfkglhsdflkj sdlfgjsdl lsdfg sdlfg sdfg sdflg sdfg sdfgljksdhf sdflgksd dflsgj sdflgjk fgsdfg sdfg sdfgsdfgsd mmmmmmm mmmmmmmmmmm mmmmmm asdfh asdlf asld asdf  aslddfkja asdlf asfdjdh asdf j df aasd  aksdjd ks djdhf adfjfaksd mm", "edited": false, "author_flair_css_class": null, "downs": 0, "body_html": "&lt;div class=\"md\"&gt;&lt;p&gt;comment 2-1: gsdfgsdfg  sdfgsdfgsdfg sdfg sdfgsdfgsd&lt;/p&gt;\n&lt;/div&gt;", "subreddit": "redditviewertesting", "name": "t1_d5y0mh9", "score_hidden": false, "stickied": false, "created": 1469970812.0, "author_flair_text": null, "created_utc": 1469942012.0, "distinguished": null, "mod_reports": [], "num_reports": null, "ups": 1}}], "after": null, "before": null}}, "user_reports": [], "saved": false, "id": "d5y0ly6", "gilded": 0, "archived": false, "report_reasons": null, "author": "gsonide", "parent_id": "t3_4v8hk9", "score": 1, "approved_by": null, "controversiality": 0, "body": "comment 2: asdfsdf asdfasdfqwerqw asdf sadfqwer qetsdfg", "edited": false, "author_flair_css_class": null, "downs": 0, "body_html": "&lt;div class=\"md\"&gt;&lt;p&gt;comment 2: asdfsdf asdfasdfqwerqw asdf sadfqwer qetsdfg&lt;/p&gt;\n&lt;/div&gt;", "subreddit": "redditviewertesting", "name": "t1_d5y0ly6", "score_hidden": false, "stickied": false, "created": 1469970779.0, "author_flair_text": null, "created_utc": 1469941979.0, "distinguished": null, "mod_reports": [], "num_reports": null, "ups": 1}}, {"kind": "t1", "data": {"subreddit_id": "t5_3fhy1", "banned_by": null, "removal_reason": null, "link_id": "t3_4v8hk9", "likes": true, "replies": "", "user_reports": [], "saved": false, "id": "d5y0m5f", "gilded": 0, "archived": false, "report_reasons": null, "author": "gsonide", "parent_id": "t3_4v8hk9", "score": 1, "approved_by": null, "controversiality": 0, "body": "comment 3: adfasd asd asdf qwer qwe dsflgkj sdfg", "edited": false, "author_flair_css_class": null, "downs": 0, "body_html": "&lt;div class=\"md\"&gt;&lt;p&gt;comment 3: adfasd asd asdf qwer qwe dsflgkj sdfg&lt;/p&gt;\n&lt;/div&gt;", "subreddit": "redditviewertesting", "name": "t1_d5y0m5f", "score_hidden": false, "stickied": false, "created": 1469970792.0, "author_flair_text": null, "created_utc": 1469941992.0, "distinguished": null, "mod_reports": [], "num_reports": null, "ups": 1}}], "after": null, "before": null}}]'
    
    #log(content)
    #content = json.loads(content.replace('\\"', '\''))  #some error here ?      TypeError: 'NoneType' object is not callable
    content = json.loads(content)
    
    del harvest[:]
    #harvest links in the post text (just 1) 
    r_linkHunter(content[0]['data']['children'])
    
    #the post title is provided in json, we'll just use that instead of messages from addLink()
    try:post_title=content[0]['data']['children'][0]['data']['title']
    except:post_title=''
    #for i, h in enumerate(harvest):
    #    log("aaaaa first harvest "+h[2])

    #harvest links in the post itself    
    r_linkHunter(content[1]['data']['children'])

    comment_score=0
    for i, h in enumerate(harvest):
        #log(str(i)+"  score:"+ str(h[0]).zfill(5)+" "+ h[1] +'|'+ h[3] )
        comment_score=h[0]
        #log("score %d < %d (%s)" %(comment_score,int_CommentTreshold, CommentTreshold) )
        
        
        if comment_score < int_CommentTreshold:
            continue
        
        hoster, DirectoryItem_url, videoID, mode_type, thumb_url,poster_url, isFolder,setInfo_type, property_link_type =make_addon_url_from(h[2])
    
        #mode_type #usually 'playVideo'
        kind=h[6] #reddit uses t1 for user comments and t3 for OP text of the post. like a poster describing the post.  
        d=h[5]   #depth of the comment
        
        tab=" "*d if d>0 else "-"
        
        author=h[7]
        
        if using_custom_gui: #custom gui uses infoLabel->votes to display the comment score, we don't need to prepend it on the title
            if kind=='t1':
                list_title=r"%s" %( tab )
            elif kind=='t3':
                list_title=r"[I]Title [/I] %s" %( tab )
            author=tab + " " +author
        else:
            if kind=='t1':
                list_title=r"[I]%2d pts.[/I] %s" %( h[0], tab )
            elif kind=='t3':
                list_title=r"[I]Title [/I] %s" %( tab )
            
        desc100=h[3].replace('\n',' ')[0:100] #first 100 characters of description

        #helps the the textbox control treat [url description] and (url) as separate words. so that they can be separated into 2 lines 
        plot=h[3].replace('](', '] (')
        plot= markdown_to_bbcode(plot)
        plot=unescape(plot)  #convert html entities e.g.:(&#39;)
        
        if DirectoryItem_url:
            #(score, link_desc, link_http, post_text, post_html, d, )
            #list_item_name=str(h[0]).zfill(3)
            
            #log(str(i)+"  score:"+ str(h[0]).zfill(5)+" desc["+ h[1] +']|text:['+ h[3]+']' +h[2] + '  videoID['+videoID+']' + 'playable:'+ setProperty_IsPlayable )
            #log( h[4] + ' -- videoID['+videoID+']' )
            #log("sss:"+ supportedPluginUrl )
            
            #fl= re.compile('\[(.*?)\]\(.*?\)',re.IGNORECASE) #match '[...](...)' with a capture group inside the []'s as capturegroup1
            #result = fl.sub(r"[B]\1[/B]", h[3])              #replace the match with [B] [/B] with capturegroup1 in the middle of the [B]'s
            
            plot= "[COLOR greenyellow]   *[%s] %s"%(hoster, plot )  + "[/COLOR]"

            liz=xbmcgui.ListItem(label=plot , #not used in gui
                                 label2="",
                                 iconImage="DefaultVideo.png", 
                                 thumbnailImage=thumb_url,
                                 path=DirectoryItem_url)
            if poster_url:
                thumb_url=poster_url
                
            if thumb_url: pass
            else: thumb_url="DefaultVideo.png"
            
            liz.setInfo( type="Video", infoLabels={ "Title": h[1], "plot": plot, "studio": hoster, "votes": str(h[0]), "director": author } )
            liz.setArt({"thumb": thumb_url, "poster":thumb_url, "banner":thumb_url, "fanart":thumb_url, "landscape":thumb_url   })


            liz.setProperty('item_type',property_link_type)   #script or playable
            liz.setProperty('onClick_action', DirectoryItem_url)  #<-- needed by the xml gui skin
            #liz.setPath(DirectoryItem_url) 

            directory_items.append( (DirectoryItem_url, liz, isFolder,) )
            #xbmcplugin.addDirectoryItem(handle=pluginhandle,url=DirectoryItem_url,listitem=liz,isFolder=isFolder)
        else:
            #this section are for comments that have no links or unsupported links
            if not ShowOnlyCommentsWithlink:
                liz=xbmcgui.ListItem(label=list_title + desc100 , 
                                     label2="",
                                     iconImage="", 
                                     thumbnailImage="")
                liz.setInfo( type="Video", infoLabels={ "Title": h[1], "plot": plot, "studio": hoster, "votes": str(h[0]), "director": author } )
                liz.setProperty('IsPlayable', 'false')
                
                directory_items.append( ("", liz, False,) )
                #xbmcplugin.addDirectoryItem(handle=pluginhandle,url="",listitem=liz,isFolder=False)
            
            #END section are for comments that have no links or unsupported links

    #for di in directory_items:
    #    log( str(di) )
    

    if using_custom_gui:   
        from resources.guis import commentsGUI
        
        li=[]
        for di in directory_items:
            #log( str(di[1] ) )
            li.append( di[1] )
            
        ui = commentsGUI('view_461_comments.xml' , addon_path, defaultSkin='Default', defaultRes='1080i', listing=li, id=55)
        #ui = commentsGUI('view_463_comments.xml' , addon_path, defaultSkin='Default', defaultRes='1080i', listing=li, id=55)
        ui.title_bar_text=post_title
        ui.include_parent_directory_entry=False

        ui.doModal()
        del ui

    else:
        #xbmcplugin.setContent(pluginhandle, "mixed")  #in estuary, mixed have limited view id's available. it has widelist which is nice for comments but we'll just stick with 'movies'
        xbmcplugin.setContent(pluginhandle, "movies")    #files, songs, artists, albums, movies, tvshows, episodes, musicvideos 
        xbmcplugin.addDirectoryItems(handle=pluginhandle, items=directory_items )
        xbmcplugin.endOfDirectory(pluginhandle)

        if comments_viewMode:
            xbmc.executebuiltin('Container.SetViewMode(%s)' %comments_viewMode)




harvest=[]
def r_linkHunter(json_node,d=0):
    from resources.domains import url_is_supported
    #recursive function to harvest stuff from the reddit comments json reply
    prog = re.compile('<a href=[\'"]?([^\'" >]+)[\'"]>(.*?)</a>')   
    for e in json_node:
        link_desc=""
        link_http=""
        author=""
        created_utc=""
        if e['kind']=='t1':     #'t1' for comments   'more' for more comments (not supported)
        
            #log("replyid:"+str(d)+" "+e['data']['id'])
            body=e['data']['body'].encode('utf-8')
    
            #log("reply:"+str(d)+" "+body.replace('\n','')[0:80])
            
            try: replies=e['data']['replies']['data']['children']
            except: replies=""
            
            try: score=e['data']['score']
            except: score=0
            
            try: post_text=cleanTitle( e['data']['body'].encode('utf-8') )
            except: post_text=""
            post_text=post_text.replace("\n\n","\n")
            
            try: post_html=cleanTitle( e['data']['body_html'].encode('utf-8') )
            except: post_html=""
    
            try: created_utc=e['data']['created_utc']
            except: created_utc=""
    
            try: author=e['data']['author'].encode('utf-8')
            except: author=""
    
            #i initially tried to search for [link description](https:www.yhotuve.com/...) in the post_text but some posts do not follow this convention
            #prog = re.compile('\[(.*?)\]\((https?:\/\/.*?)\)')   
            #result = prog.findall(post_text)
            
            result = prog.findall(post_html)
            if result:
                #store the post by itself and then a separate one for each link.
                harvest.append((score, link_desc, link_http, post_text, post_html, d, "t1",author,created_utc,)   )
  
                for link_http,link_desc in result:
                    if url_is_supported(link_http) :   
                        #store an entry for every supported link. 
                        harvest.append((score, link_desc, link_http, link_desc, post_html, d, "t1",author,created_utc,)   )    
            else:
                harvest.append((score, link_desc, link_http, post_text, post_html, d, "t1",author,created_utc,)   )    
    
            d+=1 #d tells us how deep is the comment in
            r_linkHunter(replies,d)   
            d-=1         

        if e['kind']=='t3':     #'t3' for post text (a description of the post)
            #log(str(e))
            #log("replyid:"+str(d)+" "+e['data']['id'])
            try: score=e['data']['score']
            except: score=0

            try: self_text=cleanTitle( e['data']['selftext'].encode('utf-8') )
            except: self_text=""
            
            try: self_text_html=cleanTitle( e['data']['selftext_html'].encode('utf-8') )
            except: self_text_html=""

            result = prog.findall(self_text_html)
            if len(result) > 0 :
                harvest.append((score, link_desc, link_http, self_text, self_text_html, d, "t3",author,created_utc, )   )
                 
                for link_http,link_desc in result:
                    if url_is_supported(link_http) : 
                        harvest.append((score, link_desc, link_http, link_desc, self_text_html, d, "t3",author,created_utc, )   )
            else:
                if len(self_text) > 0: #don't post an empty titles
                    harvest.append((score, link_desc, link_http, self_text, self_text_html, d, "t3",author,created_utc,)   )    
            


#MODE listImgurAlbum
def listImgurAlbum(album_url, name, type):
    #log("listImgurAlbum")
    from resources.domains import ClassImgur
    #album_url="http://imgur.com/a/fsjam"
    ci=ClassImgur()
        
    dictlist=ci.ret_album_list(album_url)
    display_album_from(dictlist, name)

def display_album_from(dictlist, album_name):
    from resources.domains import make_addon_url_from
    #this function is called by listImgurAlbum and playTumblr
    #NOTE: the directoryItem calling this needs isFolder=True or you'll get handle -1  error

#works on kodi 16.1 but doesn't load images on kodi 17.

#     ui = ssGUI('tbp_main.xml' , addon_path)
#     items=[]
#     
#     for d in dictlist:
#         #hoster, DirectoryItem_url, videoID, mode_type, thumb_url,poster_url, isFolder,setInfo_type, IsPlayable=make_addon_url_from(d['DirectoryItem_url'],False)
#         items.append({'pic': d['DirectoryItem_url'] ,'description': d['li_label'], 'title' :  d['li_label2'] })
#     
#     ui.items=items
#     ui.album_name=album_name
#     ui.doModal()
#     del ui
#  
#     return
    directory_items=[]
    label=""
    
    using_custom_gui=True
    
    for idx, d in enumerate(dictlist):
        #log('li_label:'+d['li_label'] + "  pluginhandle:"+ str(pluginhandle))
        ti=d['li_thumbnailImage']
        
        if using_custom_gui:
            #There is only 1 textbox for Title and description in our custom gui. 
            #  I don't know how to achieve this in the xml file so it is done here:
            #  combine title and description without [CR] if label is empty. [B]$INFO[Container(53).ListItem.Label][/B][CR]$INFO[Container(53).ListItem.Plot]
            #  new note: this is how it is done: 
            #     $INFO[Container(53).ListItem.Label,[B],[/B][CR]] $INFO[Container(53).ListItem.Plot]  #if the infolabel is empty, nothing is printed for that block
            combined = '[B]'+ d['li_label2'] + "[/B][CR]" if d['li_label2'] else ""
            combined += d['infoLabels'].get('plot')
            d['infoLabels']['plot'] = combined
            #d['infoLabels']['genre'] = "0,-2000"
            #d['infoLabels']['year'] = 1998
            #log( d['infoLabels'].get('plot') ) 
        else:
            #most of the time, the image does not have a title. it looks so lonely on the listitem, we just put a number on it.    
            label = d['li_label2'] if d['li_label2'] else str(idx+1).zfill(2)
            
        
        liz=xbmcgui.ListItem(label=label, 
                             label2=d['li_label2'],
                             iconImage=d['li_iconImage'],
                             thumbnailImage=ti)

        #classImgur puts the media_url into  d['DirectoryItem_url']  no modification.
        #we modify it here...
        #url_for_DirectoryItem = sys.argv[0]+"?url="+ urllib.quote_plus(d['DirectoryItem_url']) +"&mode=playSlideshow"
        hoster, DirectoryItem_url, videoID, mode_type, thumb_url,poster_url, isFolder,setInfo_type, IsPlayable=make_addon_url_from(d['DirectoryItem_url'],False)
        if poster_url=="": poster_url=ti
        
        
        liz.setInfo( type='video', infoLabels= d['infoLabels'] ) #this tricks the skin to show the plot. where we stored the picture descriptions
        liz.setArt({"thumb": ti, "poster":poster_url, "banner":poster_url, "fanart":poster_url, "landscape":d['DirectoryItem_url']   })             


        directory_items.append( (DirectoryItem_url, liz, isFolder,) )

        #xbmcplugin.addDirectoryItem(handle=pluginhandle,url=DirectoryItem_url,listitem=liz)

    if using_custom_gui:
        from resources.guis import cGUI
     
        #msg=WINDOW.getProperty(url)
        #WINDOW.clearProperty( url )
        #log( '   msg=' + msg )
    
        #<label>$INFO[Window(10000).Property(foox)]</label>
        #WINDOW.setProperty('view_450_slideshow_title',WINDOW.getProperty(url))
         
        li=[]
        for di in directory_items:
            #log( str(di[1] ) )
            li.append( di[1] )
             
        #ui = cGUI('FileBrowser.xml' , addon_path, defaultSkin='Default', defaultRes='1080i', listing=li)
        ui = cGUI('view_450_slideshow.xml' , addon_path, defaultSkin='Default', defaultRes='1080i', listing=li, id=53)
        
        ui.include_parent_directory_entry=False
        #ui.title_bar_text=WINDOW.getProperty(url)
        
        ui.doModal()
        del ui
        #WINDOW.clearProperty( 'view_450_slideshow_title' )
        #log( '   WINDOW.getProperty=' + WINDOW.getProperty('foo') )
    else:
        xbmcplugin.setContent(pluginhandle, "episodes")

        log( 'album_viewMode ' + album_viewMode )
        if album_viewMode=='0':
            pass
        else:
            xbmc.executebuiltin('Container.SetViewMode('+album_viewMode+')')
    
        xbmcplugin.addDirectoryItems(handle=pluginhandle, items=directory_items )
        xbmcplugin.endOfDirectory(pluginhandle)

 
def listTumblrAlbum(t_url, name, type):    
    from resources.domains import ClassTumblr
    log("listTumblrAlbum:"+t_url)
    t=ClassTumblr(t_url)
    
    media_url, media_type =t.get_playable_url(t_url, True)
    #log('  ' + str(media_url))
    
    if media_type=='album':
        display_album_from( media_url, name )
    else:
        log("  listTumblrAlbum can't process " + media_type)    


def playVineVideo(vine_url, name, type):
    from resources.domains import ClassVine
    #log('playVineVideo')
    
    v=ClassVine(vine_url)
    #vine_stream_url='https://v.cdn.vine.co/r/videos/38B4A9174D1177703702723739648_37968e655a0.1.5.1461921223578533188.mp4'
    vine_stream_url=v.get_playable_url(vine_url, True)    #instead of querying vine(for the .mp4 link) for each item when listing the directory item(addLink()). we do that query here. better have the delay here than for each item when listing the directory item 
    
    if vine_stream_url:
        playVideo(vine_stream_url, name, type)
    else:
        #media_status=v.whats_wrong()
        xbmc.executebuiltin('XBMC.Notification("Vine","%s")' % 'media_status'  )

    #xbmc.executebuiltin("PlayerControl('repeatOne')")  #how do i make this video play again? 

def playVidmeVideo(vidme_url, name, type):
    from resources.domains import ClassVidme
    log('playVidmeVideo')
    v=ClassVidme(vidme_url)
    vidme_stream_url=v.get_playable_url(vidme_url, True)
    if vidme_stream_url:
        playVideo(vidme_stream_url, name, type)
    else:
        media_status=v.whats_wrong()
        xbmc.executebuiltin('XBMC.Notification("Vidme","%s")' % media_status  )
        
def playStreamable(media_url, name, type):
    from resources.domains import ClassStreamable
    log('playStreamable '+ media_url)
    
    s=ClassStreamable(media_url)
    playable_url=s.get_playable_url(media_url, True)

    if playable_url:
        playVideo(playable_url, name, type)
    else:
        #media_status=s.whats_wrong()  #streamable does not tell us if access to video is denied beforehand
        xbmc.executebuiltin('XBMC.Notification("Streamable","%s")' % "Access Denied"  )
    
def playInstagram(media_url, name, type):
    from resources.domains import ClassInstagram
    log('playInstagram '+ media_url)
    #instagram video handled by ytdl. links that reddit says is image are handled here.
    i=ClassInstagram( media_url )
    image_url=i.get_playable_url(media_url, False)
    
    playSlideshow(image_url,"Instagram","")

#MODE playLiveLeakVideo       - name, type not used
def playLiveLeakVideo(id, name, type):
    playVideo(getLiveLeakStreamUrl(id), name, type)

def playFlickr(flickr_url, name, type):
    from resources.domains import ClassFlickr
    log('play flickr '+ flickr_url)
    f=ClassFlickr( flickr_url )

    try:
        media_url, media_type =f.get_playable_url(flickr_url, False)
        if media_type=='album':
            display_album_from( media_url, name )
        else:
            playSlideshow(media_url,"Flickr","")
            #log("  listTumblrAlbum can't process " + media_type)    
    except Exception as e:
        xbmc.executebuiltin('XBMC.Notification("%s", "%s" )' %( e, 'Flickr' )  )
        

def playImgurVideo(imgur_url, name, type):
    from resources.domains import ClassImgur
    log('play imgur '+ imgur_url)
    f=ClassImgur( imgur_url )

    media_url, media_type =f.get_playable_url(imgur_url, False)
    if media_type=='album':
        display_album_from( media_url, name )
    elif media_type=='video':
        playVideo(media_url, "", "")
    elif media_type=='image':
        playSlideshow(media_url,"Flickr","")
        #log("  listTumblrAlbum can't process " + media_type)    
    
#MODE downloadLiveLeakVideo       - name, type not used
def downloadLiveLeakVideo(id, name, type):
    downloader = SimpleDownloader.SimpleDownloader()
    content = opener.open("http://www.liveleak.com/view?i="+id).read()
    match = re.compile('<title>LiveLeak.com - (.+?)</title>', re.DOTALL).findall(content)
    global ll_downDir
    while not ll_downDir:
        xbmc.executebuiltin('XBMC.Notification(Download:,Liveleak '+translation(30186)+'!,5000)')
        addon.openSettings()
        ll_downDir = addon.getSetting("ll_downDir")
    url = getLiveLeakStreamUrl(id)
    filename = ""
    try:
        filename = (''.join(c for c in unicode(match[0], 'utf-8') if c not in '/\\:?"*|<>')).strip()
    except:
        filename = id
    filename+=".mp4"
    if not os.path.exists(os.path.join(ll_downDir, filename)):
        params = { "url": url, "download_path": ll_downDir }
        downloader.download(filename, params)
    else:
        xbmc.executebuiltin('XBMC.Notification(Download:,'+translation(30185)+'!,5000)')

#MODE queueVideo       -type not used
def queueVideo(url, name, type):
    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    listitem = xbmcgui.ListItem(name)
    playlist.add(url, listitem)

#MODE addToFavs         -name not used
def addToFavs(url, name, subreddit):
    file = os.path.join(addonUserDataFolder, subreddit+".fav")
    if os.path.exists(file):
        fh = open(file, 'r')
        content = fh.read()
        fh.close()
        if url not in content:
            fh = open(file, 'w')
            fh.write(content.replace("</favourites>", "    "+url.replace("\n","<br>")+"\n</favourites>"))
            fh.close()
    else:
        fh = open(file, 'a')
        fh.write("<favourites>\n    "+url.replace("\n","<br>")+"\n</favourites>")
        fh.close()

#MODE removeFromFavs      -name not used
def removeFromFavs(url, name, subreddit):
    file = os.path.join(addonUserDataFolder, subreddit+".fav")
    fh = open(file, 'r')
    content = fh.read()
    fh.close()
    fh = open(file, 'w')
    fh.write(content.replace("    "+url.replace("\n","<br>")+"\n", ""))
    fh.close()
    xbmc.executebuiltin("Container.Refresh")

#searchReddits      --url, name, type not used
def searchReddits(url, name, type):
    keyboard = xbmc.Keyboard('sort=new&t=week&q=', translation(32005))
    keyboard.doModal()
    if keyboard.isConfirmed() and keyboard.getText():  
        
        #search_string = urllib.quote_plus(keyboard.getText().replace(" ", "+"))
        search_string = keyboard.getText().replace(" ", "+")
        
        #sites_filter = site_filter_for_reddit_search()
        url = urlMain +"/search.json?" +search_string    #+ '+' + nsfw  # + sites_filter skip the sites filter

        listSubReddit(url, name, "")
        

def translation(id):
    return addon.getLocalizedString(id).encode('utf-8')

def cleanTitle(title):
        title = title.replace("&lt;","<").replace("&gt;",">").replace("&amp;","&").replace("&#039;","'").replace("&quot;","\"")
        return title.strip()
#MODE openSettings     --name, type not used
def openSettings(id, name,type):
    if id=="youtube":
        addonY = xbmcaddon.Addon(id='plugin.video.youtube')
    elif id=="vimeo":
        addonY = xbmcaddon.Addon(id='plugin.video.vimeo')
    elif id=="dailymotion":
        addonY = xbmcaddon.Addon(id='plugin.video.dailymotion_com')
    addonY.openSettings()
#MODE toggleNSFW     -- url, name, type not uised

def parameters_string_to_dict(parameters):
    paramDict = {}
    if parameters:
        paramPairs = parameters[1:].split("&")
        for paramsPair in paramPairs:
            paramSplits = paramsPair.split('=')
            if (len(paramSplits)) == 2:
                paramDict[paramSplits[0]] = paramSplits[1]
    return paramDict

# def addFavLink(name, url, mode, iconimage, description, date, site, subreddit):
#     ok = True
#     liz = xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
#     liz.setInfo(type="Video", infoLabels={"Title": name, "Plot": description, "Aired": date})
#     liz.setProperty('IsPlayable', 'true')
#     entries = []
#     entries.append((translation(30018), 'RunPlugin(plugin://'+addonID+'/?mode=queueVideo&url='+urllib.quote_plus(url)+'&name='+urllib.quote_plus(name)+')',))
#     favEntry = '<favourite name="'+name+'" url="'+url+'" description="'+description+'" thumb="'+iconimage+'" date="'+date+'" site="'+site+'" />'
#     entries.append((translation(30024), 'RunPlugin(plugin://'+addonID+'/?mode=removeFromFavs&url='+urllib.quote_plus(favEntry)+'&type='+urllib.quote_plus(subreddit)+')',))
#     if showBrowser and (osWin or osOsx or osLinux):
#         if osWin and browser_win==0:
#             entries.append((translation(30021), 'RunPlugin(plugin://plugin.program.webbrowser/?url='+urllib.quote_plus(site)+'&mode=showSite&zoom='+browser_wb_zoom+'&stopPlayback=no&showPopups=no&showScrollbar=no)',))
#         else:
#             entries.append((translation(30021), 'RunPlugin(plugin://plugin.program.chrome.launcher/?url='+urllib.quote_plus(site)+'&mode=showSite)',))
#     liz.addContextMenuItems(entries)
#     ok = xbmcplugin.addDirectoryItem(handle=pluginhandle, url=url, listitem=liz)
#     return ok

#addDir(subreddit, subreddit.lower(), next_mode, "")
def addDir(name, url, mode, iconimage, type="", listitem_infolabel=None, label2=""):
    #adds a list entry
    u = sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&type="+str(type)
    #log('addDir='+u)
    ok = True
    liz = xbmcgui.ListItem(label=name, label2=label2, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
    
    if listitem_infolabel==None:
        liz.setInfo(type="Video", infoLabels={"Title": name})
    else:
        liz.setInfo(type="Video", infoLabels=listitem_infolabel)
        
    
    ok = xbmcplugin.addDirectoryItem(handle=pluginhandle, url=u, listitem=liz, isFolder=True)
    return ok

def compose_list_item(label,label2,iconImage,property_item_type, onClick_action, infolabels=None  ):
    #build a listitem for use in our custom gui
    #if property_item_type=='script':
    #    property_url is the argument for RunAddon()  and it looks like this:   RunAddon( script.web.viewer, http://m.reddit.com/login )
    
    liz=xbmcgui.ListItem(label=label, 
                         label2=label2,
                         iconImage=iconImage, 
                         thumbnailImage=iconImage,
                         path="") #<-- DirectoryItem_url is not used here by the xml gui
    liz.setProperty('item_type', property_item_type)  #item type "script" -> ('RunAddon(%s):' % di_url )
    
        
    #liz.setInfo( type='video', infoLabels={"plot": shortcut_description, } ) 
    liz.setProperty('onClick_action', onClick_action)

    if infolabels==None:
        pass
    else:
        liz.setInfo(type="Video", infoLabels=infolabels)

    return liz

def addDirR(name, url, mode, iconimage, type="", listitem_infolabel=None, file_entry=""):
    #addDir with a remove subreddit context menu
    #alias is the text for the listitem that is presented to the user
    #file_entryis the actual string(containing alias & viewid) that is saved in the "subreddit" file
    
    u = sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&type="+str(type)
    #log('addDirR='+u)
    ok = True
    liz = xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)

    if listitem_infolabel==None:
        #liz.setInfo(type="Video", infoLabels={"Title": name})
        liz.setInfo(type="Video", infoLabels={"Title": name})
    else:
        liz.setInfo(type="Video", infoLabels=listitem_infolabel)
        
    if file_entry:
        liz.setProperty("file_entry", file_entry)
    
    #liz.addContextMenuItems([(translation(30002), 'RunPlugin(plugin://'+addonID+'/?mode=removeSubreddit&url='+urllib.quote_plus(url)+')',)])
    liz.addContextMenuItems([(translation(30003), 'RunPlugin(plugin://'+addonID+'/?mode=editSubreddit&url='+urllib.quote_plus(file_entry)+')',)     ,
                             (translation(30002), 'RunPlugin(plugin://'+addonID+'/?mode=removeSubreddit&url='+urllib.quote_plus(file_entry)+')',)  
                             ])
    
    #log("handle="+sys.argv[1]+" url="+u+" ")
    ok = xbmcplugin.addDirectoryItem(handle=pluginhandle, url=u, listitem=liz, isFolder=True)
    return ok

def pretty_datediff(dt1, dt2):
    try:
        diff = dt1 - dt2
        
        sec_diff = diff.seconds
        day_diff = diff.days
    
        if day_diff < 0:
            return 'future'
    
        if day_diff == 0:
            if sec_diff < 10:
                return translation(30060)     #"just now"
            if sec_diff < 60:
                return str(sec_diff) + translation(30061)      #" secs ago"
            if sec_diff < 120:
                return translation(30062)     #"a min ago"
            if sec_diff < 3600:
                return str(sec_diff / 60) + translation(30063) #" mins ago"
            if sec_diff < 7200:
                return translation(30064)     #"an hour ago"
            if sec_diff < 86400:
                return str(sec_diff / 3600) + translation(30065) #" hrs ago"
        if day_diff == 1:
            return translation(30066)         #"Yesterday"
        if day_diff < 7:
            return str(day_diff) + translation(30067)      #" days ago"
        if day_diff < 31:
            return str(day_diff / 7) + translation(30068)  #" wks ago"
        if day_diff < 365:
            return str(day_diff / 30) + translation(30069) #" months ago"
        return str(day_diff / 365) + translation(30070)    #" years ago"
    except:
        pass




def playSlideshow(url, name, type):
    #url='d:\\aa\\lego_fusion_beach1.jpg'

    from resources.guis import cGUI
    
    #msg=WINDOW.getProperty(url)
    #WINDOW.clearProperty( url )
    #log( '   msg=' + msg )
    msg=""
    li=[]
    liz=xbmcgui.ListItem(label=msg, label2="", iconImage="", thumbnailImage=url)
    liz.setInfo( type='video', infoLabels={"plot": msg, } ) 
    liz.setArt({"thumb": url, "poster":url, "banner":url, "fanart":url, "landscape":url  })             

    li.append(liz)
    ui = cGUI('view_450_slideshow.xml' , addon_path, defaultSkin='Default', defaultRes='1080i', listing=li, id=53)   
    ui.include_parent_directory_entry=False
    
    ui.doModal()
    del ui
    return
    
    
#     from resources.guis import qGUI
#     
#     ui = qGUI('view_image.xml' ,  addon_path, defaultSkin='Default', defaultRes='1080i')   
#     #no need to download the image. kodi does it automatically!!!
#     ui.image_path=url
#     ui.doModal()
#     del ui
#     return
# 
# 
#     #this is a workaround to not being able to show images on video addon
#     log('playSlideshow:'+url +'  ' + name )
# 
#     ui = ssGUI('tbp_main.xml' , addon_path)
#     items=[]
#     
#     items.append({'pic': url ,'description': "", 'title' : name })
#     
#     ui.items=items
#     ui.album_name=""
#     ui.doModal()
#     del ui

    #this will also work:
    #download the image, then view it with view_image.xml.
#     url=url.split('?')[0]
#     
#     filename,ext=parse_filename_and_ext_from_url(url)
#     #empty_slideshow_folder()  # we're showing only 1 file
#     xbmc.executebuiltin('ActivateWindow(busydialog)')
# 
#     os.chdir(SlideshowCacheFolder)
#     download_file= filename+"."+ext
#     if os.path.exists(download_file):
#         log("  file exists")
#     else:
#         log('  downloading %s' %(download_file))
#         downloadurl(url, download_file)
#         log('  downloaded %s' %(download_file))
#     xbmc.executebuiltin('Dialog.Close(busydialog)')
# 
#     ui = qGUI('view_image.xml' , addon_path, 'default')
#     
#     ui.image_path=SlideshowCacheFolder + fd + download_file  #fd = // or \ depending on os
#     ui.doModal()
#     return

    #download_file=download_file.replace(r"\\",r"\\\\")

    #addonUserDataFolder = xbmc.translatePath("special://profile/addon_data/"+addonID)
    #i cannot get this to work reliably...
    #xbmc.executeJSONRPC('{"jsonrpc":"2.0","id":"1","method":"Player.Open","params":{"item":{"directory":"%s"}}}' %(addonUserDataFolder) )
    #xbmc.executeJSONRPC('{"jsonrpc":"2.0","id":"1","method":"Player.Open","params":{"item":{"directory":"%s"}}}' %(r"d:\\aa\\") )
    #xbmc.executeJSONRPC('{"jsonrpc":"2.0","id":"1","method":"Player.Open","params":{"item":{"file":"%s"}}}' %(download_file) )
    #return

    #whis won't work if addon is a video add-on
    #xbmc.executebuiltin("XBMC.SlideShow(" + SlideshowCacheFolder + ")")

    return

'''
def empty_slideshow_folder():
    for the_file in os.listdir(SlideshowCacheFolder):
        file_path = os.path.join(SlideshowCacheFolder, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
                #log("deleting:"+file_path)
            #elif os.path.isdir(file_path): shutil.rmtree(file_path)
        except Exception as e:
            log("empty_slideshow_folder error:"+e)    
'''

def zoom_n_slide(image, width, height):
    #url=image, name=width, type=height
    log( 'zoom_n_slide %s: %s,%s' %(image, width, height))
    
    try:
        w=int(width)
        h=int(height)
        zoom,slide=calculate_zoom_slide(w,h)

        newWindow=xbmcgui.Window()
        newWindow.setCoordinateResolution(0)
        #ctl3=xbmcgui.ControlImage(0, 0, 1920, 1080, 'http://i.imgur.com/E0qPa3D.jpg', aspectRatio=2)
        ctl3=xbmcgui.ControlImage(0, 0, 1920, 1080, image, aspectRatio=2)
        newWindow.addControl(ctl3)

        scroll_time=int(height)*(int(height)/int(width))
        
        zoom_effect="effect=zoom loop=true center=960 end=%d time=1000" %zoom
        fade_effect="condition=true effect=slide delay=1000 start=0,0 end=0,-%d time=%d pulse=true" %(slide,scroll_time)
        
        ctl3.setAnimations([('WindowOpen', zoom_effect), ('conditional', fade_effect,) ])
        
        #newWindow.show()
        #xbmc.sleep(8000)
        newWindow.doModal()
        del newWindow
    except Exception as e:
        log("  EXCEPTION zoom_n_slide:="+ str( sys.exc_info()[0]) + "  " + str(e) )    
    

def molest_xml(url, name, type):
    #from resources.guis import cGUI
    log( 'molest_xml %s-%s-%s' %(url, name, type))
    #li=[]

    CurrentWindow = xbmcgui.Window( xbmcgui.getCurrentWindowId() )
    #log( '  cwi:'+ str(CurrentWindow) )
    
    try:
        ctl=CurrentWindow.getControl(65591)
        log( 'setting visible' )
        ctl.setVisible(True)
        xbmc.sleep(5)
        #win.addControl()
        
        ctl2=CurrentWindow.getControl(201)
        #CurrentWindow.removeControl(ctl2)
        #aa=ctl2.getProperty('width')
        #log("  aa"+str(aa))
        
        #doesn't work
        #ctl2.setImage('d:\\test.png')
        #CurrentWindow.show()
        
        #works
        #ctl3=xbmcgui.ControlLabel(200,200,100,50, "labellasdas", "font14")
        #ctl3=xbmcgui.ControlImage(1200, 200, 500, 500, 'http://target.scene7.com/is/image/Target/15773403', aspectRatio=0)
        #CurrentWindow.addControl(ctl3)
        
        
        
        
        
        
        #read later:  Is it possible set animation windowopen via script ?      http://forum.kodi.tv/showthread.php?tid=210316
        
        
        #ctl3.setAnimations([ ('WindowOpen', 'effect=zoom center=960 time=2000') , ('conditional', 'condition=true effect=slide delay=2000 start=10,10 end=1280,10 time=5000 loop=true',) ] )
        #ctl3.setAnimations([ ('conditional','condition=true effect=slide delay=2000 start=10,10 end=10,510 time=5000 loop=true')  ] )
        #ctl3.setAnimations([('conditional', 'condition=true effect=slide pulse=true delay=1000 start=10,10 end=1280,10 time=2000',)])
        
        #ctl3.setAnimations([('conditional', 'condition=true pulse=True effect=zoom end=150 time=2000'), ('conditional', 'condition=true effect=slide delay=2000 start=10,10 end=1280,10 time=5000 loop=true') ])
        
        
    except Exception as e:
        log("  EXCEPTION:="+ str( sys.exc_info()[0]) + "  " + str(e) )    
        
        
    #ui = cGUI('view_461_comments.xml' , addon_path, defaultSkin='Default', defaultRes='1080i', listing=li)
    #ui.addItems(li )
    
    #ui.doModal()
    #del ui
    
    pass

def calculate_zoom_slide(img_w, img_h):
    screen_w = 1920
    screen_h = 1080
    
    startx=0
    
    #determine how much xbmc would shrink the image to fit screen
    
    shrink_percent = float(screen_h) / img_h
    slide_end = float(img_h-screen_h) * shrink_percent

    log("  shrink_percentage %f " %(shrink_percent) )

    if img_w > screen_w:
        #startx=0

        #*** calc here needs adjustment
                
        #get the shrunked image width 
        s_w=img_w*shrink_percent

        #zoom percent needed to make the shrunked_img_w same as screen_w        
        zoom_percent = (float(screen_w) / s_w) - shrink_percent 
        log("  percent 2 zoom  %f " %(zoom_percent) )
        
        #shrunken img height is same as screen_h 
        s_h=img_h*shrink_percent  #==screen_h
        
        #compute not-so-original image height 
        nso_h=s_h* zoom_percent 
        log("  img h  %f " %(nso_h) )
        
        slide_end = float(nso_h-screen_h) * 1/zoom_percent   #shrink_percent
    else: 
        #startx= (screen_w-img_w) / 2

        #zoom this much to get original size
        zoom_percent = float(1) / shrink_percent
        log("  percent to zoom  %f " %(zoom_percent) )

    return zoom_percent * 100, slide_end


def send_email(recipient, Message):
    import smtplib
    from email.mime.text import MIMEText
    import xbmcaddon
    import time
    
    thyme = time.time()
    
    recipient = 'gedisony@gmail.com'
    
    body = '<table border="1">'
    body += '<tr><td>%s</td></tr>' % "I'm using the addon!"
    body += '</table>'
    
    msg = MIMEText(body, 'html')
    msg['Subject'] = 'LazyTV +1  %s' % thyme
    msg['From'] = 'gemalphin@gmail.com'
    msg['To'] = recipient
    msg['X-Mailer'] = 'LazyTV Shout Out %s' % thyme
    
    smtp = smtplib.SMTP('alt4.gmail-smtp-in.l.google.com')
    smtp.sendmail(msg['From'], msg['To'], msg.as_string(9))
    smtp.quit()
    
def callwebviewer(url, name, type):
    log( " callwebviewer")

    #this is how you call the webviewer addon. 
    #u="script.web.viewer, http://m.reddit.com/login"
    #xbmc.executebuiltin('RunAddon(%s)' %u )
    
    import resources.pyxbmct as pyxbmct

    # Create a window instance.
    window = pyxbmct.AddonFullWindow('Hello, World!')
    # Set the window width, height and the grid resolution: 2 rows, 3 columns.
    window.setGeometry(1920, 1080, 9, 16)
    
    #image is 1200x2220
    image=pyxbmct.Image('http://i.imgur.com/lYdRVRi.png', aspectRatio=2)
    
    window.placeControl(image, 0, 0, 9, 16 )
    
    #doesn't work. leaving it alone for now (7/27/2016)
    image.setAnimations([('WindowOpen', 'effect type="zoom" end="150" center="0" time="1800"')])
    
    #image.setAnimations([('WindowOpen', 'effect type="zoom" end="150" center="0" time="1800"',), 
    #                     ('WindowOpen', 'effect type="slide" end="2220"  delay="1800" time="1800"',)])

    
    # Connect a key action to a function.
    window.connect(pyxbmct.ACTION_NAV_BACK, window.close)
    # Show the created window.
    window.doModal()
    # Delete the window instance when it is no longer used.
    del window 

    log( " done callwebviewer")

def test_menu(url, name, type):
    log( "  test_menu")

    
    liz = xbmcgui.ListItem("open webviewer", label2="", iconImage="DefaultFolder.png", thumbnailImage="", path="")
    u=sys.argv[0]+"?mode=callwebviewer&type="

    xbmcplugin.addDirectoryItem(handle=pluginhandle, url=u, listitem=liz, isFolder=False)
    
    
    addDir("2login", sys.argv[0], "reddit_login", "" )
    addDir("3login", sys.argv[0], "reddit_login", "" )
    xbmcplugin.endOfDirectory(pluginhandle)

#     from resources.httpd import TinyWebServer
#       
#     log( "*******************starting httpd")
#     httpd = TinyWebServer('xyz')
#     httpd.create("localhost", 8090)
#     httpd.start()
#       
#     xbmc.sleep(30000)
#       
#     log( "*******************stopping httpd")    
#     httpd.stop()



def reddit_request( url ):
    #log( "  reddit_request " + url )
    
    #if there is a refresh_token, we use oauth.reddit.com instead of www.reddit.com
    if reddit_refresh_token:
        url=url.replace('www.reddit.com','oauth.reddit.com' )
        log( "  replaced reqst." + url + " + access token=" + reddit_access_token)
        
    req = urllib2.Request(url)

    #req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.8.1.14) Gecko/20080404 Firefox/2.0.0.14')
    req.add_header('User-Agent', userAgent)   #userAgent = "XBMC:"+addonID+":v"+addon.getAddonInfo('version')+" (by /u/gsonide)"
    
    #if there is a refresh_token, add the access token to the header
    if reddit_refresh_token:
        req.add_header('Authorization','bearer '+ reddit_access_token )
    
    try:
        page = urllib2.urlopen(req)
        response=page.read();page.close()
        #log( response )
        return response

    except urllib2.HTTPError, err:
        if err.code in [403,401]:  #401 Unauthorized, 403 forbidden. access tokens expire in 1 hour. maybe we just need to refresh it
            log("    attempting to get new access token")
            if reddit_get_access_token():
                log("      Success: new access token "+ reddit_access_token)
                req.add_header('Authorization','bearer '+ reddit_access_token )
                try:
                    
                    log("      2nd attempt:"+ url)
                    page = urllib2.urlopen(req)   #it has to be https:// not http://
                    response=page.read();page.close()
                    return response
                
                except urllib2.HTTPError, err:
                    xbmc.executebuiltin('XBMC.Notification("%s %s", "%s" )' %( err.code, err.msg, url)  )
                    log( err.reason )         
                except urllib2.URLError, err:
                    log( err.reason ) 
            else:
                log( "*** failed to get new access token - don't know what to do " )

            
        xbmc.executebuiltin('XBMC.Notification("%s %s", "%s" )' %( err.code, err.msg, url)  )
        log( err.reason )         
    except urllib2.URLError, err: # Not an HTTP-specific error (e.g. connection refused)
        xbmc.executebuiltin('XBMC.Notification("%s %s", "%s" )' %( err.code, err.msg, url)  )
        log( err.reason ) 
    
        
def reddit_get_refresh_token(url, name, type):
    #this function gets a refresh_token from reddit and keep it in our addon. this refresh_token is used to get 1-hour access tokens.
    #  getting a refresh_token is a one-time step
    
    #1st: use any webbrowser to  
    #  https://www.reddit.com/api/v1/authorize?client_id=hXEx62LGqxLj8w&response_type=code&state=RS&redirect_uri=http://localhost:8090/&duration=permanent&scope=read,mysubreddits
    #2nd: click allow and copy the code provided after reddit redirects the user 
    #  save this code in add-on settings.  A one-time use code that may be exchanged for a bearer token.
    code = addon.getSetting("reddit_code")
    #log("  user refresh token:"+reddit_refresh_token)
    #log("  user          code:"+code)
    
    if reddit_refresh_token and code:
        #log("  user already have refresh token:"+reddit_refresh_token)
        dialog = xbmcgui.Dialog()
        if dialog.yesno(translation(32411), translation(32412), translation(32413), translation(32414) ):
            pass
        else:
            return
        
    try:
        log( "Requesting a reddit permanent token with code=" + code )
 
        req = urllib2.Request('https://www.reddit.com/api/v1/access_token')
         
        #http://stackoverflow.com/questions/6348499/making-a-post-call-instead-of-get-using-urllib2
        data = urllib.urlencode({'grant_type'  : 'authorization_code'
                                ,'code'        : code                     #'woX9CDSuw7XBg1MiDUnTXXQd0e4'
                                ,'redirect_uri': reddit_redirect_uri})    #http://localhost:8090/
 
        #http://stackoverflow.com/questions/2407126/python-urllib2-basic-auth-problem
        import base64
        base64string = base64.encodestring('%s:%s' % (reddit_clientID, '')).replace('\n', '')  
        req.add_header('Authorization',"Basic %s" % base64string)
        req.add_header('User-Agent', userAgent)
         
        page = urllib2.urlopen(req, data=data)
        response=page.read();page.close()
        log( response )

        #response='{"access_token": "xmOMpbJc9RWqjPS46FPcgyD_CKc", "token_type": "bearer", "expires_in": 3600, "refresh_token": "56706164-ZZiEqtAhahg9BkpINvrBPQJhZL4", "scope": "identity read"}'
        status=reddit_set_addon_setting_from_response(response)
        
        if status=='ok':
            r1="Click 'OK' when done"
            r2="Settings will not be saved"
            xbmc.executebuiltin("XBMC.Notification(%s, %s)"  %( r1, r2)  )
        else:
            r2="Requesting a reddit permanent token"
            xbmc.executebuiltin("XBMC.Notification(%s, %s)"  %( status, r2)  )     
            

#    This is a 2nd option reddit oauth. user needs to request access token every hour
#         #user enters this on their webbrowser. note that there is no duration=permanent response_type=token instead of code 
#         request_url='https://www.reddit.com/api/v1/authorize?client_id=hXEx62LGqxLj8w&response_type=token&state=RS&redirect_uri=http://localhost:8090/&scope=read,identity'
#         #click on "Allow"
#         #copy the redirect url code    #enters it on settings. e.g.: LVQu8vitbEXfMPcK1sGlVVQZEpM
# 
#         #u='https://oauth.reddit.com/new.json'
#         u='https://oauth.reddit.com//api/v1/me.json'
# 
#         req = urllib2.Request(u)
#         #req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.8.1.14) Gecko/20080404 Firefox/2.0.0.14')
#         req.add_header('User-Agent', userAgent)
#         req.add_header('Authorization','bearer LVQu8vitbEXfMPcK1sGlVVQZEpM')
#         page = read,identity.urlopen(req)
#         response=page.read();page.close()
    
    except urllib2.HTTPError, err:
        xbmc.executebuiltin('XBMC.Notification("%s %s", "%s" )' %( err.code, err.msg, u)  )
        log( err.reason )         
    except urllib2.URLError, err: # Not an HTTP-specific error (e.g. connection refused)
        log( err.reason ) 
    
def reddit_get_access_token(url="", name="", type=""):
    try:
        log( "Requesting a reddit 1-hour token" )
 
        req = urllib2.Request('https://www.reddit.com/api/v1/access_token')
          
        #http://stackoverflow.com/questions/6348499/making-a-post-call-instead-of-get-using-urllib2
        data = urllib.urlencode({'grant_type'    : 'refresh_token'
                                ,'refresh_token' : reddit_refresh_token })                    #'woX9CDSuw7XBg1MiDUnTXXQd0e4'
  
        #http://stackoverflow.com/questions/2407126/python-urllib2-basic-auth-problem
        import base64
        base64string = base64.encodestring('%s:%s' % (reddit_clientID, '')).replace('\n', '')  
        req.add_header('Authorization',"Basic %s" % base64string)
        req.add_header('User-Agent', userAgent)
          
        page = urllib2.urlopen(req, data=data)
        response=page.read();page.close()
        #log( response )

        #response='{"access_token": "lZN8p1QABSr7iJlfPjIW0-4vBLM", "token_type": "bearer", "device_id": "None", "expires_in": 3600, "scope": "identity read"}'
        status=reddit_set_addon_setting_from_response(response)
        
        if status=='ok':
            #log( '    ok new access token '+ reddit_access_token )
            #r1="Click 'OK' when done"
            #r2="Settings will not be saved"
            #xbmc.executebuiltin("XBMC.Notification(%s, %s)"  %( r1, r2)  )
            return True
        else:
            r2="Requesting 1-hour token"
            xbmc.executebuiltin("XBMC.Notification(%s, %s)"  %( status, r2)  )     
    
    except urllib2.HTTPError, err:
        xbmc.executebuiltin('XBMC.Notification("%s %s", "%s" )' %( err.code, err.msg, req.get_full_url())  )
        log( err.reason )         
    except urllib2.URLError, err: # Not an HTTP-specific error (e.g. connection refused)
        log( err.reason )
    
    return False 

def reddit_set_addon_setting_from_response(response):
    global reddit_access_token    #specify "global" if you wanto to change the value of a global variable
    global reddit_refresh_token
    try:
        response = json.loads(response.replace('\\"', '\''))
        log( json.dumps(response, indent=4) )
        
        if 'error' in response:
            #Error                      Cause                                                                Resolution
            #401 response               Client credentials sent as HTTP Basic Authorization were invalid     Verify that you are properly sending HTTP Basic Authorization headers and that your credentials are correct
            #unsupported_grant_type     grant_type parameter was invalid or Http Content type was not set correctly     Verify that the grant_type sent is supported and make sure the content type of the http message is set to application/x-www-form-urlencoded
            #NO_TEXT for field code     You didn't include the code parameter                                Include the code parameter in the POST data
            #invalid_grant              The code has expired or already been used                            Ensure that you are not attempting to re-use old codes - they are one time use.            
            return response['error'] 
        else:
            if 'refresh_token' in response:  #refresh_token only returned when getting reddit_get_refresh_token. it is a one-time step
                reddit_refresh_token = response['refresh_token']
                addon.setSetting('reddit_refresh_token', reddit_refresh_token)
            
            reddit_access_token = response['access_token']
            addon.setSetting('reddit_access_token', reddit_access_token)
            #log( '    new access token '+ reddit_access_token )
            
            addon.setSetting('reddit_access_token_scope', response['scope'])
            
            unix_time_now = int(time.time())
            unix_time_now += int( response['expires_in'] )
            addon.setSetting('reddit_access_token_expires', convert_date(unix_time_now))
            
    except Exception as e:
        log("  parsing reddit token response EXCEPTION:="+ str( sys.exc_info()[0]) + "  " + str(e) )    
        return str(e)
    
    return "ok"

def reddit_revoke_refresh_token(url, name, type):    
    global reddit_access_token    #specify "global" if you wanto to change the value of a global variable
    global reddit_refresh_token
    try:
        log( "Revoking refresh token " )
 
        req = urllib2.Request('https://www.reddit.com/api/v1/revoke_token')
          
        data = urllib.urlencode({'token'          : reddit_refresh_token
                                ,'token_type_hint': 'refresh_token'       }) 
  
        import base64
        base64string = base64.encodestring('%s:%s' % (reddit_clientID, '')).replace('\n', '')  
        req.add_header('Authorization',"Basic %s" % base64string)
        req.add_header('User-Agent', userAgent)
          
        page = urllib2.urlopen(req, data=data)
        response=page.read();page.close()
        
        #no response for success. 
        log( "response:" + response )

        #response = json.loads(response.replace('\\"', '\''))
        #log( json.dumps(response, indent=4) )

        addon.setSetting('reddit_refresh_token', "")
        addon.setSetting('reddit_access_token', "")
        addon.setSetting('reddit_access_token_scope', "")
        addon.setSetting('reddit_access_token_expires', "")
        reddit_refresh_token=""
        reddit_access_token=""
        
        r2="Revoking refresh token"
        xbmc.executebuiltin("XBMC.Notification(%s, %s)"  %( 'Token revoked', r2)  )
    
    except urllib2.HTTPError, err:
        xbmc.executebuiltin('XBMC.Notification("%s %s", "%s" )' %( err.code, err.msg, req.get_full_url() )  )
        log( "http error:" + err.reason )         
    except Exception as e:
        xbmc.executebuiltin('XBMC.Notification("%s", "%s" )' %( str(e), 'Revoking refresh token' )  )
        log("  Revoking refresh token EXCEPTION:="+ str( sys.exc_info()[0]) + "  " + str(e) )    
    

import re, htmlentitydefs

## http://effbot.org/zone/re-sub.htm#unescape-html
# Removes HTML or XML character references and entities from a text string.
#
# @param text The HTML (or XML) source text.
# @return The plain text, as a Unicode string, if necessary.

def unescape(text):
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, text)

def markdown_to_bbcode(s):
    #https://gist.github.com/sma/1513929
    links = {}
    codes = []
    try:
        #def gather_link(m):
        #    links[m.group(1)]=m.group(2); return ""
        #def replace_link(m):
        #    return "[url=%s]%s[/url]" % (links[m.group(2) or m.group(1)], m.group(1))
        #def gather_code(m):
        #    codes.append(m.group(3)); return "[code=%d]" % len(codes)
        #def replace_code(m):
        #    return "%s" % codes[int(m.group(1)) - 1]
        
        def translate(p="%s", g=1):
            def inline(m):
                s = m.group(g)
                #s = re.sub(r"(`+)(\s*)(.*?)\2\1", gather_code, s)
                #s = re.sub(r"\[(.*?)\]\[(.*?)\]", replace_link, s)
                #s = re.sub(r"\[(.*?)\]\((.*?)\)", "[url=\\2]\\1[/url]", s)
                #s = re.sub(r"<(https?:\S+)>", "[url=\\1]\\1[/url]", s)
                s = re.sub(r"\B([*_]{2})\b(.+?)\1\B", "[B]\\2[/B]", s)
                s = re.sub(r"\B([*_])\b(.+?)\1\B", "[I]\\2[/I]", s)
                return p % s
            return inline
        
        #s = re.sub(r"(?m)^\[(.*?)]:\s*(\S+).*$", gather_link, s)
        #s = re.sub(r"(?m)^    (.*)$", "~[code]\\1[/code]", s)
        #s = re.sub(r"(?m)^(\S.*)\n=+\s*$", translate("~[size=200][b]%s[/b][/size]"), s)
        #s = re.sub(r"(?m)^(\S.*)\n-+\s*$", translate("~[size=100][b]%s[/b][/size]"), s)
        s = re.sub(r"(?m)^#{4,6}\s*(.*?)\s*#*$", translate("[LIGHT]%s[/LIGHT]"), s)       #heading4-6 becomed light
        s = re.sub(r"(?m)^#{1,3}\s*(.*?)\s*#*$", translate("[B]%s[/B]"), s)               #heading1-3 becomes bold
        #s = re.sub(r"(?m)^##\s+(.*?)\s*#*$", translate("[B]%s[/B]"), s)
        #s = re.sub(r"(?m)^###\s+(.*?)\s*#*$", translate("[B]%s[/B]"), s)
    
        s = re.sub(r"(?m)^>\s*(.*)$", translate("|%s"), s)                                #quotes  get pipe character beginning
        #s = re.sub(r"(?m)^[-+*]\s+(.*)$", translate("~[list]\n[*]%s\n[/list]"), s)
        #s = re.sub(r"(?m)^\d+\.\s+(.*)$", translate("~[list=1]\n[*]%s\n[/list]"), s)
        s = re.sub(r"(?m)^((?!~).*)$", translate(), s)
        #s = re.sub(r"(?m)^~\[", "[", s)
        #s = re.sub(r"\[/code]\n\[code(=.*?)?]", "\n", s)
        #s = re.sub(r"\[/quote]\n\[quote]", "\n", s)
        #s = re.sub(r"\[/list]\n\[list(=1)?]\n", "", s)
        #s = re.sub(r"(?m)\[code=(\d+)]", replace_code, s)
        
        return s
    except:
        return s
    
DATEFORMAT = xbmc.getRegion('dateshort')
TIMEFORMAT = xbmc.getRegion('meridiem')

def convert_date(stamp):
    #http://forum.kodi.tv/showthread.php?tid=221119
    date_time = time.localtime(stamp)
    if DATEFORMAT[1] == 'd':
        localdate = time.strftime('%d-%m-%Y', date_time)
    elif DATEFORMAT[1] == 'm':
        localdate = time.strftime('%m-%d-%Y', date_time)
    else:
        localdate = time.strftime('%Y-%m-%d', date_time)
    if TIMEFORMAT != '/':
        localtime = time.strftime('%I:%M%p', date_time)
    else:
        localtime = time.strftime('%H:%M', date_time)
    return localtime + '  ' + localdate

    
def downloadurl( source_url, destination=""):
    try:
        filename,ext=parse_filename_and_ext_from_url(source_url)
        if destination=="":
            urllib.urlretrieve(source_url, filename+"."+ext)
        else:
            urllib.urlretrieve(source_url, destination)
        
    except:
        log("download ["+source_url+"] failed")

def log(message, level=xbmc.LOGNOTICE):
    xbmc.log("reddit_viewer:"+message, level=level)


if __name__ == '__main__':
    dbPath = getDbPath()
    if dbPath:
        conn = sqlite3.connect(dbPath)
        c = conn.cursor()

    if len(sys.argv) > 1: 
        params=parameters_string_to_dict(sys.argv[1])
        log("sys.argv[1]="+sys.argv[1]+"  ")        
    else: params={}

    mode   = urllib.unquote_plus(params.get('mode', ''))
    url    = urllib.unquote_plus(params.get('url', ''))
    typez  = urllib.unquote_plus(params.get('type', '')) #type is a python function, try not to use a variable name same as function
    name   = urllib.unquote_plus(params.get('name', ''))
    #xbmc supplies this additional parameter if our <provides> in addon.xml has more than one entry e.g.: <provides>video image</provides>
    #xbmc only does when the add-on is started. we have to pass it along on subsequent calls   
    # if our plugin is called as a pictures add-on, value is 'image'. 'video' for video 
    #content_type=urllib.unquote_plus(params.get('content_type', ''))   
    #ctp = "&content_type="+content_type   #for the lazy
    #log("content_type:"+content_type)
    
    if HideImagePostsOnVideo: # and content_type=='video':
        setting_hide_images=True
    #log("HideImagePostsOnVideo:"+str(HideImagePostsOnVideo)+"  setting_hide_images:"+str(setting_hide_images))
    #log("params="+sys.argv[1]+"  ")
#     log("----------------------")
#     log("params="+ str(params))
#     log("mode="+ mode)
#     log("type="+ typez) 
#     log("name="+ name)
#     log("url="+  url)
#     log("pluginhandle:" + str(pluginhandle) )
#     log("-----------------------")
    
    if mode=='':mode='index'  #default mode is to list start page (index)
    #plugin_modes holds the mode string and the function that will be called given the mode
    plugin_modes = {'index'                 : index
                    ,'listSubReddit'        : listSubReddit
                    ,'playVideo'            : playVideo           
                    ,'playLiveLeakVideo'    : playLiveLeakVideo  
                    ,'playGfycatVideo'      : playGfycatVideo   
                    ,'downloadLiveLeakVideo': downloadLiveLeakVideo
                    ,'addSubreddit'         : addSubreddit         
                    ,'editSubreddit'        : editSubreddit         
                    ,'removeSubreddit'      : removeSubreddit      
                    ,'autoPlay'             : autoPlay       
                    ,'queueVideo'           : queueVideo     
                    ,'addToFavs'            : addToFavs      
                    ,'removeFromFavs'       : removeFromFavs
                    ,'searchReddits'        : searchReddits          
                    ,'openSettings'         : openSettings        
                    ,'listImgurAlbum'       : listImgurAlbum
                    ,'playImgurVideo'       : playImgurVideo  
                    ,'playSlideshow'        : playSlideshow
                    ,'listLinksInComment'   : listLinksInComment
                    ,'playVineVideo'        : playVineVideo
                    ,'playYTDLVideo'        : playYTDLVideo
                    ,'playVidmeVideo'       : playVidmeVideo
                    ,'listTumblrAlbum'      : listTumblrAlbum
                    ,'playStreamable'       : playStreamable
                    ,'playInstagram'        : playInstagram
                    ,'playFlickr'           : playFlickr
                    ,'listFlickrAlbum'      : playFlickr 
                    ,'molest_xml'           : molest_xml    #for testing 
                    ,'zoom_n_slide'         : zoom_n_slide
                    ,'test_menu'            : test_menu 
                    ,'manage_subreddits'    : manage_subreddits
                    ,'callwebviewer'        : callwebviewer
                    ,'get_refresh_token'    : reddit_get_refresh_token
                    ,'get_access_token'     : reddit_get_access_token
                    ,'revoke_refresh_token' : reddit_revoke_refresh_token
                    }
    
    #'playYTDLVideo','listLinksInComment' takes a long time to complete. when these modes are called from the gui, a long xbmc.executebuiltin("ActivateWindow(busydialog)") is run
    #   we close the busy dialog if running other modes 
    #if not mode in ['playYTDLVideo','listLinksInComment']:
    #    xbmc.executebuiltin( "Dialog.Close(busydialog)" )
    
    #whenever a list item is clicked, this part handles it.
    plugin_modes[mode](url,name,typez)

#    usually this plugin is called by a list item constructed like the one below
#         u = sys.argv[0]+"?url=&mode=addSubreddit&type="   #these are the arguments that is sent to our plugin and processed by plugin_modes
#         liz = xbmcgui.ListItem("Add Subreddit",label2="aaa", iconImage="DefaultFolder.png", thumbnailImage="")
#         liz.setInfo(type="Video", infoLabels={"Title": "aaaaaaa", "Plot": "description", "Aired": "daate", "mpaa": "aa"})
#         xbmcplugin.addDirectoryItem(handle=pluginhandle, url=u, listitem=liz, isFolder=True)



'''
github notes:  (6-27-2016)

# Clone your fork of kodi's repo into the current directory in terminal
git clone git@github.com:gedisony/repo-plugins.git repo-plugins

# Navigate to the newly cloned directory
cd repo-plugins

# Assign the original repo to a remote called "upstream"
git remote add upstream https://github.com/xbmc/repo-plugins.git

#
git checkout jarvis


If you cloned a while ago, get the latest changes from upstream:

# Fetch upstream changes
git fetch upstream
# Make sure you are on your 'master' branch
git checkout master
# Merge upstream changes
git merge upstream/master

'master' is only used as example here. Please replace it with the correct branch you want to submit your add-on towards.
*** i think you need to use 'origin/jarvis' instead of 'master'



#Create a new branch to contain your new add-on or subsequent update:
git checkout -b <add-on-branch-name>                       <------while testing, i ended up naming the branch name as "add-on-branch-name"
#The branch name isn't really relevant however a good suggestion is to name it like the addon ID.


#Commit your changes in a single commit, or your pull request is unlikely to be merged into the main repository.
#Use git's interactive rebase feature to tidy up your commits before making them public. The commit for your add-on should have the following naming convention as the following example:
*** don't know what it means "single commit" (how to commit?) 
*** go to repo-plugins and copy the entire folder plugin.video.reddit_viewer-master
*** remove the "-master"  --> plugin.video.reddit_viewer
*** 
*** this is what i did:
$ git commit -m "[plugin.video.reddit_viewer] 2.7.1"
On branch add-on-branch-name
Untracked files:
        plugin.video.reddit_viewer/                <------ error message

nothing added to commit but untracked files present

edipc@DESKTOP-5C55U1P MINGW64 ~/kodi stuff/repo-plugins (add-on-branch-name)
$ git add .    <---- did this to fix the error.

$ git commit -m "[plugin.video.reddit_viewer] 2.7.1"  <------- this will now work


#Push your topic branch up to your fork:

git push origin add-on-branch-name

#Open a pull request with a clear title and description.

*** on browser: click on pull request
upper left : base fork: xbmc/repo-plugins         base:    jarvis
upper right: head fork: gedisony/repo-plugins     compare: add-on-branch-name
*** the clear title till be [plugin.video.reddit_viewer] 2.7.1
*** (don't know what description) left it as blank

*** sent pull request on 6/27/2016

'''
'''
new github notes (7/1/2016) special thanks to Skipmode A1  http://forum.kodi.tv/showthread.php?tid=280882&pid=2365444#pid2365444

rem For a total restart: Delete repo-plugins from your repo on Github
rem For a total restart: Fork the official kodi repo to your repo on Github
rem Deleting C:\Kodi_stuff\repo-plugins and Cloning the kodi repo from your github to your pc
rem Ctrl-C to abort!!!!
pause
rmdir /s /q C:\Kodi_stuff\repo-plugins
cd C:\Kodi_stuff\
c:
rem Cloning the kodi repo from your github to your pc
git clone git@github.com:gedisony/repo-plugins.git repo-plugins
cd C:\Kodi_stuff\repo-plugins

rem Assign the official kodi repo to a remote called "upstream"
git remote add upstream https://github.com/xbmc/repo-plugins.git

rem Add the addon in your github as a remote
git remote add plugin.video.reddit_viewer git@github.com:gedisony/plugin.video.reddit_viewer

rem Fetch your addon from your github
git fetch plugin.video.reddit_viewer

rem Make a branch for your addon and go to that branch
git checkout -b branch_2.7.2 plugin.video.reddit_viewer/master

rem go to the jarvis branch
git checkout jarvis

rem delete the old version of the addon
git rm .\%1\ -r

rem get the new version of the addon from the branch you created
git read-tree --prefix=plugin.video.reddit_viewer/ -u branch_2.7.2

rem force remove .git files (not used for me)
git rm -f C:\Kodi_stuff\repo-plugins\plugin.video.reddit_viewer\.gitattributes
git rm -f C:\Kodi_stuff\repo-plugins\plugin.video.reddit_viewer\.gitignore

rem show the differences
git diff --staged

rem Commit the changes
Git commit -m "[plugin.video.reddit_viewer] 2.7.2"

rem push the stuff to the jarvis branch in your github (if everything went ok): 
git push origin jarvis

*** on browser: click on pull request (similar to one above) 
'''