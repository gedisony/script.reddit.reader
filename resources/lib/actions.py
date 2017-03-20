# -*- coding: utf-8 -*-
import xbmc
import xbmcgui
#import xbmcvfs
import sys
import shutil

from default import subredditsFile, addon, addon_path, profile_path, ytdl_core_path
from utils import xbmc_busy, log, translation

def manage_subreddits(subreddit, name, type_):
    from main_listing import index
    log('manage_subreddits(%s, %s, %s)' %(subreddit, name, type_) )
    #this funciton is called by the listSubRedditGUI when user presses left button when on the subreddits list

    #http://forum.kodi.tv/showthread.php?tid=148568
    dialog = xbmcgui.Dialog()
    #funcs = (        addSubreddit,        editSubreddit,        removeSubreddit,    )
    #elected_index = dialog.select(subreddit, ['add new subreddi', 'edit   subreddit', 'remove subreddit'])
    selected_index = dialog.select(subreddit, [translation(32001), translation(32003), translation(32002)])

    #the if statements below is not as elegant as autoselecting the func from funcs but more flexible in the case with add subreddit where we should not send a subreddit parameter
    #    func = funcs[selected_index]
    #     #assign item from funcs to func
    #    func(subreddit, name, type_)
    #log('selected_index ' + str(selected_index))
    if selected_index == 0:       # 0->first item
        addSubreddit('','','')
    elif selected_index == 1:     # 1->second item
        editSubreddit(subreddit,'','')
    elif selected_index == 2:     # 2-> third item
        removeSubreddit(subreddit,'','')
    else:                         #-1 -> escape pressed or [cancel]
        pass

    xbmc_busy(False)
    #this is a hack to force the subreddit listing to refresh.
    #   the calling gui needs to close after calling this function
    #   after we are done editing the subreddits file, we call index() (the start of program) again.
    index("","","")

def addSubreddit(subreddit, name, type_):
    from reddit import this_is_a_multihub, format_multihub
    log( 'addSubreddit ' + subreddit)
    alreadyIn = False

    with open(subredditsFile, 'r') as fh:
        content = fh.readlines()
        #fh.close()

    if subreddit:
        for line in content:
            #log('line=['+line+']toadd=['+subreddit+']')
            if line.strip()==subreddit.strip():
                #log('  MATCH '+line+'='+subreddit)
                alreadyIn = True
        if not alreadyIn:
            with open(subredditsFile, 'a') as fh:
                fh.write(subreddit+'\n')
                #fh.close()
    else:
        #dialog = xbmcgui.Dialog()
        #ok = dialog.ok('Add subreddit', 'Add a subreddit (videos)','or  Multiple subreddits (music+listentothis)','or  Multireddit (/user/.../m/video)')
        #would be great to have some sort of help to show first time user here

        keyboard = xbmc.Keyboard('', translation(32001))
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
                with open(subredditsFile, 'a') as fh:
                    fh.write(subreddit+'\n')
                    #fh.close()

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
    from reddit import this_is_a_multihub, format_multihub
    log( 'editSubreddit ' + subreddit)

    with open(subredditsFile, 'r') as fh:
        content = fh.readlines()
        #fh.close()

    contentNew = ""

    keyboard = xbmc.Keyboard(subreddit, translation(32003))
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

        with open(subredditsFile, 'w') as fh:
            fh.write(contentNew)
            #fh.close()

        xbmc.executebuiltin("Container.Refresh")

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
    liz=xbmcgui.ListItem(label=msg, label2="", iconImage="", thumbnailImage=image_url)
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
    from domains import sitesBase
    from utils import build_script
    directory_items=[]
    label=""

    for idx, d in enumerate(dictlist):
        ti=d['li_thumbnailImage']
        media_url=d.get('DirectoryItem_url')
        media_type=d.get('type')
        media_thumb=d.get('thumb')

        #Error Type: <type 'exceptions.TypeError'> cannot concatenate 'str' and 'list' objects
        log('  display_album_from list:'+ media_url + "  " + repr(media_type) )  # ****** don't forget to add "[0]" when using parseDOM    parseDOM(div,"img", ret="src")[0]

        #There is only 1 textbox for Title and description in our custom gui.
        #  I don't know how to achieve this in the xml file so it is done here:
        #  combine title and description without [CR] if label is empty. [B]$INFO[Container(53).ListItem.Label][/B][CR]$INFO[Container(53).ListItem.Plot]
        #  new note: this is how it is done:
        #     $INFO[Container(53).ListItem.Label,[B],[/B][CR]] $INFO[Container(53).ListItem.Plot]  #if the infolabel is empty, nothing is printed for that block
        combined = '[B]'+ d['li_label2'] + "[/B][CR]" if d['li_label2'] else ""
        combined += d['infoLabels'].get('plot') if d['infoLabels'].get('plot') else ""
        d['infoLabels']['plot'] = combined
        #d['infoLabels']['genre'] = "0,-2000"
        #d['infoLabels']['year'] = 1998
        #log( d['infoLabels'].get('plot') )

        liz=xbmcgui.ListItem(label=label,
                             label2=d['li_label2'],
                             iconImage=media_thumb,
                             thumbnailImage=media_thumb)

        if media_type==sitesBase.TYPE_VIDEO:
            liz.setProperty('item_type','script')
            liz.setProperty('onClick_action', build_script('playYTDLVideo', media_url,'',media_thumb) )

        #classImgur puts the media_url into  d['DirectoryItem_url']  no modification.
        #we modify it here...
        #url_for_DirectoryItem = sys.argv[0]+"?url="+ urllib.quote_plus(d['DirectoryItem_url']) +"&mode=viewImage"
        #hoster, DirectoryItem_url, videoID, mode_type, thumb_url,poster_url, isFolder,setInfo_type, IsPlayable=make_addon_url_from(d['DirectoryItem_url'],False)
        #if poster_url=="": poster_url=ti

        liz.setInfo( type='video', infoLabels= d['infoLabels'] ) #this tricks the skin to show the plot. where we stored the picture descriptions
        #liz.setArt({"thumb": ti, "poster":poster_url, "banner":d['DirectoryItem_url'], "fanart":poster_url, "landscape":d['DirectoryItem_url']   })
        liz.setArt({"thumb": ti, "banner":media_url })

        directory_items.append( (media_url, liz, False,) )

    from guis import cGUI

    #msg=WINDOW.getProperty(url)
    #WINDOW.clearProperty( url )
    #log( '   msg=' + msg )

    #<label>$INFO[Window(10000).Property(foox)]</label>
    #WINDOW.setProperty('view_450_slideshow_title',WINDOW.getProperty(url))

    li=[]
    for di in directory_items:
        #log( str(di[1] ) )
        li.append( di[1] )

    ui = cGUI('view_450_slideshow.xml' , addon_path, defaultSkin='Default', defaultRes='1080i', listing=li, id=53)

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
            xbmc.executebuiltin('XBMC.Notification("%s", "%s" )'  %( translation(32200), translation(32055) )  )  #slideshow, no playable items
            return

        if addon.getSetting('use_slideshow_for_album') == 'true':
            slideshowAlbum( dictlist, name )
        else:
            display_album_from( dictlist, name )

def playURLRVideo(url, name, type_):
    import urlresolver
    from urlparse import urlparse
    parsed_uri = urlparse( url )
    domain = '{uri.netloc}'.format(uri=parsed_uri)
    #hmf = urlresolver.HostedMediaFile(url)
    try:
        media_url = urlresolver.resolve(url)
        if media_url:
            log( '  URLResolver stream url=' + repr(media_url ))

            pl = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
            pl.clear()
            pl.add(media_url, xbmcgui.ListItem(name))
            xbmc.Player().play(pl, windowed=False)  #scripts play video like this.
        else:
            log( "  Can't URL Resolve:" + repr(url))
            xbmc.executebuiltin('XBMC.Notification("%s", "%s (URLresolver" )'  %( translation(30192), domain )  )
    except Exception as e:
        xbmc.executebuiltin('XBMC.Notification("%s","%s (URLresolver)")' %(  str(e), domain )  )

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
        sub_msg=name
    else:
        sub_msg=translation(32021) #Parsing error
    xbmc.executebuiltin('XBMC.Notification("%s", "%s" )' %( message, sub_msg  ) )

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
    from YoutubeDLWrapper import YoutubeDLWrapper, _selectVideoQuality
    import pprint

    pl = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    pl.clear()

    dialog_progress_title='Youtube_dl'  #.format(ytdl_get_version_info())

    dialog_progress_YTDL = xbmcgui.DialogProgressBG()
    dialog_progress_YTDL.create(dialog_progress_title )
    dialog_progress_YTDL.update(10,dialog_progress_title,translation(32012)  )

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

        #log( "YoutubeDL extract_info:\n" + pprint.pformat(ydl_info, indent=1) )
        video_infos=_selectVideoQuality(ydl_info, quality=0, disable_dash=True)
        #log( "video_infos:\n" + pprint.pformat(video_infos, indent=1, depth=5) )
        dialog_progress_YTDL.update(80,dialog_progress_title,translation(32013)  )

        for video_info in video_infos:
            url=video_info.get('xbmc_url')  #there is also  video_info.get('url')  url without the |useragent...
            title=video_info.get('title') or name
            ytdl_format=video_info.get('ytdl_format')
            if ytdl_format:
                description=ytdl_format.get('description')
                #check if there is a time skip code
                try:
                    start_time=ytdl_format.get('start_time',0)   #int(float(ytdl_format.get('start_time')))
                except (ValueError, TypeError):
                    start_time=0

            li=xbmcgui.ListItem(label=title,
                                label2='',
                                iconImage=video_info.get('thumbnail'),
                                thumbnailImage=video_info.get('thumbnail'),
                                path=url)
            li.setInfo( type="Video", infoLabels={ "Title": title, "plot": description } )
            li.setProperty('StartOffset', str(start_time))
            pl.add(url, li)

        xbmc.Player().play(pl, windowed=False)

        #only use the time skip code if there is only one item in the playlist
        #if start_time and pl.size()==1:
        #    xbmc.Player().seekTime(start_time)

    except Exception as e:
        err_msg=str(e)+';'  #ERROR: No video formats found; please report this issue on https://yt-dl.org/bug . Make sure you are using the latest vers....
        short_err=err_msg.split(';')[0]
        log( "playYTDLVideo Exception:" + str( sys.exc_info()[0]) + "  " + str(e) )
        xbmc.executebuiltin('XBMC.Notification("%s", "%s" )'  %( "Youtube_dl", short_err )  )
        #try urlresolver
        log('   trying urlresolver...')
        playURLRVideo(url, name, type_)
    finally:
        dialog_progress_YTDL.update(100,dialog_progress_title ) #not sure if necessary to set to 100 before closing dialogprogressbg
        dialog_progress_YTDL.close()


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
    import os, urllib
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
                xbmc.sleep(2000)
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


if __name__ == '__main__':
    pass
