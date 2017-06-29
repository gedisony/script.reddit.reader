# -*- coding: utf-8 -*-
import xbmc
import xbmcgui
#import xbmcvfs
import sys
import shutil, os
import re, urllib
import pprint
import json

from default import subredditsFile, addon, addon_path, profile_path, ytdl_core_path, subredditsPickle,CACHE_FILE
from utils import xbmc_busy, log, translation, xbmc_notify
from reddit import get_subreddit_entry_info

ytdl_quality=addon.getSetting("ytdl_quality")
try: ytdl_quality=[0, 1, 2, 3][ int(ytdl_quality) ]
except ValueError: ytdl_quality=1
ytdl_DASH=addon.getSetting("ytdl_DASH")=='true'

def manage_subreddits(subreddit_entry, name, type_):
    from main_listing import index
    log('manage_subreddits(%s, %s, %s)' %(subreddit_entry, name, type_) )

    #http://forum.kodi.tv/showthread.php?tid=148568
    dialog = xbmcgui.Dialog()
    #funcs = (        addSubreddit,        editSubreddit,        removeSubreddit,    )
    #elected_index = dialog.select(subreddit, ['add new subreddi', 'edit   subreddit', 'remove subreddit'])
    selected_index = dialog.select(subreddit_entry, [translation(32001), translation(32003), translation(32002), translation(32004)])

    #the if statements below is not as elegant as autoselecting the func from funcs but more flexible in the case with add subreddit where we should not send a subreddit parameter
    #    func = funcs[selected_index]
    #     #assign item from funcs to func
    #    func(subreddit, name, type_)
    #log('selected_index ' + str(selected_index))
    if selected_index == 0:       # 0->first item
        addSubreddit('','','')
    elif selected_index == 1:     # 1->second item
        editSubreddit(subreddit_entry,'','')
    elif selected_index == 2:     # 2-> third item
        removeSubreddit(subreddit_entry,'','')
    elif selected_index == 3:     # 3-> fourth item
        from reddit import subreddit_entry_to_listitem
        li=subreddit_entry_to_listitem(subreddit_entry)
        li_to_KodiFavourites(li)
    else:                         #-1 -> escape pressed or [cancel]
        pass

    xbmc_busy(False)
    #this is a hack to force the subreddit listing to refresh.
    #   the calling gui needs to close after calling this function
    #   after we are done editing the subreddits file, we call index() (the start of program) again.
    index("","","")

def addSubreddit(subreddit, name, type_):
    from utils import colored_subreddit
    from reddit import this_is_a_multireddit, format_multihub
    alreadyIn = False
    with open(subredditsFile, 'r') as fh:
        content = fh.readlines()
    if subreddit:
        for line in content:
            if line.lower()==subreddit.lower():
                alreadyIn = True
        if not alreadyIn:
            with open(subredditsFile, 'a') as fh:
                fh.write(subreddit+'\n')

            get_subreddit_entry_info(subreddit)
        xbmc_notify(colored_subreddit(subreddit), translation(32019) )
    else:
        #dialog = xbmcgui.Dialog()
        #ok = dialog.ok('Add subreddit', 'Add a subreddit (videos)','or  Multiple subreddits (music+listentothis)','or  Multireddit (/user/.../m/video)')
        #would be great to have some sort of help to show first time user here

        keyboard = xbmc.Keyboard('', translation(32001))
        keyboard.doModal()
        if keyboard.isConfirmed() and keyboard.getText():
            subreddit = keyboard.getText()

            #cleanup user input. make sure /user/ and /m/ is lowercase
            if this_is_a_multireddit(subreddit):
                subreddit = format_multihub(subreddit)
            else:
                get_subreddit_entry_info(subreddit)

            for line in content:
                if line.lower()==subreddit.lower()+"\n":
                    alreadyIn = True

            if not alreadyIn:
                with open(subredditsFile, 'a') as fh:
                    fh.write(subreddit+'\n')

        xbmc.executebuiltin("Container.Refresh")

def removeSubreddit(subreddit, name, type_):
    log( 'removeSubreddit ' + subreddit)

    with open(subredditsFile, 'r') as fh:
        content = fh.readlines()

    contentNew = ""
    for line in content:
        if line!=subreddit+'\n':
            #log('line='+line+'toremove='+subreddit)
            contentNew+=line
    with open(subredditsFile, 'w') as fh:
        fh.write(contentNew)
        #fh.close()
    xbmc.executebuiltin("Container.Refresh")

def editSubreddit(subreddit, name, type_):
    from reddit import this_is_a_multireddit, format_multihub
    log( 'editSubreddit ' + subreddit)

    with open(subredditsFile, 'r') as fh:
        content = fh.readlines()

    contentNew = ""

    keyboard = xbmc.Keyboard(subreddit, translation(32003))
    keyboard.doModal()
    if keyboard.isConfirmed() and keyboard.getText():
        newsubreddit = keyboard.getText()
        #cleanup user input. make sure /user/ and /m/ is lowercase
        if this_is_a_multireddit(newsubreddit):
            newsubreddit = format_multihub(newsubreddit)
        else:
            get_subreddit_entry_info(newsubreddit)

        for line in content:
            if line.strip()==subreddit.strip() :      #if matches the old subreddit,
                #log("adding: %s  %s  %s" %(line, subreddit, newsubreddit)  )
                contentNew+=newsubreddit+'\n'
            else:
                contentNew+=line

        with open(subredditsFile, 'w') as fh:
            fh.write(contentNew)

        xbmc.executebuiltin("Container.Refresh")

def searchReddits(url, subreddit, type_):
    from default import urlMain
    from main_listing import listSubReddit

    #reddit search only works with a single subreddit
    if subreddit:
        initial_search_string='restrict_sr=on&sort=relevance&t=all&q='
        initial_url=urlMain+'/r/'+subreddit
    else:
        initial_search_string='sort=relevance&t=year&q='
        initial_url=urlMain

    keyboard = xbmc.Keyboard(initial_search_string, translation(32073))
    keyboard.doModal()
    if keyboard.isConfirmed() and keyboard.getText():

        search_string=keyboard.getText()

        if search_string:
            search_string=urllib.quote_plus(search_string,safe='&=') #only &= are used because they're in the initial_search_string

    #    #this    https://www.reddit.com/r/Art/.json?&nsfw:no+&limit=10
    #    #becomes https://www.reddit.com/r/Art/search.json?&nsfw:no+&limit=10&q=SEARCHTERM&restrict_sr=on&sort=relevance&t=all
        url = initial_url +"/search.json?" +search_string    #+ '+' + nsfw  # + sites_filter skip the sites filter

        listSubReddit(url, 'Search', "")

def setting_gif_repeat_count():
    srepeat_gif_video= addon.getSetting("repeat_gif_video")
    try: repeat_gif_video = int(srepeat_gif_video)
    except ValueError: repeat_gif_video = 0
    #repeat_gif_video          = [0, 1, 3, 10, 100][repeat_gif_video]
    return [0, 1, 3, 10, 100][repeat_gif_video]

def viewImage(image_url, name, preview_url):
    from guis import cGUI

    log('  viewImage %s, %s, %s' %( image_url, name, preview_url))

    #msg=WINDOW.getProperty(url)
    #WINDOW.clearProperty( url )
    #log( '   msg=' + msg )
    msg=""
    li=[]
    liz=xbmcgui.ListItem(label=msg, label2="")
    liz.setInfo( type='video', infoLabels={"plot": msg, } )
    liz.setArt({"thumb": preview_url, "banner":image_url })

    li.append(liz)
    ui = cGUI('view_450_slideshow.xml' , addon_path, defaultSkin='Default', defaultRes='1080i', listing=li, id=53)
    ui.include_parent_directory_entry=False

    ui.doModal()
    del ui
    return

#     from resources.lib.guis import qGUI
#
#     ui = qGUI('view_image.xml' ,  addon_path, defaultSkin='Default', defaultRes='1080i')
#     #no need to download the image. kodi does it automatically!!!
#     ui.image_path=url
#     ui.doModal()
#     del ui
#     return
#
#     #this is a workaround to not being able to show images on video addon
#     log('viewImage:'+url +'  ' + name )
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

def viewTallImage(image_url, width, height):
    log( 'viewTallImage %s: %sx%s' %(image_url, width, height))
    #image_url=unescape(image_url) #special case for handling reddituploads urls
    #log( 'viewTallImage %s: %sx%s' %(image_url, width, height))

    xbmc_busy(False)

    can_quit=True
    if can_quit==True:
        useWindow=xbmcgui.WindowDialog()
        useWindow.setCoordinateResolution(0)

        try:
            w=int(float(width))
            h=int(float(height))
            optimal_h=int(h*1.5)
            #log( '    **' + repr(h))
            loading_img = xbmc.validatePath('/'.join((addon_path, 'resources', 'skins', 'Default', 'media', 'srr_busy.gif' )))

            img_control = xbmcgui.ControlImage(0, 800, 1920, optimal_h, '', aspectRatio=2)  #(values 0 = stretch (default), 1 = scale up (crops), 2 = scale down (black bars)
            img_loading = xbmcgui.ControlImage(1820, 0, 100, 100, loading_img, aspectRatio=2)

            #the cached image is of lower resolution. we force nocache by using setImage() instead of defining the image in ControlImage()
            img_control.setImage(image_url, False)

            useWindow.addControls( [ img_loading, img_control])
            #useWindow.addControl(  img_control )

            scroll_time=(int(h)/int(w))*20000

            img_control.setAnimations( [
                                        ('conditional', "condition=true effect=fade  delay=0    start=0   end=100   time=4000 "  ) ,
                                        ('conditional', "condition=true effect=slide delay=2000 start=0,-%d end=0,0 tween=sine easing=in time=%d pulse=true" %( (h*1.4), scroll_time) ),
                                        ]  )

            useWindow.doModal()
            useWindow.removeControls( [img_control,img_loading] )
            del useWindow
        except Exception as e:
            log("  EXCEPTION viewTallImage:="+ str( sys.exc_info()[0]) + "  " + str(e) )

    else:
        # can be done this way but can't get keypress to exit animation
        useWindow = xbmcgui.Window( xbmcgui.getCurrentWindowId() )
        xbmc_busy(False)
        w=int(float(width))
        h=int(float(height))
        optimal_h=int(h*1.5)
        #log( '    **' + repr(h))
        loading_img = xbmc.validatePath('/'.join((addon_path, 'resources', 'skins', 'Default', 'media', 'srr_busy.gif' )))

        img_control = xbmcgui.ControlImage(0, 1080, 1920, optimal_h, '', aspectRatio=2)  #(values 0 = stretch (default), 1 = scale up (crops), 2 = scale down (black bars)
        img_loading = xbmcgui.ControlImage(1820, 0, 100, 100, loading_img, aspectRatio=2)

        #the cached image is of lower resolution. we force nocache by using setImage() instead of defining the image in ControlImage()
        img_control.setImage(image_url, False)
        useWindow.addControls( [ img_loading, img_control])
        scroll_time=int(h)*(int(h)/int(w))*10
        img_control.setAnimations( [
                                    ('conditional', "condition=true effect=fade  delay=0    start=0   end=100   time=4000 "  ) ,
                                    ('conditional', "condition=true effect=slide delay=2000 start=0,0 end=0,-%d time=%d pulse=true" %( (h*1.6) ,scroll_time) ),
                                    ('conditional', "condition=true effect=fade  delay=%s   start=100 end=0     time=2000 " %(scroll_time*1.8) ) ,
                                    ]  )
        xbmc.sleep(scroll_time*2)
        useWindow.removeControls( [img_control,img_loading] )

def display_album_from(dictlist, album_name):
    from utils import dictlist_to_listItems

    directory_items=dictlist_to_listItems(dictlist)

    from guis import cGUI

    #msg=WINDOW.getProperty(url)
    #WINDOW.clearProperty( url )
    #log( '   msg=' + msg )

    ui = cGUI('view_450_slideshow.xml' , addon_path, defaultSkin='Default', defaultRes='1080i', listing=directory_items, id=53)
    ui.include_parent_directory_entry=False
    #ui.title_bar_text=WINDOW.getProperty(url)

    ui.doModal()
    del ui

def listAlbum(album_url, name, type_):
    from slideshow import slideshowAlbum
    from domains import sitesManager
    log("    listAlbum:"+album_url)

    hoster = sitesManager( album_url )
    #log( '  %s %s ' %(hoster.__class__.__name__, album_url ) )

    if hoster:
        dictlist=hoster.ret_album_list(album_url)

        if type_=='return_dictlist':  #used in autoSlideshow
            return dictlist

        if not dictlist:
            xbmc_notify(translation(32200), translation(32055)) #slideshow, no playable items
            return
        #log(pprint.pformat(dictlist))
        if addon.getSetting('use_slideshow_for_album') == 'true':
            slideshowAlbum( dictlist, name )
        else:
            display_album_from( dictlist, name )

def playURLRVideo(url, name, type_):
    dialog_progress_title='URL Resolver'
    dialog_progress_YTDL = xbmcgui.DialogProgressBG()
    dialog_progress_YTDL.create(dialog_progress_title )
    dialog_progress_YTDL.update(10,dialog_progress_title,translation(32014)  )

    import urlresolver
    from urlparse import urlparse
    parsed_uri = urlparse( url )
    domain = '{uri.netloc}'.format(uri=parsed_uri)
    #hmf = urlresolver.HostedMediaFile(url)
    dialog_progress_YTDL.update(20,dialog_progress_title,translation(32012)  )

    try:
        media_url = urlresolver.resolve(url)
        dialog_progress_YTDL.update(80,dialog_progress_title,translation(32013)  )
        if media_url:
            log( '  URLResolver stream url=' + repr(media_url ))

            pl = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
            pl.clear()
            pl.add(media_url, xbmcgui.ListItem(name))
            xbmc.Player().play(pl, windowed=False)  #scripts play video like this.
        else:
            log( "  Can't URL Resolve:" + repr(url))
            xbmc_notify('URLresolver', translation(32192),icon="type_urlr.png" )  #Failed to get playable url
    except Exception as e:
        xbmc_notify('URLresolver:'+domain, str(e),icon="type_urlr.png" )
    dialog_progress_YTDL.close()

def loopedPlayback(url, name, type_):
    #for gifs
    #log('*******************loopedplayback ' + url)
    pl = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    pl.clear()
    pl.add(url, xbmcgui.ListItem(name))
    for _ in range( 0, setting_gif_repeat_count() ):
        pl.add(url, xbmcgui.ListItem(name))

    #pl.add(url, xbmcgui.ListItem(name))
    xbmc.Player().play(pl, windowed=False)

def error_message(message, name, type_):
    if name:
        sub_msg=name  #name is usually the title of the post
    else:
        sub_msg=translation(32021) #Parsing error
    xbmc_notify(message, sub_msg)

def playVideo(url, name, type_):
    xbmc_busy(False)

    pl = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    pl.clear()

    if url : #sometimes url is a list of url or just a single string
        if isinstance(url, basestring):
            pl.add(url, xbmcgui.ListItem(name))
            xbmc.Player().play(pl, windowed=False)  #scripts play video like this.
            #listitem = xbmcgui.ListItem(path=url)   #plugins play video like this.
            #xbmcplugin.setResolvedUrl(pluginhandle, True, listitem)
        else:
            for u in url:
                #log('u='+ repr(u))
                #pl.add(u)
                pl.add(u, xbmcgui.ListItem(name))
            xbmc.Player().play(pl, windowed=False)
    else:
        log("playVideo(url) url is blank")

def playYTDLVideo(url, name, type_):
    dialog_progress_title='Youtube_dl'  #.format(ytdl_get_version_info())
    dialog_progress_YTDL = xbmcgui.DialogProgressBG()
    dialog_progress_YTDL.create(dialog_progress_title )
    dialog_progress_YTDL.update(10,dialog_progress_title,translation(32014)  )

    from YoutubeDLWrapper import YoutubeDLWrapper, _selectVideoQuality
    from urlparse import urlparse, parse_qs

    o = urlparse(url)
    query = parse_qs(o.query)
    video_index=0
    #note that in domains.py youtube class will send a simplified url to avoid sending
    #   https://www.youtube.com/watch?v=R6_dZhE-4bk&index=22&list=PLGJ6ezwqAB2a4RP8hWEWAGB9eT2bmaBsy  (ytdl will parse around 90+ videos, takes a very long time)
    #   http://youtube.com/v/R6_dZhE-4bk   (will be faster)
    if 'index' in query:
        try:video_index=int(query['index'][0])
        except (TypeError, ValueError): video_index=0
        #log( repr(video_index) )
        dialog_progress_YTDL.update(20,dialog_progress_title,translation(32017)  )
    else:
        #if there is index, link is likely a playlist, parsing will take a looooong time.
        #  we move progress dialog here to differentiate
        dialog_progress_YTDL.update(20,dialog_progress_title,translation(32012)  )

    pl = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    pl.clear()

    #use YoutubeDLWrapper by ruuk to avoid  bad file error
    ytdl=YoutubeDLWrapper()
    try:
        ydl_info=ytdl.extract_info(url, download=False)
        #in youtube_dl utils.py def unified_timestamp(date_str, day_first=True):
        # there was an error playing https://vimeo.com/14652586
        #   on line 1195:
        # change          except ValueError:
        #     to          except (ValueError,TypeError):
        #   this already fixed by ruuk magic. in YoutubeDLWrapper

        #log( "YoutubeDL extract_info:\n" + pprint.pformat(ydl_info, indent=1, depth=3) )
        #log('quality============='+repr(ytdl_quality))
        #log('ytdl_DASH==========='+repr(ytdl_DASH))
        #link_type=ydl_info.get("_type")
        #entries=ydl_info.get('entries')
        video_infos=_selectVideoQuality(ydl_info, quality=ytdl_quality, disable_dash=(not ytdl_DASH) )
        log( "video_infos:\n" + pprint.pformat(video_infos, indent=1, depth=3) )
        dialog_progress_YTDL.update(80,dialog_progress_title,translation(32013)  )

        if video_index > 0:
            add_ytdl_video_info_to_playlist(video_infos[video_index-1], pl, name)
        else:
            for video_info in video_infos:
                add_ytdl_video_info_to_playlist(video_info, pl, name)

        if len(pl)>1:
            xbmc_notify("Multiple video", "{} videos in playlist".format(len(pl)))

        xbmc.Player().play(pl, windowed=False)
        #only use the time skip code if there is only one item in the playlist
        #if start_time and pl.size()==1:
        #    xbmc.Player().seekTime(start_time)

    except Exception as e:
        ytdl_ver=dialog_progress_title+' v'+ytdl_get_version_info('local')
        err_msg=str(e)+';'  #ERROR: No video formats found; please report this issue on https://yt-dl.org/bug . Make sure you are using the latest vers....
        short_err=err_msg.split(';')[0]
        log( "playYTDLVideo Exception:" + str( sys.exc_info()[0]) + "  " + str(e) )
        xbmc_notify(ytdl_ver, short_err,icon='type_ytdl.png')

        #try urlresolver
        log('   trying urlresolver...')
        playURLRVideo(url, name, type_)
    finally:
        dialog_progress_YTDL.update(100,dialog_progress_title ) #not sure if necessary to set to 100 before closing dialogprogressbg
        dialog_progress_YTDL.close()

def add_ytdl_video_info_to_playlist(video_info, pl, title=None):
    url=video_info.get('xbmc_url')  #there is also  video_info.get('url')  url without the |useragent...
    #log('***befor:'+repr(url))
    url=urllib.quote_plus(url.encode('utf-8'), safe="&$+,/:;=?@#<>[]{}|\^%")
    #log('***after :'+repr(url))
    title=video_info.get('title') or title
    ytdl_format=video_info.get('ytdl_format')
    if ytdl_format:
        description=ytdl_format.get('description')
        #check if there is a time skip code
        try:
            start_time=ytdl_format.get('start_time',0)   #int(float(ytdl_format.get('start_time')))
        except (ValueError, TypeError):
            start_time=0

        video_thumbnail=video_info.get('thumbnail')
    li=xbmcgui.ListItem(label=title,
                        label2='',
                        path=url)
    li.setArt({"thumb": video_thumbnail, "icon":video_thumbnail })
    li.setInfo( type="Video", infoLabels={ "Title": title, "plot": description } )
    li.setProperty('StartOffset', str(start_time))
    pl.add(url, li)

YTDL_VERSION_URL = 'https://yt-dl.org/latest/version'
YTDL_LATEST_URL_TEMPLATE = 'https://yt-dl.org/latest/youtube-dl-{}.tar.gz'

def ytdl_get_version_info(which_one='latest'):
    import urllib2
    if which_one=='latest':
        try:
            newVersion = urllib2.urlopen(YTDL_VERSION_URL).read().strip()
            return newVersion
        except:
            return "0.0"
    else:
        try:
            #*** it seems like the script.module.youtube_dl version gets imported if the one from resources.lib is missing
            from youtube_dl.version import __version__
            return __version__
        except Exception as e:
            log('error getting ytdl local version:'+str(e))
            return "0.0"

def update_youtube_dl_core(url,name,action_type):
#credit to ruuk for most of the download code
    import urllib
    import tarfile

    if action_type=='download':
        newVersion=note_ytdl_versions()
        LATEST_URL=YTDL_LATEST_URL_TEMPLATE.format(newVersion)

        profile = xbmc.translatePath(profile_path)  #xbmc.translatePath(addon.getAddonInfo('profile')).decode('utf-8')
        archivePath = os.path.join(profile,'youtube_dl.tar.gz')
        extractedPath = os.path.join(profile,'youtube-dl')
        extracted_core_path=os.path.join(extractedPath,'youtube_dl')
        #ytdl_core_path  xbmc.translatePath(  addon_path+"/resources/lib/youtube_dl/" )

        try:
            if os.path.exists(extractedPath):
                shutil.rmtree(extractedPath, ignore_errors=True)
                update_dl_status('temp files removed')

            update_dl_status('Downloading {0} ...'.format(newVersion))
            log('  From: {0}'.format(LATEST_URL))
            log('    to: {0}'.format(archivePath))
            urllib.urlretrieve(LATEST_URL,filename=archivePath)

            if os.path.exists(archivePath):
                update_dl_status('Extracting ...')

                with tarfile.open(archivePath,mode='r:gz') as tf:
                    members = [m for m in tf.getmembers() if m.name.startswith('youtube-dl/youtube_dl')] #get just the files from the youtube_dl source directory
                    tf.extractall(path=profile,members=members)
            else:
                update_dl_status('Download failed')
        except Exception as e:
            update_dl_status('Error:' + str(e))

        update_dl_status('Updating...')

        if os.path.exists(extracted_core_path):
            log( '  extracted dir exists:'+extracted_core_path)

            if os.path.exists(ytdl_core_path):
                log( '  destination dir exists:'+ytdl_core_path)
                shutil.rmtree(ytdl_core_path, ignore_errors=True)
                update_dl_status('    Old ytdl core removed')
                xbmc.sleep(1000)
            try:
                shutil.move(extracted_core_path, ytdl_core_path)
                update_dl_status('    New core copied')
                xbmc.sleep(1000)
                update_dl_status('Update complete')
                xbmc.Monitor().waitForAbort(2.0)
                #ourVersion=ytdl_get_version_info('local')
                setSetting('ytdl_btn_check_version', "")
                setSetting('ytdl_btn_download', "")
            except Exception as e:
                update_dl_status('Failed...')
                log( 'move failed:'+str(e))

    elif action_type=='checkversion':
        note_ytdl_versions()

def note_ytdl_versions():
    #display ytdl versions and return latest version
    setSetting('ytdl_btn_check_version', "checking...")
    ourVersion=ytdl_get_version_info('local')
    setSetting('ytdl_btn_check_version', "{0}".format(ourVersion))

    setSetting('ytdl_btn_download', "checking...")
    newVersion=ytdl_get_version_info('latest')
    setSetting('ytdl_btn_download',      "latest {0}".format(newVersion))

    return newVersion


def update_dl_status(message):
    log(message)
    setSetting('ytdl_btn_download', message)

def setSetting(setting_id, value):
    addon.setSetting(setting_id, value)

def delete_setting_file(url,name,action_type):
    #log( "delete setting file:" + action_type)
    if action_type=='requests_cache':
        file_to_delete=CACHE_FILE+'.sqlite'
    elif action_type=='icons_cache':
        file_to_delete=subredditsPickle
    elif action_type=='subreddits_setting':
        file_to_delete=subredditsFile

    try:
        os.remove(file_to_delete)
        xbmc_notify("Deleting", '..'+file_to_delete[-30:])
    except OSError as e:
        xbmc_notify("Error:", str(e))

def listRelatedVideo(url,name,type_):
    #type_: 'channel' -other videos in the channel
    #       'related' -related videos
    #only youtube is supported for now
    from domains import ClassYoutube
    import requests
    #log('*****name='+repr(name))
    links_dictList=[]
    match=re.compile( ClassYoutube.regex, re.I).findall( url )
    if match:
        #log('***** isYouTubeable' + repr(url))
        yt=ClassYoutube(url)
        try:
            yt.get_thumb_url()
            poster=yt.poster_url
            #log('  thung:'+yt.thumb_url)
            url_type,_=yt.get_video_channel_user_or_playlist_id_from_url(url)
            #log('  listRelatedVideo:type_:{} url_type:{} url:{}'.format(type_,url_type,url) )
            xbmc_busy(True)
            if type_=='links_in_description':
                links_dictList=yt.get_links_in_description(return_channelID_only=False)
            elif type_=='search':
                keyboard = xbmc.Keyboard(name, translation(32529))
                keyboard.doModal()
                if keyboard.isConfirmed() and keyboard.getText():
                    search_string=keyboard.getText()
                    if search_string:
                        links_dictList=yt.ret_album_list(type_,search_string)
                        name=search_string #this shows up on the top of screen

            else: # 'channel' 'related default
                links_dictList=yt.ret_album_list(type_)  #returns a list of dict same as one used for albums
            xbmc_busy(False)

            if links_dictList:
                dictlist_to_RelatedVideo_gui(links_dictList, url, url_type, name, type_, poster)
            else:
                xbmc_notify('Nothing to list', url)

        except (ValueError, requests.exceptions.RequestException) as e:
            xbmc_notify('Error', str(e))
        finally:
            xbmc_busy(False)
    else:
        xbmc_notify('cannot identify youtube url', url)

def dictlist_to_RelatedVideo_gui(dictlist, url, url_type, title, type_, poster=None ):
    from utils import dictlist_to_listItems
    from ContextMenus import build_youtube_context_menu_entries, build_add_to_favourites_context_menu_entry

    context_menu_list=[]

    gui_title_text=None
    if dictlist:
        #log(pprint.pformat(dictlist))
        directory_items=dictlist_to_listItems(dictlist)
        for li in directory_items:
            link_url=li.getProperty('link_url')
            video_id=li.getProperty('video_id')
            label=li.getLabel()
            channel_name=li.getProperty('channel_name')
            channel_id=li.getProperty('channel_id')
            onClick_action=li.getProperty('onClick_action')
            thumbnail=li.getArt('thumb')
            del context_menu_list[:] #empty the list
            context_menu_list.extend(build_youtube_context_menu_entries(type_,link_url,video_id, title=label, channel_id_from_previous_listing=channel_id,channel_name=channel_name))
            context_menu_list.extend(build_add_to_favourites_context_menu_entry(label,onClick_action,thumbnail) )
            li.setProperty('context_menu', str(context_menu_list) )

        if type_=='links_in_description':
            from guis import text_to_links_gui
            ui = text_to_links_gui('srr_links_in_text.xml' , addon_path, defaultSkin='Default', defaultRes='1080i', listing=directory_items, title=title, poster=poster)

        else: # 'channel' 'related' default
            if type_=='related':
                gui_title_text="Related videos: {}".format(title)
            if type_=='search':
                gui_title_text="Search: {}".format(title)
            elif type_=='channel':
                gui_title_text="Channel: {}".format(dictlist[0].get('channel_name'))
            elif type_=='playlist':
                gui_title_text="{}".format(title)
            elif type_=='playlists':
                gui_title_text="Playlists in channel: {}".format(dictlist[0].get('channel_name'))
            else:#type determined from url
                if url_type=='channel':
                    gui_title_text="Videos in channel"
                elif url_type=='playlist':
                    gui_title_text="{}".format(title)
                elif url_type=='user':
                    gui_title_text="User Videos"
                elif url_type=='more':
                    gui_title_text="{}".format(title)

            from guis import cGUI
            ui = cGUI('srr_related_videos.xml' , addon_path, defaultSkin='Default', defaultRes='1080i', listing=directory_items, id=55, title=gui_title_text, poster=poster)
            ui.include_parent_directory_entry=False
        ui.doModal()
        del ui

def listMoreVideo(google_api_request_url,label_name,type_):
    from domains import ClassYoutube
    from utils import safe_cast

    #https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&type=video&maxResults=50&key=AIzaSyCqvYW8NI-OpMPaWR1DuZYW_llpmFdHRBI&playlistId=PLJ8cMiYb3G5eJquaiw6Xlyt3Qhe-3e7Xh
    yt=ClassYoutube(google_api_request_url)#this will be a broken class because it won't be able to parse

    just_numbers_from_label=re.sub("[^0-9]", "", label_name) #Removes all non-numeric characters  "Page 2" becomes "2"
    page_indicator=safe_cast(just_numbers_from_label,int,default=0)
    links=yt.get_video_list(None,None,google_api_request_url,page_indicator)
    yt.assemble_images_dictList(links)

    links_dictList=yt.dictList

    if links_dictList:
        dictlist_to_RelatedVideo_gui(links_dictList, google_api_request_url, 'more', label_name, type_)
    else:
        xbmc_notify('Nothing to list', google_api_request_url)

def li_to_KodiFavourites(listitem):
    onClick_action=listitem.getProperty('onClick_action')
    if onClick_action:
        addtoKodiFavorites(command=onClick_action,
                           name=listitem.getLabel(),
                           thumbnail=listitem.getArt('thumb')
                           )

def addtoKodiFavorites(command, name, thumbnail):
    import xml.etree.ElementTree
    from utils import unescape

#adding to favorites involve 3 steps:
#  1.) add the favorite via jsonrpc (script params not included)
#  2.) modify the favourites.xml to include script params <-- (kodi18 leia alpha1) i think there is another favourites file or this file is cached until another favorite is added
#  3.) ??? <-- adding another favorite will delete the first one (until kodi is restarted) need to find a way for kodi to reload the modified favourite.xml

    #http://kodi.wiki/view/JSON-RPC_API/v8#Favourites
    #schema=xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "JSONRPC.Introspect", "id": 1}')
    #log(repr(schema))
    favorite_was_found=False
    #add_dummy_favorite()
    temp_command='script.reddit.reader' #can't add script favorites with parameter using jsonrpc
    saved_command='RunScript("script.reddit.reader")'

    json_rpc_command={"jsonrpc": "2.0",
                      "method": "Favourites.AddFavourite",
                      'params': {
                                 'title': name,
                                 'type': 'script',
                                 'path': temp_command,
                                 'thumbnail':thumbnail,
                                 },
                      'id': '1'
                      }
    a=xbmc.executeJSONRPC(json.dumps(json_rpc_command))
    #log(repr(a))
    a=json.loads(a)
    if a.get('result','')=="OK":
        log('Favourite added')
        #now that we've created the favorite, we edit it to add parameters
        favorites_xml       = xbmc.translatePath(os.path.join(addon.getAddonInfo('profile'), '..','..','favourites.xml'))
        if os.path.exists(favorites_xml):
            #log('{} exists'.format(favorites_xml) )
            et = xml.etree.ElementTree.parse(favorites_xml)
            root=et.getroot()

            for f in root.findall('favourite'):
                #the name attribute is escape encoded the xml file.
                fav_name=unescape( f.get('name') ) #replaces &amp; to & etc.
                fav_cmd=f.text
                #log('*a*'+repr(name) + '  ' + saved_command)
                #log('*b*'+repr(fav_name) + '  ' + fav_cmd )
                #log('---')
                if (fav_name==name) and (fav_cmd==saved_command):
                    log('Favourite entry found {}'.format(fav_name) )
                    favorite_was_found=True
                    f.text=command

            if favorite_was_found:
                et.write(favorites_xml)
                xbmc_notify(translation(32028), fav_name, icon=thumbnail)
                #log('Favourite file updated')

    #add_dummy_favorite() #second time removes it

def add_dummy_favorite():
    json_rpc_command={"jsonrpc": "2.0",
                      "method": "Favourites.AddFavourite",
                      'params': {
                                 'title': 'dummy',
                                 'type': 'script',
                                 'path': 'dummy_command_enough_to_e_unique',
                                 },
                      'id': '1'
                      }
    a=xbmc.executeJSONRPC(json.dumps(json_rpc_command))
    log("dummy favorite:" + repr(a))

if __name__ == '__main__':
    pass
