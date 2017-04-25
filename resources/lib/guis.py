#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2012 Tristan Fischer (sphere@dersphere.de)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import os
import re
import sys
import urllib
import json

import xbmc
import xbmcaddon
import xbmcgui
from xbmcgui import ControlButton

from utils import build_script
#import xbmcplugin

addon = xbmcaddon.Addon()
addon_path = addon.getAddonInfo('path')
addon_name = addon.getAddonInfo('name')

def dump(obj):
    for attr in dir(obj):
        if hasattr( obj, attr ):
            log( "obj.%s = %s" % (attr, getattr(obj, attr)))

class ExitMonitor(xbmc.Monitor):
    def __init__(self, exit_callback):
        self.exit_callback = exit_callback

#     def onScreensaverDeactivated(self):
#         self.exit_callback()

    def abortRequested(self):
        self.exit_callback()

class contextMenu(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.listing = kwargs.get("listing")

        #log( str(args) )
        #log(sys.argv[1])

    def onInit(self):
        self.list_control=self.getControl(996)
        self.list_control.addItems(self.listing)
        pass

    def onAction(self, action):
        if action in [ xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK ]:
            self.close()

    def onClick(self, controlID):
        from reddit import assemble_reddit_filter_string

        selected_item=self.list_control.getSelectedItem()
        di_url=selected_item.getPath()
        xbmc.executebuiltin( di_url  )
        self.close()
        #dump(selected_item)

class cGUI(xbmcgui.WindowXML):
    # view_461_comments.xml
    include_parent_directory_entry=True
    title_bar_text=""
    gui_listbox_SelectedPosition=0

    #plot_font="a" #font used for 'plot' <- where the image or comment description is stored ### cannot set font size.
    #CONTROL_ID_FOR_PLOT_TEXTBOX=65591

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXML.__init__(self, *args, **kwargs)
        #xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)   #<--- what's the difference?
        self.subreddits_file = kwargs.get("subreddits_file")
        self.listing = kwargs.get("listing")
        self.main_control_id = kwargs.get("id")
        self.context_menu=kwargs.get("context_menu")

        #log( str(args) )
        #log(sys.argv[1])

    def onInit(self):
        xbmc.executebuiltin( "Dialog.Close(busydialog)" )
        self.gui_listbox = self.getControl(self.main_control_id)
        #important to reset the listbox. when control comes back to this GUI(after calling another gui).
        #  kodi will "onInit" this GUI again. we end up adding items in gui_listbox
        self.gui_listbox.reset()
        self.exit_monitor = ExitMonitor(self.close_gui)#monitors for abortRequested and calls close on the gui

        if self.title_bar_text:
            self.ctl_title_bar = self.getControl(1)
            self.ctl_title_bar.setLabel(self.title_bar_text)

        # will not work. 'xbmcgui.ControlTextBox' does not have methods to set font size
        # it might be possible to make the textbox control in code and addcontrol() it. but then you would have to figure out how to get text to change when listbox selection changes.
        #if self.plot_font:
        #    self.ctl_plot_textbox = self.getControl(self.CONTROL_ID_FOR_PLOT_TEXTBOX)
        #    self.ctl_plot_textbox.setLabel('Status', 'font14', '0xFFFFFFFF', '0xFFFF3300', '0xFF000000')

        #url="plugin://plugin.video.reddit_viewer/?url=plugin%3A%2F%2Fplugin.video.youtube%2Fplay%2F%3Fvideo_id%3D73lsIXzBar0&mode=playVideo"
        #url="http://i.imgur.com/ARdeL4F.mp4"
        if self.include_parent_directory_entry:
            if self.gui_listbox_SelectedPosition==0:
                self.gui_listbox_SelectedPosition=1 #skip the ".." as the first selected item
            back_image='DefaultFolderBackSquare.png'
            listitem = xbmcgui.ListItem(label='..', label2="", iconImage=back_image)
            #listitem.setInfo( type="Video", infoLabels={ "Title": '..', "plot": "", "studio": '' } )
            listitem.setArt({"thumb": back_image, "clearart": "DefaultFolderBackSquare.png"}) #, "poster":back_image, "banner":back_image, "fanart":back_image, "landscape":back_image   })

            listitem.setInfo(type='video', infoLabels={"Studio":".."})
            #liz.setProperty('link_url', nextUrl )

            #listitem.setPath(url)
            self.gui_listbox.addItem(listitem)

        self.gui_listbox.addItems(self.listing)
        self.setFocus(self.gui_listbox)

        if self.gui_listbox_SelectedPosition > 0:
            self.gui_listbox.selectItem( self.gui_listbox_SelectedPosition )

    def onClick(self, controlID):

        if controlID == self.main_control_id:
            self.gui_listbox_SelectedPosition = self.gui_listbox.getSelectedPosition()
            item = self.gui_listbox.getSelectedItem()

            if self.include_parent_directory_entry and self.gui_listbox_SelectedPosition == 0:
                self.close()  #include_parent_directory_entry means that we've added a ".." as the first item on the list onInit

            #name = item.getLabel()
            try:di_url=item.getProperty('onClick_action') #this property is created when assembling the kwargs.get("listing") for this class
            except:di_url=""
            item_type=item.getProperty('item_type').lower()

            log( "  clicked on %d IsPlayable=%s  url=%s " %( self.gui_listbox_SelectedPosition, item_type, di_url )   )
            if item_type=='playable':
                    #a big thank you to spoyser (http://forum.kodi.tv/member.php?action=profile&uid=103929) for this help
                    pl = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
                    pl.clear()
                    pl.add(di_url, item)
                    xbmc.Player().play(pl, windowed=False)
                    #self.close()
            elif item_type=='script':
                #"script.web.viewer, http://m.reddit.com/login"
                #log(  di_url )

                #xbmc.executebuiltin("ActivateWindow(busydialog)")
                #xbmc.executebuiltin( di_url  )
                #xbmc.sleep(5000)
                #xbmc.executebuiltin( "Dialog.Close(busydialog)" )

                self.busy_execute_sleep(di_url, 3000, close=False)   #note: setting close to false seems to cause kodi not to close properly (will wait on this thread)

                #modes=['listImgurAlbum','viewImage','listLinksInComment','playTumblr','playInstagram','playFlickr' ]
                #if any(x in di_url for x in modes):
                    #viewImage uses xml gui, xbmc.Player() sometimes report an error after 'play'-ing
                    #   use RunPlugin to avoid this issue



                #xbmcplugin.setResolvedUrl(self.pluginhandle, True, item)
                #xbmc.executebuiltin('RunPlugin(%s)' %di_url )  #works for showing image(with gui) but doesn't work for videos(Attempt to use invalid handle -1)
                #xbmc.executebuiltin('RunScript(%s)' %di_url )   #nothing works

                #xbmc.executebuiltin('RunAddon(plugin.video.reddit_viewer)'  ) #does nothing. adding the parameter produces error(unknown plugin)
                #xbmc.executebuiltin('ActivateWindow(video,%s)' %di_url )       #Can't find window video   ...#Activate/ReplaceWindow called with invalid destination window: video

        elif controlID == 5:
            pass
        elif controlID == 7:
            pass

    def load_subreddits_file_into_a_listitem(self):
        from utils import compose_list_item, prettify_reddit_query
        from reddit import parse_subreddit_entry, assemble_reddit_filter_string
        entries=[]
        listing=[]

        if os.path.exists(self.subreddits_file):
            with open(self.subreddits_file, 'r') as fh:
                content = fh.read()
                fh.close()
                spl = content.split('\n')

                for i in range(0, len(spl), 1):
                    if spl[i]:
                        subreddit = spl[i].strip()
                        entries.append(subreddit )
        entries.sort()
        #log( '  entries count ' + str( len( entries) ) )

        for subreddit_entry in entries:
            #strip out the alias identifier from the subreddit string retrieved from the file so we can process it.
            subreddit, alias, shortcut_description=parse_subreddit_entry(subreddit_entry)
            #log( subreddit + "   " + shortcut_description )

            reddit_url= assemble_reddit_filter_string("",subreddit, "yes")

            liz = compose_list_item( alias, "", "", "script", build_script("listSubReddit",reddit_url,prettify_reddit_query(alias)) )
            liz.setProperty('ACTION_manage_subreddits', build_script('manage_subreddits', subreddit_entry,"","" ) )

            listing.append(liz)

        return listing

    def build_context_menu(self):
        pass

    def busy_execute_sleep(self,executebuiltin, sleep=500, close=True):
        #
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        #RunAddon(script.reddit.reader,mode=listSubReddit&url=https%3A%2F%2Fwww.reddit.com%2Fr%2Fall%2F.json%3F%26nsfw%3Ano%2B%26limit%3D10%26after%3Dt3_4wmiag&name=all&type=)
        xbmc.executebuiltin( executebuiltin  )

        xbmc.Monitor().waitForAbort( int(sleep/1000)   )
        #xbmc.sleep(sleep) #a sleep of 500 is enough for listing subreddit  use about 5000 for executing a link/playing video especially a ytdl video

        if close:
            self.close()
        else:
            xbmc.executebuiltin( "Dialog.Close(busydialog)" )
        pass

    def close_gui(self):
        log('  close gui via exit monitor')
        self.close()
        pass

class indexGui(cGUI):
    #this is the gui that handles the initial screen.

    def onInit(self):
        #cGui.onInit()
        self.gui_listbox = self.getControl(self.main_control_id)
        #important to reset the listbox. when control comes back to this GUI(after calling another gui).
        #  kodi will "onInit" this GUI again. we end up adding items in gui_listbox
        self.gui_listbox.reset()

        if self.title_bar_text:
            self.ctl_title_bar = self.getControl(1)
            self.ctl_title_bar.setLabel(self.title_bar_text)

        #load subreddit file directly here instead of the function that calls the gui.
        #   that way, this gui can refresh the list after the subreddit file modified
        self.gui_listbox.addItems( self.load_subreddits_file_into_a_listitem() )

        #self.setFocus(self.gui_listbox)

        if self.gui_listbox_SelectedPosition > 0:
            self.gui_listbox.selectItem( self.gui_listbox_SelectedPosition )

        pass


    def onAction(self, action):

        if action in [ xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK ]:
            self.close()

        try:focused_control=self.getFocusId()
        except:focused_control=0

        if focused_control==self.main_control_id:  #main_control_id is the listbox

            self.gui_listbox_SelectedPosition  = self.gui_listbox.getSelectedPosition()
            item = self.gui_listbox.getSelectedItem()

            item_type   =item.getProperty('item_type').lower()

            if action in [ xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_CONTEXT_MENU ]:
                ACTION_manage_subreddits=item.getProperty('ACTION_manage_subreddits')
                log( "   left pressed  %d IsPlayable=%s  url=%s " %(  self.gui_listbox_SelectedPosition, item_type, ACTION_manage_subreddits )   )
                #xbmc.executebuiltin("ActivateWindow(busydialog)")


                xbmc.executebuiltin( ACTION_manage_subreddits  )

                self.close()
                #xbmc.sleep(2000)
                #xbmc.executebuiltin( "Dialog.Close(busydialog)" )

            if action == xbmcgui.ACTION_MOVE_RIGHT:
                right_button_action=item.getProperty('right_button_action')

                log( "   RIGHT pressed  %d IsPlayable=%s  url=%s " %(  self.gui_listbox_SelectedPosition, item_type, right_button_action )   )


class listSubRedditGUI(cGUI):
    reddit_query_of_this_gui=''
    SUBREDDITS_LIST=550
    SIDE_SLIDE_PANEL=9000
    #all controls in the side panel needs to be included in focused_control ACTION_MOVE_RIGHT check
    BTN_GOTO_SUBREDDIT=6052
    BTN_ZOOM_N_SLIDE=6053
    BTN_PLAY_ALL=6054
    BTN_SLIDESHOW=6055
    BTN_READ_HTML=6056
    BTN_PLAY_FROM_HERE=6057
    BTN_COMMENTS=6058
    BTN_SEARCH=6059
    BTN_RELOAD=6060
    IMG_POST_PREVIEW=201
    IMG_POST_PREVIEW2=203
    SLIDER_CTL=17
    ALBUM_LIST=5501

    def __init__(self, *args, **kwargs):
        cGUI.__init__(self, *args, **kwargs)
        #log(repr(kwargs))
        #ichdr=kwargs.get('ichdr')
        #banner=kwargs.get('banner')
        self.setProperty("subreddit_icon", kwargs.get('icon'))  #$INFO[Window.Property(subreddit_icon)]
        self.setProperty("subreddit_banner", kwargs.get('banner'))  #$INFO[Window.Property(subreddit_banner)]
        self.setProperty("subreddit_header", kwargs.get('header'))  #$INFO[Window.Property(subreddit_header)]

    def onInit(self):
        cGUI.onInit(self)

        self.setProperty("bg_image", "srr_blackbg.jpg")  #this is retrieved in the xml file by $INFO[Window.Property(bg_image)]

        self.album_listbox = self.getControl(self.ALBUM_LIST)

        #scb=self.getControl(17)#trying to hide the scrollbar. not working...
        #scb.setVisible(False)

        #self.subreddits_listbox = self.getControl(self.SUBREDDITS_LIST)
        #self.subreddits_listbox.reset()
        #self.subreddits_listbox.addItems( self.load_subreddits_file_into_a_listitem() )

    def onAction(self, action):
        from utils import dictlist_to_listItems
        import pprint

        try:focused_control=self.getFocusId()
        except:focused_control=0
        #log( "  onAction focused control=" +  str(focused_control) + " " + str( self.a ))

        if focused_control==self.main_control_id:  #main_control_id is the listbox
            self.gui_listbox_SelectedPosition = self.gui_listbox.getSelectedPosition()
            item = self.gui_listbox.getSelectedItem()
            item_type=item.getProperty('item_type').lower()

            album_images=item.getProperty('album_images')  #set in main_listing.py addLink()
            self.album_listbox.reset()
            if album_images:
                dictlist=json.loads(album_images)
                listItems=dictlist_to_listItems(dictlist)
                #log(pprint.pformat(listItems))
                self.album_listbox.addItems(listItems)

            #I want the grouplist to always scroll back on top
           #slider_ctl=self.getControl(self.SLIDER_CTL) #unknown control type in python
            #slider_ctl.setPercent(0)

            if action in [ xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK ]:
                self.close()


#            if action in [ xbmcgui.ACTION_MOVE_LEFT ] :
#                #show side menu panel
#            #    self.setFocusId(self.SIDE_SLIDE_PANEL)
#                #right_button_action=item.getProperty('right_button_action')
#                #log( "   LEFT pressed  %d IsPlayable=%s  url=%s " %(  self.gui_listbox_SelectedPosition, item_type, right_button_action )   )
#                #xbmc.executebuiltin( right_button_action  )
#
#                #xbmc.executebuiltin( "RunAddon(script.reddit.reader, ?mode=zoom_n_slide&url=d:\\test4.jpg&name=2988&type=5312)"  )
#                #xbmc.executebuiltin( "RunAddon(script.reddit.reader, ?mode=molest_xml)"  )

            if action in [xbmcgui.ACTION_CONTEXT_MENU]:
                import ast
                cxm_string=item.getProperty('context_menu')
                #log(repr(cxm_string))
                #cxm=ast.literal_eval(cxm_string)
                li=[]
                for label, action in ast.literal_eval(cxm_string):
                    liz=xbmcgui.ListItem(label=label,
                         label2='',
                         path=action)
                    li.append(liz)
                    #log(repr(cxm))
                cxm=contextMenu('srr_DialogContextMenu.xml',addon_path,listing=li)
                cxm.doModal()
                del cxm

            elif action == xbmcgui.ACTION_MOVE_LEFT:
                comments_action=item.getProperty('comments_action')
                log( "   RIGHT(comments) pressed  %d IsPlayable=%s  url=%s " %(  self.gui_listbox_SelectedPosition, item_type, comments_action )   )
                if comments_action:
                    #if there are no comments, the comments_action property is not created for this listitem
                    self.busy_execute_sleep(comments_action,3000,False )

            #elif action == xbmcgui.ACTION_MOVE_RIGHT:
            #this is done in the xml. prevents the scrollbar from getting focus when hidden.
            #    self.setFocusId(17)

        elif focused_control==self.SLIDER_CTL:
            if action in [xbmcgui.ACTION_MOVE_LEFT]:
                self.setFocusId(self.main_control_id)

        if focused_control in [self.SIDE_SLIDE_PANEL,self.SUBREDDITS_LIST,self.BTN_GOTO_SUBREDDIT,self.BTN_ZOOM_N_SLIDE,self.BTN_SLIDESHOW, self.BTN_READ_HTML, self.BTN_COMMENTS, self.BTN_SEARCH, self.BTN_RELOAD]:
            if action in [xbmcgui.ACTION_MOVE_RIGHT, xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK ]:
                self.setFocusId(self.main_control_id)

        if focused_control==self.ALBUM_LIST:
            #SelectedPosition = self.album_listbox.getSelectedPosition()
            item = self.album_listbox.getSelectedItem()
            item_type=item.getProperty('item_type').lower()

            if action in [ xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK ]:
                self.close()

            if action in [xbmcgui.ACTION_CONTEXT_MENU]:
                log('  context menu pressed for album image')
                pass


    def onClick(self, controlID):
        #from reddit import assemble_reddit_filter_string
        #log( ' clicked on control id %d'  %controlID )
        if controlID==self.main_control_id:
            self.gui_listbox_SelectedPosition = self.gui_listbox.getSelectedPosition()
            listbox_selected_item=self.gui_listbox.getSelectedItem()

            if self.include_parent_directory_entry and self.gui_listbox_SelectedPosition == 0:
                self.close()  #include_parent_directory_entry means that we've added a ".." as the first item on the list onInit()

            self.process_clicked_item(listbox_selected_item)

        elif controlID==self.ALBUM_LIST:
            #SelectedPosition = self.album_listbox.getSelectedPosition()
            selected_item=self.album_listbox.getSelectedItem()
            self.process_clicked_item(selected_item)

    def process_clicked_item(self, clicked_item):
        di_url=clicked_item.getProperty('onClick_action') #this property is created when assembling the kwargs.get("listing") for this class
        item_type=clicked_item.getProperty('item_type').lower()

        log( "  clicked on %d IsPlayable=%s  url=%s " %( self.gui_listbox_SelectedPosition, item_type, di_url )   )
        if item_type=='playable':
                #a big thank you to spoyser (http://forum.kodi.tv/member.php?action=profile&uid=103929) for this help
                pl = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
                pl.clear()
                pl.add(di_url, clicked_item)
                xbmc.Player().play(pl, windowed=False)
        elif item_type=='script':
            #if user clicked on 'next' we close this screen and load the next page.
            if 'mode=listSubReddit' in di_url:
                self.busy_execute_sleep(di_url,500,True )
            else:
                self.busy_execute_sleep(di_url,5000,False )

#    def play_from_here(self):
#        i=self.gui_listbox.getSelectedPosition()
#        list_item_bs = self.gui_listbox.getListItem(i-1)
#        post_id_bs   = list_item_bs.getProperty('post_id')
#
#        #replace or put &after=post_id to the reddit query so that the returned posts will be "&after=post_id"
#        rq=self.reddit_query_of_this_gui.split('&after=')[0]
#        #log('  rq= %s ' %( rq ) )
#        if post_id_bs:
#            rq = rq + '&after=' + post_id_bs
#        #log('  rq= %s ' %( rq ) )
#
#        action=build_script('autoPlay', rq,'','')
#        log('  PLAY_FROM_HERE %d %s %s' %( i, post_id_bs, list_item_bs.getLabel() ) )
#        self.busy_execute_sleep(action, 10000,False)

class commentsGUI(cGUI):
    BTN_LINKS=6771
    links_on_top=False
    links_top_selected_position=0
    listbox_selected_position=0

    #NOTE: i cannot get the links button to hide. so instead, I set a property when calling this class and have the button xml check for this property.
    #self.btn_links = self.getControl(self.BTN_LINKS)
    #self.btn_links.setVisible(True)
    def onInit(self):
        cGUI.onInit(self)

        #after playing a video, onInit is called again. we return the list to the state where it was at.
        if self.links_on_top:
            self.sort_links_top()
            if self.gui_listbox_SelectedPosition > 0:
                self.gui_listbox.selectItem( self.gui_listbox_SelectedPosition )
            self.setFocus(self.gui_listbox)
        #else:
        #    self.sort_links_normal()

    def onAction(self, action):
        #self.btn_links.setVisible(True)
        focused_control=self.getFocusId()
        if action in [ xbmcgui.ACTION_MOVE_LEFT ]:
            if focused_control==self.main_control_id:
                self.gui_listbox_SelectedPosition  = self.gui_listbox.getSelectedPosition()
                item = self.gui_listbox.getSelectedItem()
                self.setFocusId(self.BTN_LINKS)
            elif focused_control==self.BTN_LINKS:
                self.close()

        if action in [ xbmcgui.ACTION_MOVE_RIGHT ]:
            if focused_control==self.BTN_LINKS:
                self.setFocusId(self.main_control_id)

        if action in [ xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK ]:
            self.close()

    pass

    def onClick(self, controlID):
        cGUI.onClick(self, controlID)

        if controlID == self.BTN_LINKS:
            self.toggle_links_sorting()
            #set focus back to list so that user don't have to go back
            self.setFocusId(self.main_control_id)

    def getKey(self, li):
        #for sorting the comments list with links on top
        if li.getProperty('onClick_action'): return 1
        else:                                return 2

    def toggle_links_sorting(self):
        if self.links_on_top:
            self.sort_links_normal()
        else:
            self.sort_links_top()

    def sort_links_top(self):
        self.listbox_selected_position=self.gui_listbox.getSelectedPosition()

        self.gui_listbox.reset()
        self.gui_listbox.addItems( sorted( self.listing, key=self.getKey)  )
        self.gui_listbox.selectItem( self.links_top_selected_position )
        self.links_on_top=True

    def sort_links_normal(self):
        self.links_top_selected_position=self.gui_listbox.getSelectedPosition()
        self.gui_listbox.reset()
        self.gui_listbox.addItems( self.listing  )
        self.gui_listbox.selectItem( self.listbox_selected_position )
        self.links_on_top=False


def log(message, level=xbmc.LOGNOTICE):
    xbmc.log("reddit.reader GUI:"+message, level=level)

class progressBG( xbmcgui.DialogProgressBG ):
    progress=0.00
    heading='Loading...'
    tick_increment=1.00
    def __init__(self,heading):
        xbmcgui.DialogProgressBG.__init__(self)
        self.heading=heading
        xbmcgui.DialogProgressBG.create(self, self.heading)

    def update(self, progress, message=None):
        if self.progress>=100:
            self.progress=100
        else:
            self.progress+=progress

        if message:
            super(progressBG, self).update( int(self.progress), self.heading, message )
        else:
            super(progressBG, self).update( int(self.progress), self.heading )

    def set_tick_total(self,tick_total):
        if tick_total==0:
            self.tick_increment=1
        else:
            self.tick_total=tick_total
            remaining=100-self.progress
            self.tick_increment=float(remaining)/tick_total
            #log('xxxxremaining['+repr(remaining) +']xxxxtick_total['+repr(tick_total)+']xxxxincrement['+repr(self.tick_increment))+']'

    def tick(self,how_many, message=None):
        #increment remaining loading percentage by 1 (sort of)
        self.update(self.tick_increment*how_many, message)

    def end(self):
        super(progressBG, self).update( 100 )
        super(progressBG, self).close() #it is important to close xbmcgui.DialogProgressBG

    def getProgress(self):
        return self.progress

#class comments_GUI2(xbmcgui.WindowXML):
#    def __init__(self, *args, **kwargs):
#        xbmcgui.WindowXML.__init__(self, *args, **kwargs)
#        self.listing = kwargs.get("listing")
#        self.context_menu=kwargs.get("context_menu")
#
#    def onInit(self):
#        t1=self.getControl(100)
#        #grouplist=self.getControl(204)
#
#        #ctb1=xbmcgui.ControlTextBox(200,800,200,200)
#        #ctb1.setText('control text box number one')
#        #ctb1.setVisible(True)
#        #ctb1.setPosition(200,200)
#        #t1.setText('Lorem Ipsum is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industrys standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book. It has survived not only five centuries, but also the leap into electronic typesetting, remaining essentially unchanged. It was popularised in the 1960s with the release of Letraset sheets containing Lorem Ipsum passages, and more recently with desktop publishing software like Aldus PageMaker including versions of Lorem Ipsum.')
#        pass

if __name__ == '__main__':
    pass

