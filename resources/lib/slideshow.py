import xbmc
import json
import xbmcvfs
import random
import sys

from xbmcgui import ControlImage, WindowDialog, WindowXMLDialog, Window, ControlTextBox, ControlLabel

#autoSlideshow

from default import addon, log, translation, addon_path, addonID,SlideshowCacheFolder, reddit_request, getPlayCount
from domains import sitesManager, sitesBase, parse_reddit_link, listAlbum

from utils import unescape, post_excluded_from, determine_if_video_media_from_reddit_json, remove_duplicates

from functools import partial

import threading
from Queue import Queue, Empty

ADDON_NAME = addonID      #addon.getAddonInfo('name')  <--changed to id
ADDON_PATH = addon_path   #addon.getAddonInfo('path')  

q=Queue()

def slideshowAlbum(dictlist, name):
    log("slideshowAlbum")

    entries=[]        
    for d in dictlist:
        media_url=d.get('DirectoryItem_url')
        title    =d.get('li_label')
        width    =d.get('width')
        height   =d.get('height')
        
        entries.append([title,media_url, width, height, len(entries)])

    def k2(x): return x[1]
    entries=remove_duplicates(entries, k2)

    for e in entries:
        q.put(e)
    
    #s= AppleTVLikeScreensaver(ev,q)
    #s= TableDropScreensaver(ev,q)
    ev=threading.Event()
    
    #s= HorizontalSlideScreensaver(ev,q)
    s= ScreensaverManager(ev,q)
    
    try:
        s.start_loop()
    except Exception as e: 
        log("  EXCEPTION slideshowAlbum:="+ str( sys.exc_info()[0]) + "  " + str(e) )    

    s.close()
    del s
    sys.modules.clear()
    
    
    return


def autoSlideshow(url, name, type):
    #from domains import sitesBase, parse_reddit_link
    #from utils import unescape, post_excluded_from, determine_if_video_media_from_reddit_json, remove_duplicates
    #from default import reddit_request, getPlayCount
    #collect a list of title and urls as entries[] from the j_entries obtained from reddit
    #then create a playlist from those entries
    #then play the playlist


#     newWindow=WindowDialog()
#     newWindow.setCoordinateResolution(0)
#  
#     #ctl3=ControlImage(0, 0, 1920, 1080, 'http://i.imgur.com/E0qPa3D.jpg', aspectRatio=2)
#     ctl3=ControlImage(0, 0, 1920, 1080, 'd:\\emi_camera\\IMG_0023.JPG', aspectRatio=2)
#     newWindow.addControl(ctl3)
#  
#     #scroll_time=int(height)*(int(height)/int(width))*2
#     #zoom_effect="effect=zoom loop=true delay=1000 center=960 end=%d time=1000" %zoom
#     #fade_effect="condition=true effect=slide delay=2000 start=0,0 end=0,-%d time=%d pulse=true" %(slide,scroll_time)
#     #ctl3.setAnimations([('WindowOpen', zoom_effect), ('conditional', fade_effect,) ])
#      
#     newWindow.show()
#     xbmc.sleep(8000)
#     #newWindow.doModal()
#     del newWindow
#     

    #xbmc_window = Window()
    #xbmc_window.show()

#     def stop():        pass
#     xbmc_window = ScreensaverWindow(stop)
#     
#     ctl3=ControlImage(0, 0, 1920, 1080, 'd:\\emi_camera\\IMG_0023.JPG', aspectRatio=2)
#     xbmc_window.addControl(ctl3)
# 
#     xbmc_window.show()
#     xbmc.sleep(8000)
#     return

    log('starting slideshow '+ url)
    ev=threading.Event()
    
    
    entries = []
    watchdog_counter=0
    preview_w=0
    preview_h=0
    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    playlist.clear()

    #content = opener.open(url).read()
    content = reddit_request(url)        
    if not content: return
    #log( str(content) )
    #content = json.loads(content.replace('\\"', '\''))
    content = json.loads(content)
    
    log("slideshow %s-Parsing %d items" %( type, len(content['data']['children']) )    )
    
    for j_entry in content['data']['children']:
        try:
            title = unescape(j_entry['data']['title'].encode('utf-8'))
            log("  TITLE:%s "  %( title ) )
            
            try:
                media_url = j_entry['data']['url']
            except:
                media_url = j_entry['data']['media']['oembed']['url']

            try:
                preview=j_entry['data']['preview']['images'][0]['source']['url'].encode('utf-8').replace('&amp;','&')
                try:
                    preview_h = float( j_entry['data']['preview']['images'][0]['source']['height'] )
                    preview_w = float( j_entry['data']['preview']['images'][0]['source']['width'] )
                except:
                    preview_w=0
                    preview_h=0

            except Exception as e:
                #log("   getting preview image EXCEPTION:="+ str( sys.exc_info()[0]) + "  " + str(e) )
                preview="" 

             


            ld=parse_reddit_link(link_url=media_url, assume_is_video=False, needs_preview=True, get_playable_url=True )
            if ld:
                if not preview:
                    preview = ld.poster
                
                
                if (addon.getSetting('include_albums')=='true') and (ld.media_type==sitesBase.TYPE_ALBUM) :
                    dictlist = listAlbum( media_url, title, 'return_dictlist')
                    for d in dictlist:
                        #log('    (S) adding items from album ' + title  +' ' + d.get('DirectoryItem_url') )
                        t2=d.get('li_label') if d.get('li_label') else title
                        entries.append([ t2, d.get('DirectoryItem_url'), d.get('width'), d.get('height'), len(entries)])
                
                else:
                    if addon.getSetting('use_reddit_preview')=='true':
                        if preview: entries.append([title,preview,preview_w, preview_h,len(entries)]) #log('      (N)added preview:%s %s' %( title,preview) )
                        elif ld.poster: entries.append([title,ld.poster,preview_w, preview_h,len(entries)])    #log('      (N)added poster:%s %s' % ( title,ld.poster) ) 
                    else:
                        if ld.poster: entries.append([title,ld.poster,preview_w, preview_h,len(entries)])
                        elif preview: entries.append([title,preview,preview_w, preview_h,len(entries)])
            else: 
                if preview:
                    #log('      (N)added preview:%s' % title )
                    entries.append([title,preview,preview_w, preview_h,len(entries)])
                        

                    
        except Exception as e:
            log( '  autoPlay exception:' + str(e) )
            pass
    
    #for i,e in enumerate(entries): log('  e1-%d %s' %(i, e[1]) )
    def k2(x): return x[1]
    entries=remove_duplicates(entries, k2)
    #for i,e in enumerate(entries): log('  e2-%d %s' %(i, e[1]) )

    for e in entries: 
        log('  possible playable items(%d) %s...%s' %(e[4], e[0].ljust(15)[:15], e[1]) )
        
    if len(entries)==0:
        log('  Play All: no playable items' )
        xbmc.executebuiltin('XBMC.Notification("%s","%s")' %(translation(32054), translation(32055)  ) )  #Play All     No playable items
        return
    
    entries_to_buffer=4
    #log('  entries:%d buffer:%d' %( len(entries), entries_to_buffer ) )
    if len(entries) < entries_to_buffer:
        entries_to_buffer=len(entries)
        #log('entries to buffer reduced to %d' %entries_to_buffer )

    #if type.endswith("_RANDOM"):
    #    random.shuffle(entries)

    #for title, url in entries:
    #    log("  added to playlist:"+ title + "  " + url )

    log("**********autoPlay*************")

    for e in entries:
        q.put(e)


    
    #s= AppleTVLikeScreensaver(ev,q)
    #s= TableDropScreensaver(ev,q)
    #s= HorizontalSlideScreensaver(ev,q)
    s= ScreensaverManager(ev,q)
    
    #s.start_loop()
    try:
        s.start_loop()
    except Exception as e: 
        log("  EXCEPTION slideshowAlbum:="+ str( sys.exc_info()[0]) + "  " + str(e) )    

    s.close()
    del s
    sys.modules.clear()
    
    
    return


### credit to https://github.com/dersphere/script.screensaver.multi_slideshow for this code
#
#
CHUNK_WAIT_TIME = 250
ACTION_IDS_EXIT = [9, 10, 13, 92]
ACTION_IDS_PAUSE = [12,68,79,229]   #ACTION_PAUSE = 12  ACTION_PLAY = 68  ACTION_PLAYER_PLAY = 79   ACTION_PLAYER_PLAYPAUSE = 229


class ScreensaverWindow(WindowDialog):
    def __init__(self, exit_callback):
        self.exit_callback = exit_callback
        #log('  #####%d ' %  self.getResolution())
 
    def onAction(self, action):
        action_id = action.getId()
        if action_id in ACTION_IDS_EXIT:
            self.exit_callback()

class ScreensaverXMLWindow(WindowXMLDialog):

        #WindowXMLDialog.__init__(xmlfilename, scriptPath)
        #self.exit_callback = exit_callback
        #WindowXMLDialog.__init__( "xmlfilename", "scriptPath" )

        #log('  #####%d ' %  self.getResolution())

    def __init__(self, *args, **kwargs):
        WindowXMLDialog.__init__(self, *args, **kwargs)
        #xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)   
        self.exit_callback = kwargs.get("exit_callback")
        #self.subreddits_file = kwargs.get("exit_callback")
        

    def onAction(self, action):
        action_id = action.getId()
        self.exit_callback(action_id)
#         if action_id in ACTION_IDS_EXIT:
#             self.exit_callback(action_id)


class ScreensaverBase(object):

    MODE = None
    IMAGE_CONTROL_COUNT = 10
    FAST_IMAGE_COUNT = 0
    NEXT_IMAGE_TIME = 2000
    BACKGROUND_IMAGE = 'srr_blackbg.jpg'
    
    pause_requested=False

    def __init__(self, thread_event, image_queue):
        #self.log('__init__ start')
        self.exit_requested = False
        self.background_control = None
        self.preload_control = None
        self.image_count = 0
        #self.image_controls = []
        self.tni_controls = []
        self.global_controls = []
        self.exit_monitor = ExitMonitor(self.stop)
        
        self.init_xbmc_window()
#         self.xbmc_window = ScreensaverWindow(self.stop)
#         self.xbmc_window.show()
        
        self.init_global_controls()
        self.load_settings()
        self.init_cycle_controls()
        self.stack_cycle_controls()
        #self.log('__init__ end')
    
    def init_xbmc_window(self):
        self.xbmc_window = ScreensaverWindow(self.stop)
        self.xbmc_window.show()
        

    def init_global_controls(self):
        #self.log('  init_global_controls start')
        
        loading_img = xbmc.validatePath('/'.join((ADDON_PATH, 'resources', 'skins', 'Default', 'media', 'srr_busy.gif' )))
        
        self.loading_control = ControlImage(576, 296, 128, 128, loading_img)
        self.preload_control = ControlImage(-1, -1, 1, 1, '')
        self.background_control = ControlImage(0, 0, 1280, 720, '')
        self.global_controls = [
            self.preload_control, self.background_control, self.loading_control
        ]
        self.xbmc_window.addControls(self.global_controls)
        #self.log('  init_global_controls end')

    def load_settings(self):
        pass

    def init_cycle_controls(self):
        #self.log('  init_cycle_controls start')
        for i in xrange(self.IMAGE_CONTROL_COUNT):
            img_control = ControlImage(0, 0, 0, 0, '', aspectRatio=2)  #(values 0 = stretch (default), 1 = scale up (crops), 2 = scale down (black bars)
            txt_control = ControlTextBox(0, 0, 0, 0, font='font16')
#                     xbfont_left = 0x00000000
#                     xbfont_right = 0x00000001
#                     xbfont_center_x = 0x00000002
#                     xbfont_center_y = 0x00000004
#                     xbfont_truncated = 0x00000008
            #ControlLabel(x, y, width, height, label, font=None, textColor=None, disabledColor=None, alignment=0, hasPath=False, angle=0)
            #txt_control = ControlLabel(0, 0, 0, 0, '', font='font30', textColor='', disabledColor='', alignment=6, hasPath=False, angle=0)
            
            #self.image_controls.append(img_control)
            self.tni_controls.append([txt_control,img_control])
        #self.log('  init_cycle_controls end')

    def stack_cycle_controls(self):
        #self.log('stack_cycle_controls start')
        # add controls to the window in same order as image_controls list
        # so any new image will be in front of all previous images
        #self.xbmc_window.addControls(self.image_controls)
        #self.xbmc_window.addControls(self.text_controls)

        self.xbmc_window.addControls(self.tni_controls[1])
        self.xbmc_window.addControls(self.tni_controls[0])
        
        #self.log('stack_cycle_controls end')

    def start_loop(self):
        self.log('start_loop start')
        
        #images = self.get_images('q')
        desc_and_images = self.get_description_and_images('q')
        
        #if addon.getSetting('random_order') == 'true':
        #    random.shuffle(images)
        desc_and_images_cycle=cycle(desc_and_images)
        
        #image_url_cycle = cycle(images)
        #image_controls_cycle = cycle(self.image_controls)
        tni_controls_cycle= cycle(self.tni_controls)

        #self.log('  image_url_cycle %s' % image_url_cycle)
        
        
        self.hide_loading_indicator()
        
        #pops the first one
        #image_url = image_url_cycle.next()
        desc_and_image=desc_and_images_cycle.next()
        #self.log('  image_url_cycle.next %s' % image_url)
        
        #get the current screen saver value
        saver_mode = json.loads(  xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 0, "method": "Settings.getSettingValue", "params": {"setting":"screensaver.mode" } }')  ) 
        saver_mode = saver_mode.get('result').get('value')       
        #log('****screensavermode=' + repr(saver_mode) )
        #set the screensaver to none
        xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 0, "method":"Settings.setSettingValue", "params": {"setting":"screensaver.mode", "value":""} } ' )
        
        while not self.exit_requested:
            self.log('  using image: %s ' % ( repr(desc_and_image ) ) )


            if not self.pause_requested:            
                #pops an image control
                #image_control = image_controls_cycle.next()
                tni_control = tni_controls_cycle.next()
                
                #process_image done by subclass( assign animation and stuff to image control ) 
                #self.process_image(image_control, image_url)
                #self.process_image(image_control, desc_and_image)
                self.process_image(tni_control, desc_and_image)
                
                #image_url = image_url_cycle.next()
                desc_and_image=desc_and_images_cycle.next()

            
            #self.wait()
            if self.image_count < self.FAST_IMAGE_COUNT:
                self.image_count += 1
            else:
                #self.preload_image(image_url)
                self.preload_image(desc_and_image[1])
                self.wait()
                
        self.log('start_loop end')
        
        #return the screensaver back
        xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 0, "method":"Settings.setSettingValue", "params": {"setting":"screensaver.mode", "value" : "%s"} }' % saver_mode )


    def get_description_and_images(self, source):
        #self.log('get_images2')
        self.image_aspect_ratio = 16.0 / 9.0

        images = []

        if source == 'image_folder':
            path = SlideshowCacheFolder  #addon.getSetting('image_path')
            if path:
                images = self._get_folder_images(path)
        elif source == 'q':
            #implement width & height extract here.
            images=[[item[0], item[1],item[2], item[3], ] for item in q.queue]
            #texts=[item[0] for item in q.queue]
            #for i in images: self.log('   image: %s' %i)
            #self.log('    %d images' % len(images))

        return images


    #for movie, audio or tv shows
    def _get_json_images(self, method, key, prop):
        self.log('_get_json_images start')
        query = {
            'jsonrpc': '2.0',
            'id': 0,
            'method': method,
            'params': {
                'properties': [prop],
            }
        }
        response = json.loads(xbmc.executeJSONRPC(json.dumps(query)))
        images = [
            element[prop] for element
            in response.get('result', {}).get(key, [])
            if element.get(prop)
        ]
        self.log('_get_json_images end')
        return images

    def _get_folder_images(self, path):
        self.log('_get_folder_images started with path: %s' % repr(path))
        dirs, files = xbmcvfs.listdir(path)
        images = [
            xbmc.validatePath(path + f) for f in files
            if f.lower()[-3:] in ('jpg', 'png')
        ]
        #if addon.getSetting('recursive') == 'true':
        #    for directory in dirs:
        #        if directory.startswith('.'):
        #            continue
        #        images.extend(
        #            self._get_folder_images(
        #                xbmc.validatePath('/'.join((path, directory, '')))
        #            )
        #        )
        self.log('_get_folder_images ends')
        return images

    def hide_loading_indicator(self):
        bg_img = xbmc.validatePath('/'.join(( ADDON_PATH, 'resources', 'skins', 'Default', 'media', self.BACKGROUND_IMAGE )))
        #bg_img = self.BACKGROUND_IMAGE
        self.loading_control.setAnimations([(
            'conditional',
            'effect=fade start=100 end=0 time=500 condition=true'
        )])
        self.background_control.setAnimations([(
            'conditional',
            'effect=fade start=0 end=100 time=500 delay=500 condition=true'
        )])
        self.background_control.setImage(bg_img)

    def process_image(self, image_control, image_url):
        # Needs to be implemented in sub class
        raise NotImplementedError

    def preload_image(self, image_url):
        # set the next image to an unvisible image-control for caching
        #self.log('preloading image: %s' % repr(image_url))
        self.preload_control.setImage(image_url)
        #self.log('preloading done')

    def wait(self):
        # wait in chunks of 500ms to react earlier on exit request
        chunk_wait_time = int(CHUNK_WAIT_TIME)
        remaining_wait_time = int(self.NEXT_IMAGE_TIME)
        while remaining_wait_time > 0:
            if self.exit_requested:
                self.log('wait aborted')
                return
            if remaining_wait_time < chunk_wait_time:
                chunk_wait_time = remaining_wait_time
            remaining_wait_time -= chunk_wait_time
            xbmc.sleep(chunk_wait_time)

    def action_id_handler(self,action_id):
        #log('  action ID:' + str(action_id) )
        if action_id in ACTION_IDS_EXIT:
            #self.exit_callback()
            self.stop()
        if action_id in ACTION_IDS_PAUSE:  
            self.pause()          
            

    def stop(self,action_id=0):
        self.log('stop')
        self.exit_requested = True
        self.exit_monitor = None

    def pause(self):
        #pause disabled. too complicated(not possible?) to stop animation  
        #self.pause_requested = not self.pause_requested
        #self.log('pause %s' %self.pause_requested )
        pass

    def close(self):
        self.del_controls()

    def del_controls(self):
        #self.log('del_controls start')
        #self.xbmc_window.removeControls(self.img_controls)  
        try: self.xbmc_window.removeControls(self.tni_controls[0]) #imageControls
        except: pass
        try: self.xbmc_window.removeControls(self.tni_controls[1]) #textBoxes
        except: pass
        
        self.xbmc_window.removeControls(self.global_controls)
        self.preload_control = None
        self.background_control = None
        self.loading_control = None
        self.tni_controls = []
        self.global_controls = []
        self.xbmc_window.close()
        self.xbmc_window = None
        #self.log('del_controls end')

    def log(self, msg):
        log(u'slideshow: %s' % msg)

    

class HorizontalSlideScreensaver2(ScreensaverBase):

    MODE = 'Fade2'
    BACKGROUND_IMAGE = 'srr_blackbg.jpg'
    IMAGE_CONTROL_COUNT = 35
    FAST_IMAGE_COUNT = 0
    DISTANCE_RATIO = 0.7
    SPEED = 1.0
    CONCURRENCY = 1.0
    #SCREEN = 0

    def init_xbmc_window(self):
        #self.xbmc_window = ScreensaverWindow(  exit_callback=self.stop )          
        self.xbmc_window = ScreensaverXMLWindow( "slideshow01.xml", addon_path, defaultSkin='Default', exit_callback=self.stop )
        self.xbmc_window.setCoordinateResolution(5)
        self.xbmc_window.show()

    def load_settings(self):
        self.SPEED = float(addon.getSetting('slideshow_speed'))
        self.CONCURRENCY = 1.0 #float(addon.getSetting('appletvlike_concurrency'))
        self.MAX_TIME = int(30000 / self.SPEED)  #int(15000 / self.SPEED)
        self.NEXT_IMAGE_TIME =  int(6000.0 / self.SPEED)
        
    def stack_cycle_controls(self):
        # randomly generate a zoom in percent as betavariant
        # between 10 and 70 and assign calculated width to control.
        # Remove all controls from window and re-add sorted by size.
        # This is needed because the bigger (=nearer) ones need to be in front
        # of the smaller ones.
        # Then shuffle image list again to have random size order.

#         for image_control in self.image_controls:
#             zoom = int(random.betavariate(2, 2) * 40) + 10
#             #zoom = int(random.randint(10, 70))
#             width = 1280 / 100 * zoom
#             image_control.setWidth(width)
#         self.image_controls = sorted(
#             self.image_controls, key=lambda c: c.getWidth()
#         )
#         self.xbmc_window.addControls(self.image_controls)
#         random.shuffle(self.image_controls)


#         for image_control in self.image_controls:
# #             zoom = int(random.betavariate(2, 2) * 40) + 10
#             width  = 1280
#             height = 720    #1280 / 100 * zoom
#             image_control.setHeight(height)
#             image_control.setWidth(width)
            
            
#         self.image_controls = sorted(
#             self.image_controls, key=lambda c: c.getWidth()
#         )
#         self.xbmc_window.addControls(self.image_controls)
#         random.shuffle(self.image_controls)
        
        #self.xbmc_window.addControls(self.tni_controls[0])
        #self.xbmc_window.addControls(self.tni_controls[1])
        for txt_ctl, img_ctl in self.tni_controls:
            self.xbmc_window.addControl(img_ctl)

        self.txt_background=ControlImage(720, 0, 560, 720, 'srr_dialog-bg.png', aspectRatio=1)
        self.xbmc_window.addControl( self.txt_background  )
        
        for txt_ctl, img_ctl in self.tni_controls:
            self.xbmc_window.addControl(txt_ctl)
                        

    def process_image(self, tni_control, desc_and_image):

        MOVE_ANIMATION = (
            'effect=slide start=1280,0 end=-1280,0 center=auto time=%s '
            'tween=circle easing=out delay=0 condition=true'
        )

        FADE_ANIMATION = (
            'effect=fade delay=10 time=4000 '
            'tween=linear easing=out condition=true'
        )
        
        image_control=tni_control[1]
        text_control=tni_control[0]
        
        
        image_control.setVisible(False)
        image_control.setImage('')
        text_control.setVisible(False)
        text_control.setText('')
        
        self.txt_background.setVisible(False)  
        self.txt_background.setImage('')

        time = self.MAX_TIME #/ zoom * self.DISTANCE_RATIO * 100   #30000

        animations = [
            ('conditional', MOVE_ANIMATION % time)
        ]
        # set all parameters and properties

        #labels can have text centered but can't have multiline
        #textbox can have multiline but not centered text... what to do...
        #setLabel(self, label='', font=None, textColor=None, disabledColor=None, shadowColor=None, focusedColor=None, label2=''):
        text_control.setText(desc_and_image[0])
        text_control.setPosition(730, 0)
        text_control.setWidth(540)
        text_control.setHeight(720)
        text_control.setAnimations(  [('conditional', 'condition=true effect=fade delay=0 time=500 start=0 end=100  ' ), 
                                      ('conditional', 'condition=true effect=fade delay=%s time=1000 start=100 end=0 tween=circle easing=in' % self.NEXT_IMAGE_TIME  ) ]  )
        text_control.setVisible(True)
#       

        image_control.setImage(desc_and_image[1])
        image_control.setPosition(0, 0)
        image_control.setWidth(1280)   #16:9
        #image_control.setWidth(1680)    #21:9  
        image_control.setHeight(720)
        image_control.setAnimations(animations)
        # show the image
        image_control.setVisible(True)


#         c=self.xbmc_window.getControl(101)
#         #log('    **' +c.getText() )
#         c.setText( desc_and_image[0] )
#         cy=c.getY()
#         #c.setPosition( 0, cy+10 )
#         self.xbmc_window.removeControl(c)   #graaaahhhh!!! won't work. access violation!
#         self.xbmc_window.addControl(c)


        self.txt_background.setImage('srr_dlg-bg.png')
        #self.txt_background.setPosition(0, 0)
        # re-stack it (to be on top)
        #self.xbmc_window.removeControl(self.txt_background)
        #self.xbmc_window.addControl(self.txt_background)
        #self.txt_background.setColorDiffuse('0xCCCCCCCC') 
        self.txt_background.setVisible(True)  



class HorizontalSlideScreensaver(ScreensaverBase):

    MODE = 'slideLeft'
    BACKGROUND_IMAGE = 'srr_blackbg.jpg'
    IMAGE_CONTROL_COUNT = 35
    FAST_IMAGE_COUNT = 0
    DISTANCE_RATIO = 0.7
    SPEED = 1.0
    CONCURRENCY = 1.0
    #SCREEN = 0
    IMAGE_ANIMATIONS = [ ]

    TEXT_ANIMATIONS= [ ] 

    def load_settings(self):
        self.SPEED = float(addon.getSetting('slideshow_speed'))
        self.SHOW_TITLE = addon.getSetting('show_title') == 'true'
        
        self.CONCURRENCY = 1.0 #float(addon.getSetting('appletvlike_concurrency'))
        self.MAX_TIME = int(30000 / self.SPEED)  #int(15000 / self.SPEED)
        self.NEXT_IMAGE_TIME =  int(6000.0 / self.SPEED)

        self.IMAGE_ANIMATIONS = [
                ('conditional', 'effect=slide start=1280,0 end=-1280,0 center=auto time=%s '
                                'tween=circle easing=out delay=0 condition=true' % self.MAX_TIME),
            ]
    
        self.TEXT_ANIMATIONS= [
                ('conditional', 'condition=true effect=fade delay=0 time=500 start=0 end=100  ' ), 
                ('conditional', 'condition=true effect=fade delay=%s time=500 start=100 end=0 tween=circle easing=in' % self.NEXT_IMAGE_TIME  ) ] 


    #using WindowXMLDialog(ScreensaverXMLWindow) instead of WindowDialog. the image used in text background does not load when using WindowDialog (???)  some images load, most don't  
    def init_xbmc_window(self):
        #self.xbmc_window = ScreensaverWindow(  exit_callback=self.stop )          
        self.xbmc_window = ScreensaverXMLWindow( "slideshow01.xml", addon_path, defaultSkin='Default', exit_callback=self.action_id_handler )
        self.xbmc_window.setCoordinateResolution(5)
        self.xbmc_window.show()

        
    def stack_cycle_controls(self):
        # randomly generate a zoom in percent as betavariant
        # between 10 and 70 and assign calculated width to control.
        # Remove all controls from window and re-add sorted by size.
        # This is needed because the bigger (=nearer) ones need to be in front
        # of the smaller ones.
        # Then shuffle image list again to have random size order.

#         for image_control in self.image_controls:
#             zoom = int(random.betavariate(2, 2) * 40) + 10
#             #zoom = int(random.randint(10, 70))
#             width = 1280 / 100 * zoom
#             image_control.setWidth(width)
#         self.image_controls = sorted(
#             self.image_controls, key=lambda c: c.getWidth()
#         )
#         self.xbmc_window.addControls(self.image_controls)
#         random.shuffle(self.image_controls)


#         for image_control in self.image_controls:
# #             zoom = int(random.betavariate(2, 2) * 40) + 10
#             width  = 1280
#             height = 720    #1280 / 100 * zoom
#             image_control.setHeight(height)
#             image_control.setWidth(width)
            
            
#         self.image_controls = sorted(
#             self.image_controls, key=lambda c: c.getWidth()
#         )
#         self.xbmc_window.addControls(self.image_controls)
#         random.shuffle(self.image_controls)
        
        #self.xbmc_window.addControls(self.tni_controls[0])
        #self.xbmc_window.addControls(self.tni_controls[1])
            
        for txt_ctl, img_ctl in self.tni_controls:
            self.xbmc_window.addControl(img_ctl)

        if self.SHOW_TITLE:
            self.txt_background=ControlImage(0, 685, 1280, 40, 'srr_dialog-bg.png', aspectRatio=1)
            self.xbmc_window.addControl( self.txt_background  )
        
            #ControlLabel(x, y, width, height, label, font=None, textColor=None, disabledColor=None, alignment=0, hasPath=False, angle=0)
            self.image_label=ControlLabel(10,683,1280,40,'',font='font16', textColor='', disabledColor='', alignment=6, hasPath=False, angle=0)
            self.xbmc_window.addControl( self.image_label  )
        #for txt_ctl, img_ctl in self.tni_controls:
        #    self.xbmc_window.addControl(txt_ctl)

    def process_image(self, tni_control, desc_and_image):
        image_control=tni_control[1]
        text_control=tni_control[0]
        
        image_control.setVisible(False)
        image_control.setImage('')
        text_control.setVisible(False)
        text_control.setText('')
        
        #self.image_label.setVisible(False)
        #self.image_label.setLabel('')
        if self.SHOW_TITLE:
            self.txt_background.setVisible(False)  
            self.txt_background.setImage('')

        #time = self.MAX_TIME #/ zoom * self.DISTANCE_RATIO * 100   #30000

        # set all parameters and properties

        #labels can have text centered but can't have multiline
        #textbox can have multiline but not centered text... what to do...
        #setLabel(self, label='', font=None, textColor=None, disabledColor=None, shadowColor=None, focusedColor=None, label2=''):

        if self.SHOW_TITLE:
            
            if self.image_label.getLabel() == desc_and_image[0]:  #avoid animating the same text label if previous one is the same
                self.image_label.setAnimations( [ ('conditional', 'condition=true effect=fade delay=0 time=0 start=100 end=100  ' ) ]  )
            else:
                self.image_label.setAnimations( self.TEXT_ANIMATIONS )

            if desc_and_image[0]:  
                self.image_label.setLabel(desc_and_image[0])
                self.image_label.setVisible(True)
                
                self.txt_background.setImage('srr_dlg-bg.png')
                self.txt_background.setVisible(True)  
            else:   #don't show text and text_background if no text 
                self.image_label.setVisible(False)
                self.txt_background.setVisible(False)
                
    #             text_control.setText(desc_and_image[0])
    #             text_control.setPosition(10, 685)
    #             text_control.setWidth(1280)
    #             text_control.setHeight(40)
    #             text_control.setAnimations( self.TEXT_ANIMATIONS )
    #             text_control.setVisible(True)
    #         


        image_control.setImage(desc_and_image[1])
        image_control.setPosition(0, 0)
        image_control.setWidth(1280)   #16:9
        #image_control.setWidth(1680)    #21:9  
        image_control.setHeight(720)
        image_control.setAnimations(self.IMAGE_ANIMATIONS)
        # show the image
        image_control.setVisible(True)

class FadeScreensaver( HorizontalSlideScreensaver, ScreensaverBase):
    MODE = 'Fade'
    
    def load_settings(self):
        self.SPEED = float(addon.getSetting('slideshow_speed'))
        self.SHOW_TITLE = addon.getSetting('show_title') == 'true'
        
        self.CONCURRENCY = 1.0 #float(addon.getSetting('appletvlike_concurrency'))
        self.MAX_TIME = int(30000 / self.SPEED)  #int(15000 / self.SPEED)
        self.NEXT_IMAGE_TIME =  int(6000.0 / self.SPEED)

        self.IMAGE_ANIMATIONS = [
                ('conditional', 'effect=fade start=0 end=100 center=auto time=%s '
                                'tween=back  delay=0 condition=true' % self.NEXT_IMAGE_TIME),
                ('conditional', 'effect=fade start=100 end=0 center=auto time=500 '
                                'tween=linear            delay=%s condition=true' %(self.NEXT_IMAGE_TIME+1000) ),
            ]
    
        self.TEXT_ANIMATIONS= [
                ('conditional', 'condition=true effect=fade delay=0 time=500 start=0 end=100  ' ), 
                ('conditional', 'condition=true effect=fade delay=%s time=500 start=100 end=0 tween=circle easing=in' % self.NEXT_IMAGE_TIME  ) ] 

class AdaptiveSlideScreensaver( HorizontalSlideScreensaver, ScreensaverBase):
    MODE = 'SlideUDLR'

    def load_settings(self):
        self.SPEED = float(addon.getSetting('slideshow_speed'))
        self.SHOW_TITLE = addon.getSetting('show_title') == 'true'
        
        self.CONCURRENCY = 1.0 #float(addon.getSetting('appletvlike_concurrency'))
        self.MAX_TIME = int(36000 / self.SPEED)  #int(15000 / self.SPEED)
        self.NEXT_IMAGE_TIME =  int(12000.0 / self.SPEED)
    
    def process_image(self, tni_control, desc_and_image):
        image_control=tni_control[1]
        text_control=tni_control[0]

        width =desc_and_image[2] if desc_and_image[2] else 0
        height=desc_and_image[3] if desc_and_image[3] else 0
        if width>0 and height>0:
            ar=float(float(width)/height)
        else:
            ar=1.0
        
        image_control.setVisible(False)
        image_control.setImage('')
        text_control.setVisible(False)
        text_control.setText('')
        
        direction=random.choice([1,0])
        if ar < 0.85:
            up_down=True
        else:
            up_down=False
            
        #log('  %d  %dx%d %f' %(direction, width,height,ar ) )

        #default dimension of the image control        
        ctl_width=1680
        ctl_height=720

        if up_down:
            #with tall images, the image control dimension has to be tall 
            sx=0;ex=0
            sy=-1680;ey=720
            ctl_width=1280
            ctl_height=1680
        else:
            sx=1280;ex=-1680
            sy=0;ey=0

        if direction:
            sx,ex=ex,sx
            sy,ey=ey,sy
        
        slide_animation=[
            ('conditional', 'effect=slide start=%d,%d end=%d,%d center=auto time=%s '
                            'tween=cubic easing=out delay=0 condition=true' % ( sx,sy,ex,ey, self.MAX_TIME)),
        ]
            
        if self.SHOW_TITLE:
            self.txt_background.setVisible(False)  
            self.txt_background.setImage('')

        if self.SHOW_TITLE:
            
            if self.image_label.getLabel() == desc_and_image[0]:  #avoid animating the same text label if previous one is the same
                self.image_label.setAnimations( [ ('conditional', 'condition=true effect=fade delay=0 time=0 start=100 end=100  ' ) ]  )
            else:
                self.image_label.setAnimations( self.TEXT_ANIMATIONS )

            if desc_and_image[0]:  
                self.image_label.setLabel(desc_and_image[0])
                self.image_label.setVisible(True)
                
                self.txt_background.setImage('srr_dlg-bg.png')
                self.txt_background.setVisible(True)  
            else:   #don't show text and text_background if no text 
                self.image_label.setVisible(False)
                self.txt_background.setVisible(False)
                
        image_control.setImage(desc_and_image[1])
        image_control.setPosition(0, 0)
        image_control.setWidth(ctl_width)  
        image_control.setHeight(ctl_height)
        image_control.setAnimations(slide_animation)
        # show the image
        image_control.setVisible(True)


class TableDropScreensaver(ScreensaverBase):

    MODE = 'TableDrop'
    BACKGROUND_IMAGE = 'srr_blackbg.jpg'
    IMAGE_CONTROL_COUNT = 20
    FAST_IMAGE_COUNT = 0
    NEXT_IMAGE_TIME = 1500
    MIN_WIDTH = 500
    MAX_WIDTH = 700

    def load_settings(self):
        self.NEXT_IMAGE_TIME = 1500 #int(addon.getSetting('tabledrop_wait'))

    def process_image(self, image_control, image_url):
        ROTATE_ANIMATION = (
            'effect=rotate start=0 end=%d center=auto time=%d '
            'delay=0 tween=circle condition=true'
        )
        DROP_ANIMATION = (
            'effect=zoom start=%d end=100 center=auto time=%d '
            'delay=0 tween=circle condition=true'
        )
        FADE_ANIMATION = (
            'effect=fade start=0 end=100 time=200 '
            'condition=true'
        )
        # hide the image
        image_control.setVisible(False)
        image_control.setImage('')
        # re-stack it (to be on top)
        self.xbmc_window.removeControl(image_control)
        self.xbmc_window.addControl(image_control)
        # calculate all parameters and properties
        width = random.randint(self.MIN_WIDTH, self.MAX_WIDTH)
        height = int(width / self.image_aspect_ratio)
        x_position = random.randint(0, 1280 - width)
        y_position = random.randint(0, 720 - height)
        drop_height = random.randint(400, 800)
        drop_duration = drop_height * 1.5
        rotation_degrees = random.uniform(-20, 20)
        rotation_duration = drop_duration
        animations = [
            ('conditional', FADE_ANIMATION),
            ('conditional',
             ROTATE_ANIMATION % (rotation_degrees, rotation_duration)),
            ('conditional',
             DROP_ANIMATION % (drop_height, drop_duration)),
        ]
        # set all parameters and properties
        image_control.setImage(image_url[1])
        image_control.setPosition(x_position, y_position)
        image_control.setWidth(width)
        image_control.setHeight(height)
        image_control.setAnimations(animations)
        # show the image
        image_control.setVisible(True)


class StarWarsScreensaver(ScreensaverBase):

    MODE = 'StarWars'
    BACKGROUND_IMAGE = 'stars.jpg'
    IMAGE_CONTROL_COUNT = 6
    SPEED = 0.5

    def load_settings(self):
        self.SPEED = float(addon.getSetting('starwars_speed'))
        self.EFFECT_TIME = 9000.0 / self.SPEED
        self.NEXT_IMAGE_TIME = self.EFFECT_TIME / 7.6

    def process_image(self, image_control, image_url):
        TILT_ANIMATION = (
            'effect=rotatex start=0 end=55 center=auto time=0 '
            'condition=true'
        )
        MOVE_ANIMATION = (
            'effect=slide start=0,1280 end=0,-2560 time=%d '
            'tween=linear condition=true'
        )
        # hide the image
        image_control.setImage('')
        image_control.setVisible(False)
        # re-stack it (to be on top)
        self.xbmc_window.removeControl(image_control)
        self.xbmc_window.addControl(image_control)
        # calculate all parameters and properties
        width = 1280
        height = 720
        x_position = 0
        y_position = 0
        animations = [
            ('conditional', TILT_ANIMATION),
            ('conditional', MOVE_ANIMATION % self.EFFECT_TIME),
        ]
        # set all parameters and properties
        image_control.setPosition(x_position, y_position)
        image_control.setWidth(width)
        image_control.setHeight(height)
        image_control.setAnimations(animations)
        image_control.setImage(image_url)
        # show the image
        image_control.setVisible(True)


class RandomZoomInScreensaver(ScreensaverBase):

    MODE = 'RandomZoomIn'
    IMAGE_CONTROL_COUNT = 7
    NEXT_IMAGE_TIME = 2000
    EFFECT_TIME = 5000

    def load_settings(self):
        self.NEXT_IMAGE_TIME = 2000  # int(addon.getSetting('randomzoom_wait'))
        self.EFFECT_TIME = 5000      # int(addon.getSetting('randomzoom_effect'))

    def process_image(self, image_control, image_url):
        ZOOM_ANIMATION = (
            'effect=zoom start=1 end=100 center=%d,%d time=%d '
            'tween=quadratic condition=true'
        )
        # hide the image

        #ctl3=ControlImage(0, 0, 1920, 1080, image_url, aspectRatio=2)
        #self.xbmc_window.addControl(ctl3)
        
        image_control.setVisible(False)
        image_control.setImage('')
        # re-stack it (to be on top)
        self.xbmc_window.removeControl(image_control)
        self.xbmc_window.addControl(image_control)
        
        
        # calculate all parameters and properties
        width = 1280
        height = 720
        x_position = 0
        y_position = 0
        zoom_x = random.randint(0, 1280)
        zoom_y = random.randint(0, 720)
        animations = [
            ('conditional', ZOOM_ANIMATION % (zoom_x, zoom_y, self.EFFECT_TIME)),
        ]
        # set all parameters and properties
        image_control.setImage(image_url)
        image_control.setPosition(x_position, y_position)
        image_control.setWidth(width)
        image_control.setHeight(height)
        image_control.setAnimations(animations)
        # show the image
        image_control.setVisible(True)


class AppleTVLikeScreensaver(ScreensaverBase):

    MODE = 'AppleTVLike'
    IMAGE_CONTROL_COUNT = 35
    FAST_IMAGE_COUNT = 2
    DISTANCE_RATIO = 0.7
    SPEED = 1.0
    CONCURRENCY = 1.0
    #SCREEN = 0

    def load_settings(self):
        self.SPEED = 1.0 #float(addon.getSetting('appletvlike_speed'))
        self.CONCURRENCY = 1.0 #float(addon.getSetting('appletvlike_concurrency'))
        self.MAX_TIME = int(15000 / self.SPEED)
        self.NEXT_IMAGE_TIME = int(4500.0 / self.CONCURRENCY / self.SPEED)

    def stack_cycle_controls(self):
        # randomly generate a zoom in percent as betavariant
        # between 10 and 70 and assign calculated width to control.
        # Remove all controls from window and re-add sorted by size.
        # This is needed because the bigger (=nearer) ones need to be in front
        # of the smaller ones.
        # Then shuffle image list again to have random size order.

        for image_control in self.image_controls:
            zoom = int(random.betavariate(2, 2) * 40) + 10
            #zoom = int(random.randint(10, 70))
            width = 1280 / 100 * zoom
            image_control.setWidth(width)
        self.image_controls = sorted(
            self.image_controls, key=lambda c: c.getWidth()
        )
        self.xbmc_window.addControls(self.image_controls)
        random.shuffle(self.image_controls)

    def process_image(self, image_control, image_url):
        MOVE_ANIMATION = (
            'effect=slide start=0,720 end=0,-720 center=auto time=%s '
            'tween=linear delay=0 condition=true'
        )
        image_control.setVisible(False)
        image_control.setImage('')
        # calculate all parameters and properties based on the already set
        # width. We can not change the size again because all controls need
        # to be added to the window in size order.
        width = image_control.getWidth()
        zoom = width * 100 / 1280
        height = int(width / self.image_aspect_ratio)
        # let images overlap max 1/2w left or right
        center = random.randint(0, 1280)
        x_position = center - width / 2
        y_position = 0

        time = self.MAX_TIME / zoom * self.DISTANCE_RATIO * 100

        animations = [
            ('conditional', MOVE_ANIMATION % time),
        ]
        # set all parameters and properties
        image_control.setImage(image_url[1])
        image_control.setPosition(x_position, y_position)
        image_control.setWidth(width)
        image_control.setHeight(height)
        image_control.setAnimations(animations)
        # show the image
        image_control.setVisible(True)


class GridSwitchScreensaver(ScreensaverBase):

    MODE = 'GridSwitch'

    ROWS_AND_COLUMNS = 4
    NEXT_IMAGE_TIME = 1000
    EFFECT_TIME = 500
    RANDOM_ORDER = False

    IMAGE_CONTROL_COUNT = ROWS_AND_COLUMNS ** 2
    FAST_IMAGE_COUNT = IMAGE_CONTROL_COUNT

    def load_settings(self):
        self.NEXT_IMAGE_TIME = int(addon.getSetting('gridswitch_wait'))
        self.ROWS_AND_COLUMNS = int(addon.getSetting('gridswitch_rows_columns'))
        self.RANDOM_ORDER = addon.getSetting('gridswitch_random') == 'true'
        self.IMAGE_CONTROL_COUNT = self.ROWS_AND_COLUMNS ** 2
        self.FAST_IMAGE_COUNT = self.IMAGE_CONTROL_COUNT

    def stack_cycle_controls(self):
        # Set position and dimensions based on stack position.
        # Shuffle image list to have random order.
        super(GridSwitchScreensaver, self).stack_cycle_controls()
        for i, image_control in enumerate(self.image_controls):
            current_row, current_col = divmod(i, self.ROWS_AND_COLUMNS)
            width = 1280 / self.ROWS_AND_COLUMNS
            height = 720 / self.ROWS_AND_COLUMNS
            x_position = width * current_col
            y_position = height * current_row
            image_control.setPosition(x_position, y_position)
            image_control.setWidth(width)
            image_control.setHeight(height)
        if self.RANDOM_ORDER:
            random.shuffle(self.image_controls)

    def process_image(self, image_control, image_url):
        if not self.image_count < self.FAST_IMAGE_COUNT:
            FADE_OUT_ANIMATION = (
                'effect=fade start=100 end=0 time=%d condition=true' % self.EFFECT_TIME
            )
            animations = [
                ('conditional', FADE_OUT_ANIMATION),
            ]
            image_control.setAnimations(animations)
            xbmc.sleep(self.EFFECT_TIME)
        image_control.setImage(image_url)
        FADE_IN_ANIMATION = (
            'effect=fade start=0 end=100 time=%d condition=true' % self.EFFECT_TIME
        )
        animations = [
            ('conditional', FADE_IN_ANIMATION),
        ]
        image_control.setAnimations(animations)


class ExitMonitor(xbmc.Monitor):

    def __init__(self, exit_callback):
        self.exit_callback = exit_callback

    def onScreensaverDeactivated(self):
        self.exit_callback()


MODES = (
    'slideLeft',
    'Fade',
    'SlideUDLR',
    'Random',
)
class ScreensaverManager(object):

    def __new__(cls, ev, q):
        mode = MODES[int(addon.getSetting('slideshow_mode'))]
        if mode == 'Random':
            subcls = random.choice(ScreensaverBase.__subclasses__( ))
            return subcls( ev, q)
        for subcls in ScreensaverBase.__subclasses__():
            #log('  mode:%s subclass:%s' %( mode, subcls.__name__ ))
            if subcls.MODE == mode:
                return subcls( ev, q)
            
        raise ValueError('Not a valid ScreensaverBase subclass: %s' % mode)


def cycle(iterable):
    saved = []
    for element in iterable:
        yield element
        saved.append(element)
    while saved:
        for element in saved:
            yield element

if __name__ == '__main__':
     
    #RunAddon(script.reddit.reader,mode=autoSlideshow&url=https%3A%2F%2Fwww.reddit.com%2F.json%3F%26nsfw%3Ano%2B%26limit%3D10&name=&type=)
 
    #autoSlideshow('https://www.reddit.com/.json?nsfw=no&limit=10','','')
 
    sys.modules.clear()

