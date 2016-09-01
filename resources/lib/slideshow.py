import xbmc
import json
import xbmcvfs
import random

from xbmcgui import ControlImage, WindowDialog, Window, ControlTextBox, ControlLabel

#autoSlideshow

from default import log, translation, addon_path, addonID,SlideshowCacheFolder
import threading
from Queue import Queue, Empty

ADDON_NAME = addonID      #addon.getAddonInfo('name')  <--changed to id
ADDON_PATH = addon_path   #addon.getAddonInfo('path')  

q=Queue()

def autoSlideshow(url, name, type):
    from domains import sitesBase, parse_reddit_link
    from utils import unescape, post_excluded_from, determine_if_video_media_from_reddit_json, remove_duplicates
    from default import reddit_request, getPlayCount
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
            #log("  Title:%s -%c"  %( title, ("v" if is_a_video else " ") ) )
            
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

            is_a_video = determine_if_video_media_from_reddit_json(j_entry) 

#             hoster, DirectoryItem_url, processed_media_url, modecommand, thumb_url,poster_url, isFolder,setInfo_type, IsPlayable=make_addon_url_from(media_url=media_url, 
#                                                                                                                                                      assume_is_video=is_a_video, 
#                                                                                                                                                      needs_thumbnail=True,
#                                                                                                                                                      preview_url='',
#                                                                                                                                                      get_playable_url=False )  #we resolve the playable url

 
#             if DirectoryItem_url:
#                 #log('   type:'+ setInfo_type)
#                 if setInfo_type in ['pictures','album']:
#                     entries.append([title,processed_media_url,modecommand])
            
            if preview:
                log('  added preview:%s' % title )
                entries.append([title,preview,preview_w, preview_h,len(entries)])
            else:
                ld=parse_reddit_link(link_url=media_url, assume_is_video=False, needs_preview=True, get_playable_url=True )
                if ld:
                    if ld.poster:
                        log('  added b poster:%s' % title )
                        entries.append([title, ld.poster, ld.poster_w, ld.poster_h, len(entries)])
                
            
                    
                
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
    s= HorizontalSlideScreensaver(ev,q)
    s.start_loop()
    return


### credit to https://github.com/dersphere/script.screensaver.multi_slideshow for this code
#
#
CHUNK_WAIT_TIME = 250
ACTION_IDS_EXIT = [9, 10, 13, 92]

class ScreensaverWindow(WindowDialog):

    def __init__(self, exit_callback):
        self.exit_callback = exit_callback
        #log('  #####%d ' %  self.getResolution())

    def onAction(self, action):
        action_id = action.getId()
        if action_id in ACTION_IDS_EXIT:
            self.exit_callback()

class ScreensaverBase(object):

    MODE = None
    IMAGE_CONTROL_COUNT = 10
    FAST_IMAGE_COUNT = 0
    NEXT_IMAGE_TIME = 2000
    BACKGROUND_IMAGE = 'srr_blackbg.jpg'

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
        
        self.xbmc_window = ScreensaverWindow(self.stop)
        self.xbmc_window.show()
        
        self.init_global_controls()
        self.load_settings()
        self.init_cycle_controls()
        self.stack_cycle_controls()
        #self.log('__init__ end')

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
            txt_control = ControlTextBox(0, 0, 0, 0, font='font30')
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
        
        while not self.exit_requested:
            self.log('  using image: %s ' % ( repr(desc_and_image ) ) )
            
            #pops an image control
            #image_control = image_controls_cycle.next()
            tni_control   = tni_controls_cycle.next()
            
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


    def get_images(self, source):
        #self.log('get_images')
        self.image_aspect_ratio = 16.0 / 9.0
        #source = SOURCES[int(addon.getSetting('source'))]
        #prop = PROPS[int(addon.getSetting('prop'))]
        images = []
        texts = []
        #if source == 'movies':
        #    images = self._get_json_images('VideoLibrary.GetMovies', 'movies', prop)
        #elif source == 'albums':
        #    images = self._get_json_images('AudioLibrary.GetAlbums', 'albums', prop)
        #elif source == 'shows':
        #    images = self._get_json_images('VideoLibrary.GetTVShows', 'tvshows', prop)
        
        if source == 'image_folder':
            path = SlideshowCacheFolder  #addon.getSetting('image_path')
            if path:
                images = self._get_folder_images(path)
        elif source == 'q':
            images=[item[1] for item in q.queue]
            texts=[item[0] for item in q.queue]
            #for i in images: self.log('   image: %s' %i)
            #self.log('    %d images' % len(images))


                
#         if not images:
#             cmd = 'XBMC.Notification("{header}", "{message}")'.format(
#                 header=addon.getLocalizedString(32500),
#                 message=addon.getLocalizedString(32501)
#             )
#             xbmc.executebuiltin(cmd)
#             images = (
#                 self._get_json_images('VideoLibrary.GetMovies', 'movies', 'fanart')
#                 or self._get_json_images('AudioLibrary.GetArtists', 'artists', 'fanart')
#             )
#         if not images:
#             raise NoImagesException
        
        return images

    def get_description_and_images(self, source):
        #self.log('get_images2')
        self.image_aspect_ratio = 16.0 / 9.0

        images = []

        if source == 'image_folder':
            path = SlideshowCacheFolder  #addon.getSetting('image_path')
            if path:
                images = self._get_folder_images(path)
        elif source == 'q':
            images=[[item[0], item[1]] for item in q.queue]
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

    def stop(self):
        self.log('stop')
        self.exit_requested = True
        self.exit_monitor = None

    def close(self):
        self.del_controls()

    def del_controls(self):
        self.log('del_controls start')
        self.xbmc_window.removeControls(self.image_controls)
        self.xbmc_window.removeControls(self.global_controls)
        self.preload_control = None
        self.background_control = None
        self.loading_control = None
        self.image_controls = []
        self.global_controls = []
        self.xbmc_window.close()
        self.xbmc_window = None
        self.log('del_controls end')

    def log(self, msg):
        log(u'slideshow: %s' % msg)


class HorizontalSlideScreensaver(ScreensaverBase):

    MODE = 'HorizontalSlide'
    BACKGROUND_IMAGE = 'srr_blackbg.jpg'
    IMAGE_CONTROL_COUNT = 35
    FAST_IMAGE_COUNT = 0
    DISTANCE_RATIO = 0.7
    SPEED = 1.0
    CONCURRENCY = 1.0
    #SCREEN = 0

    def load_settings(self):
        self.SPEED = 2 #float(addon.getSetting('appletvlike_speed'))
        self.CONCURRENCY = 1.0 #float(addon.getSetting('appletvlike_concurrency'))
        self.MAX_TIME = int(15000 / self.SPEED)
        self.NEXT_IMAGE_TIME =  5000 #int(4500.0 / self.CONCURRENCY / self.SPEED)
        

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
            self.xbmc_window.addControl(txt_ctl)
            

    def process_image(self, tni_control, desc_and_image):
#         MOVE_ANIMATION = (
#             'effect=slide start=1920,0 end=-1920,0 center=auto time=%s '
#             'tween=linear delay=0 condition=true'
#         )
        MOVE_ANIMATION = (
            'effect=slide start=1280,0 end=-1280,0 center=auto time=%s '
            'tween=circle easing=out delay=0 condition=true'
        )
        image_control=tni_control[1]
        text_control=tni_control[0]
        
        image_control.setVisible(False)
        image_control.setImage('')
        text_control.setText('')

        time = 30000 #self.MAX_TIME #/ zoom * self.DISTANCE_RATIO * 100

        animations = [
            ('conditional', MOVE_ANIMATION % time),
        ]
        # set all parameters and properties

        #labels can have text centered but can't have multiline
        #textbox can have multiline but not centered text... what to do...
        #setLabel(self, label='', font=None, textColor=None, disabledColor=None, shadowColor=None, focusedColor=None, label2=''):
#         text_control.setText(desc_and_image[0])
#         text_control.setPosition(320, 550)
#         text_control.setWidth(640)
#         text_control.setHeight(220)
#         text_control.setAnimations(animations)
#         text_control.setVisible(True)
#         

        image_control.setImage(desc_and_image[1])
        image_control.setPosition(0, 0)
        image_control.setWidth(1280)
        image_control.setHeight(720)
        image_control.setAnimations(animations)
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

def cycle(iterable):
    saved = []
    for element in iterable:
        yield element
        saved.append(element)
    while saved:
        for element in saved:
            yield element
