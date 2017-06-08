# -*- coding: utf-8 -*-
import xbmc
import xbmcgui
import xbmcaddon
import urllib, urlparse
import json
import threading
import re
from Queue import Queue

import os,sys

from default import addon, addon_path, itemsPerPage, urlMain, subredditsFile, subredditsPickle, int_CommentTreshold,addonUserDataFolder,CACHE_FILE
from utils import xbmc_busy, log, translation, post_excluded_from


use_requests_cache   = addon.getSetting("use_requests_cache") == "true"
default_frontpage    = addon.getSetting("default_frontpage")
no_index_page        = addon.getSetting("no_index_page") == "true"
main_gui_skin        = addon.getSetting("main_gui_skin")
use_first_link_in_textpost_for_the_following_subreddits=addon.getSetting("use_first_link_in_textpost_for_the_following_subreddits")

if use_requests_cache:
    import requests_cache
    requests_cache.install_cache(CACHE_FILE, backend='sqlite', expire_after=604800 )  #cache expires after: 86400=1day   604800=7 days

def index(url,name,type_):
    ## this is where the __main screen is created

    from guis import indexGui
    from reddit import assemble_reddit_filter_string, create_default_subreddits, populate_subreddits_pickle

    if not os.path.exists(subredditsFile):
        create_default_subreddits()

    if not os.path.exists(subredditsPickle):
        populate_subreddits_pickle()

    if no_index_page:
        log( "   default_frontpage " +default_frontpage )
        if default_frontpage:
            listSubReddit( assemble_reddit_filter_string("",default_frontpage) , default_frontpage, "")
        else:
            listSubReddit( assemble_reddit_filter_string("","") , "Reddit-Frontpage", "") #https://www.reddit.com/.json?&&limit=10
    else:
        #subredditsFile loaded in gui
        ui = indexGui('index.xml' , addon_path, defaultSkin='Default', defaultRes='1080i', subreddits_file=subredditsFile, id=55)
        ui.title_bar_text="Reddit Reader"
        ui.include_parent_directory_entry=False

        ui.doModal()
        del ui

    return

#global variables used for creating the context menu
GCXM_hasmultiplesubreddit=False
GCXM_hasmultipledomain=False
GCXM_hasmultipleauthor=False
GCXM_actual_url_used_to_generate_these_posts=''
GCXM_reddit_query_of_this_gui=''

def subreddit_icoheader_banner(subreddit):
    from reddit import get_subreddit_entry_info, ret_sub_info
    addtl_subr_info=ret_sub_info(subreddit)
    #log('addtl_subr_info'+repr(addtl_subr_info))
    try: #if addtl_subr_info:
        icon=addtl_subr_info.get('icon_img')
        banner=addtl_subr_info.get('banner_img')
        header=addtl_subr_info.get('header_img',None)  #usually the small icon on upper left side on subreddit screen
        #log('\nicon:'+repr(icon)+'\nheader:'+repr(header)+'\nbanner:'+repr(banner))
        #icoheader=(icon if icon else header)
    except AttributeError:
        icon=banner=header=None
        #get subreddit info and store it in out subreddits pickle for next time
        get_subreddit_entry_info(subreddit)
    return icon,banner,header

def listSubReddit(url, subreddit_key, type_):
    from guis import progressBG
    from utils import post_is_filtered_out, build_script, compose_list_item, xbmc_notify,prettify_reddit_query, set_query_field
    from reddit import reddit_request, has_multiple, assemble_reddit_filter_string

    global GCXM_hasmultiplesubreddit, GCXM_actual_url_used_to_generate_these_posts,GCXM_reddit_query_of_this_gui,GCXM_hasmultipledomain,GCXM_hasmultipleauthor
    #the +'s got removed by url conversion
    title_bar_name=subreddit_key.replace(' ','+')
    if title_bar_name.startswith('?'):
        title_bar_name=prettify_reddit_query(title_bar_name)
    #log("  title_bar_name %s " %(title_bar_name) )

    log("listSubReddit r/%s\n %s" %(title_bar_name,url) )

    currentUrl = url
    icon=banner=header=None
    xbmc_busy()

    loading_indicator=progressBG('Loading...')
    loading_indicator.update(0,'Retrieving '+subreddit_key)
    content = reddit_request(url)
    loading_indicator.update(10,subreddit_key  )

    if not content:
        xbmc_busy(False)
        loading_indicator.end() #it is important to close xbmcgui.DialogProgressBG
        return

    threads = []
    q_liz = Queue()   #output queue (listitem)

    content = json.loads(content)
    #log("query returned %d items " % len(content['data']['children']) )
    posts_count=len(content['data']['children'])
    filtered_out_posts=0

    hms=has_multiple('subreddit', content['data']['children'])

    if hms==False:  #r/random and r/randnsfw returns a random subreddit. we need to use the name of this subreddit for the "next page" link.
        try: g=content['data']['children'][0]['data']['subreddit']
        except ValueError: g=""
        except IndexError:
            xbmc_busy(False)
            loading_indicator.end() #it is important to close xbmcgui.DialogProgressBG
            xbmc_notify("List Subreddit",translation(32022))
            return
        if g:
            title_bar_name=g
            #preserve the &after string so that functions like play slideshow and play all videos can 'play' the correct page
            #  extract the &after string from currentUrl -OR- send it with the 'type' argument when calling this function.
            currentUrl=assemble_reddit_filter_string('',g) + '&after=' + type_

        #put subreddit icon/header in the GUI
        icon,banner,header=subreddit_icoheader_banner(g)

    GCXM_hasmultiplesubreddit=hms
    GCXM_hasmultipledomain=has_multiple('domain', content['data']['children'])
    GCXM_hasmultipleauthor=has_multiple('author', content['data']['children'])
    GCXM_actual_url_used_to_generate_these_posts=url
    GCXM_reddit_query_of_this_gui=currentUrl

    for idx, entry in enumerate(content['data']['children']):
        try:
            #if entry.get('kind')!='t3':
            #    filtered_out_posts+=1
            #    continue
            if post_is_filtered_out( entry.get('data') ):
                filtered_out_posts+=1
                continue
            #have threads process each reddit post
            t = threading.Thread(target=reddit_post_worker, args=(idx, entry,q_liz), name='#t%.2d'%idx)
            threads.append(t)
            t.start()

        except Exception as e:
            log(" EXCEPTION:="+ str( sys.exc_info()[0]) + "  " + str(e) )

    #check the queue to determine progress
    break_counter=0 #to avoid infinite loop
    expected_listitems=(posts_count-filtered_out_posts)
    if expected_listitems>0:
        loading_indicator.set_tick_total(expected_listitems)
        last_queue_size=0
        while q_liz.qsize() < expected_listitems:
            if break_counter>=100:
                break

            #each change in the queue size gets a tick on our progress track
            if last_queue_size < q_liz.qsize():
                items_added=q_liz.qsize()-last_queue_size
                loading_indicator.tick(items_added)
            else:
                break_counter+=1

            last_queue_size=q_liz.qsize()
            xbmc.sleep(100)

    #wait for all threads to finish before collecting the list items
    for idx, t in enumerate(threads):
        #log('    joining %s' %t.getName())
        t.join(timeout=20)

    xbmc_busy(False)

    #compare the number of entries to the returned results
    #log( "queue:%d entries:%d" %( q_liz.qsize() , len(content['data']['children'] ) ) )
    if q_liz.qsize() != expected_listitems:
        #some post might be filtered out.
        log('some threads did not return a listitem')

    #for t in threads: log('isAlive %s %s' %(t.getName(), repr(t.isAlive()) )  )

    #liu=[ qi for qi in sorted(q_liz.queue) ]
    li=[ liz for idx,liz in sorted(q_liz.queue) ]

    #empty the queue.
    with q_liz.mutex:
        q_liz.queue.clear()

    loading_indicator.end() #it is important to close xbmcgui.DialogProgressBG

    try:
        #this part makes sure that you load the next page instead of just the first
        after=content['data']['after']
        o = urlparse.urlparse(currentUrl)
        current_url_query = urlparse.parse_qs(o.query)

        count=current_url_query.get('count')
        if current_url_query.get('count')==None:
            #firsttime it is none
            count=itemsPerPage
        else:
            #nexttimes it will be kept incremented with itemsPerPage
            try: count=int(current_url_query.get('count')[0]) + int(itemsPerPage)
            except ValueError: count=itemsPerPage

        nextUrl=set_query_field(currentUrl,'count', count, True)
        #log('$$$   nextUrl: ' +nextUrl)

        nextUrl=set_query_field(nextUrl, field='after', value=after, replace=True)  #(url, field, value, replace=False):
        #log('$$$currenturl: ' +currentUrl)
        #log('$$$   nextUrl: ' +nextUrl)

        liz = compose_list_item( translation(32004), "", "DefaultFolderNextSquare.png", "script", build_script("listSubReddit",nextUrl,title_bar_name,after) )

        #for items at the bottom left corner
        liz.setArt({ "clearart": "DefaultFolderNextSquare.png"  })
        liz.setInfo(type='video', infoLabels={"Studio":translation(32004)})
        liz.setProperty('link_url', nextUrl )
        li.append(liz)

    except Exception as e:
        log(" EXCEPTzION:="+ str( sys.exc_info()[0]) + "  " + str(e) )

    xbmc_busy(False)

    title_bar_name=urllib.unquote_plus(title_bar_name)
    ui=skin_launcher('listSubReddit',
                     title_bar_name=title_bar_name,
                     listing=li,
                     subreddits_file=subredditsFile,
                     currentUrl=currentUrl,
                     icon=icon,
                     banner=banner,
                     header=header)
    ui.doModal()
    del ui
    #ui.show()  #<-- interesting possibilities. you have to handle the actions outside of the gui class.
    #xbmc.sleep(8000)

def skin_launcher(mode,**kwargs ):
    #launches the gui using .xml file defined in settings (incomplete)
    from guis import listSubRedditGUI

    #kodi_version = xbmcVersion()
    #log( ' kodi version:%f' % kodi_version )
    #if kodi_version >= 17:  #krypton
    #    pass

    title_bar_text=kwargs.get('title_bar_name')
    #listing=kwargs.get('listing')
    #subreddits_file=kwargs.get('subreddits_file')
    currentUrl=kwargs.get('currentUrl')
    #log('********************* ' + repr(currentUrl))
    try:
        ui = listSubRedditGUI(main_gui_skin , addon_path, defaultSkin='Default', defaultRes='1080i',
                              id=55,
                              **kwargs   #just pass along the **kwargs, the class will sort them out
                              )
        ui.title_bar_text='[B]'+ title_bar_text + '[/B]'
        ui.reddit_query_of_this_gui=currentUrl
        #ui.include_parent_directory_entry=True
        #ui.doModal()
        #del ui
        return ui
    except Exception as e:
        log('  skin_launcher:%s(%s)' %( str(e), main_gui_skin ) )
        xbmc.executebuiltin('XBMC.Notification("%s","%s[CR](%s)")' %(  translation(32108), str(e), main_gui_skin)  )

def reddit_post_worker(idx, entry, q_out):
    import datetime
    from utils import pretty_datediff, clean_str, get_int, format_description
    from reddit import determine_if_video_media_from_reddit_json
    from domains import sitesBase
    try:
        credate = ""
        is_a_video=False
        title_line2=""
        thumb_w=0; thumb_h=0

        t_on = translation(32071)  #"on"
        #t_pts = u"\U0001F4AC"  # translation(30072) #"cmnts"  comment bubble symbol. doesn't work
        t_pts = u"\U00002709"  # translation(30072)   envelope symbol
        t_up = u"\U000025B4"  #u"\U00009650"(up arrow)   #upvote symbol

        #on 3/21/2017 we're adding a new feature that lets users view their saved posts by entering /user/username/saved as their subreddit.
        #  in addition to saved posts, users can also save comments. we need to handle it by checking for "kind"
        kind=entry.get('kind')  #t1 for comments  t3 for posts
        data=entry.get('data')
        if data:
            if kind=='t3':
                title = clean_str(data,['title'])
                description=clean_str(data,['media','oembed','description'])
                post_selftext=clean_str(data,['selftext'])

                description=post_selftext+'\n'+description if post_selftext else description
                domain=clean_str(data,['domain'])
            else:
                title=clean_str(data,['link_title'])
                description=clean_str(data,['body'])
                domain='Comment post'

            description=format_description(description, hide_text_in_parens=False)
            first_link_in_description=None

            #title=strip_emoji(title) #an emoji in the title was causing a KeyError  u'\ud83c'
            title=format_description(title)

            is_a_video = determine_if_video_media_from_reddit_json(entry)
            log("  POS%s%cTITLE%.2d=%s" %( kind, ("v" if is_a_video else " "), idx, title ))
            #log("description%.2d=%s" %(idx,description))
            post_id = entry['kind'] + '_' + data.get('id')  #same as entry['data']['name']
            #log('  %s  %s ' % (post_id, entry['data']['name'] ))
            commentsUrl = urlMain+clean_str(data,['permalink'])
            #log("commentsUrl"+str(idx)+"="+commentsUrl)
            try:
                aaa = data.get('created_utc')
                credate = datetime.datetime.utcfromtimestamp( aaa )
                now_utc = datetime.datetime.utcnow()
                pretty_date=pretty_datediff(now_utc, credate)
                credate = str(credate)
            except (AttributeError,TypeError,ValueError):
                credate = ""

            subreddit=clean_str(data,['subreddit'])
            author=clean_str(data,['author'])
            #log("     DOMAIN%.2d=%s" %(idx,domain))

            #post_excluded_from() is a misnomer. it just returns true if subreddit is in csv-list
            if (post_excluded_from( use_first_link_in_textpost_for_the_following_subreddits, subreddit) or
                post_excluded_from( use_first_link_in_textpost_for_the_following_subreddits, 'all')        ):
                first_link_in_description=sitesBase.get_first_url_from(description)
                #override the domain so that bottom right of gui matches link
                if first_link_in_description:
                    domain = '{uri.netloc}'.format( uri=urlparse.urlparse( first_link_in_description ) )

            ups = data.get('score',0)       #downs not used anymore
            num_comments = data.get('num_comments',0)

            d_url=clean_str(data,['url'])
            link_url=clean_str(data,['link_url'])
            media_oembed_url=clean_str(data,['media','oembed','url'])
#            log('   kind     ='+kind)
#            log('    url     ='+d_url)
#            log('    link_url='+link_url)
#            log('   permalink='+clean_str(data,['permalink']))
#            log('    media_oembed_url='+media_oembed_url)
            media_url=next((item for item in [first_link_in_description,d_url,link_url,media_oembed_url] if item ), '')
            #log("     MEDIA%.2d=%s" %(idx,media_url))

            thumb=clean_str(data,['thumbnail'])

            #media_w=get_int(data,['media','oembed','width'])
            #media_h=get_int(data,['media','oembed','height'])
            #log('  media_w='+repr(media_w)+' h='+repr(media_h) )

            #try:log('  media_w='+repr(data.get('media')['oembed']['width']  ) )
            #except:pass

            if not thumb.startswith('http'): #in ['nsfw','default','self']:  #reddit has a "default" thumbnail (alien holding camera with "?")
                thumb=""

            if thumb=="":
                thumb=clean_str(data,['media','oembed','thumbnail_url']).replace('&amp;','&')

            #a blank preview image will be replaced with poster_url from parse_reddit_link() for domains that support it
            preview=clean_str(data,['preview','images',0,'source','url']).replace('&amp;','&') #data.get('preview')['images'][0]['source']['url'].encode('utf-8').replace('&amp;','&')
            #log('  preview='+repr(preview))
            #try:
            thumb_h=get_int(data,['preview','images',0,'source','height'])#float( data.get('preview')['images'][0]['source']['height'] )
            thumb_w=get_int(data,['preview','images',0,'source','width']) #float( data.get('preview')['images'][0]['source']['width'] )
            #except (AttributeError,TypeError,ValueError):
                #log("   thumb_w _h EXCEPTION:="+ str( sys.exc_info()[0]) + "  " + str(e) )
            #   thumb_w=0; thumb_h=0

            #preview images are 'keep' stretched to fit inside 1080x1080.
            #  if preview image is smaller than the box we have for thumbnail, we'll use that as thumbnail and not have a bigger stretched image
            if thumb_w > 0 and thumb_w < 280:
                #log('*******preview is small ')
                thumb=preview
                thumb_w=0; thumb_h=0; preview=""

            over_18=data.get('over_18')

            title_line2=""
            title_line2 = "[I][COLOR dimgrey]%d%c %s %s [B][COLOR cadetblue]r/%s[/COLOR][/B] (%d) %s[/COLOR][/I]" %(ups,t_up,pretty_date,t_on, subreddit,num_comments, t_pts)

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
                    commentsUrl=commentsUrl,
                    subreddit=subreddit,
                    link_url=media_url,
                    over_18=over_18,
                    posted_by=author,
                    num_comments=num_comments,
                    post_id=post_id,
                    )

            q_out.put( [idx, liz] )  #we put the idx back for easy sorting

    except Exception as e:
        log( '  #reddit_post_worker EXCEPTION:' + repr(sys.exc_info()) +'--'+ str(e) )

def addLink(title, title_line2, iconimage, previewimage,preview_w,preview_h,domain, description, credate, reddit_says_is_video, commentsUrl, subreddit, link_url, over_18, posted_by="", num_comments=0,post_id=''):
    from utils import ret_info_type_icon, build_script,colored_subreddit
    #from reddit import assemble_reddit_filter_string
    from domains import parse_reddit_link, sitesBase
    from ContextMenus import build_context_menu_entries

    preview_ar=0.0
    DirectoryItem_url=''

    if over_18:
        mpaa="R"
        title_line2 = "[COLOR red][NSFW][/COLOR] "+title_line2
    else:
        mpaa=""

    post_title=title

    if len(post_title) > 100 or description:
        il_description='[B]%s[/B][CR][CR]%s' %( post_title, description )
    else:
        il_description=''

    il={ "title": post_title, "plot": il_description, "Aired": credate, "mpaa": mpaa, "Genre": "r/"+subreddit, "studio": domain, "director": posted_by }   #, "duration": 1271}   (duration uses seconds for titan skin

    liz=xbmcgui.ListItem(label=post_title
                         ,label2=title_line2
                         ,path='')   #path not used by gui.

    if preview_w==0 or preview_h==0:
        preview_ar=0.0
    else:
        preview_ar=float(preview_w) / preview_h

        #log('    preview_ar:'+repr(preview_ar))
        if preview_ar>1.4:   #this triggers whether the (control id 203) will show up
            #the gui checks for this: String.IsEmpty(Container(55).ListItem.Property(preview_ar))  to show/hide a wider preview
            #   this is overridden if the post is an album.
            liz.setProperty('preview_ar', str(preview_ar) ) # -- $INFO[ListItem.property(preview_ar)]
            #text_below_image=il_description+title_line2 + colored_subreddit( posted_by, 'dimgrey',False )
            text_below_image='[B]%s[/B][CR]%s %s[CR]%s' %( post_title, title_line2, colored_subreddit( ' by '+posted_by, 'dimgrey',False ), description )
            liz.setInfo(type='video', infoLabels={"plotoutline": text_below_image, }  )

        #makes the gui use a control that allows the user scroll tall image
        if preview_ar<0.3:
            liz.setProperty('very_tall_image', str(preview_ar) ) # -- IsEmpty(Container(55).ListItem.Property(very_tall_image))
        elif preview_ar<0.5:
            liz.setProperty('tall_image', str(preview_ar) ) # -- IsEmpty(Container(55).ListItem.Property(tall_image))

    if num_comments > 0 or description:
        liz.setProperty('comments_action', build_script('listLinksInComment', commentsUrl ) )

    liz.setProperty('link_url', link_url )

    liz.setInfo(type='video', infoLabels=il)

    #use clearart to indicate if link is video, album or image. here, we default to unsupported.
    clearart=ret_info_type_icon('', '')
    liz.setArt({ "clearart": clearart  })

    #force all links to ytdl to see if they are playable
    liz.setProperty('item_type','script')
    liz.setProperty('onClick_action', build_script('playYTDLVideo', link_url,'',previewimage) )

    #***build context menu***
    #    convert a list of tuple into a string then set it as a property
    #    in GUI, the string is converted back via ast.literal_eval() and put into listItems
    liz.setProperty('context_menu', str(build_context_menu_entries(num_comments, commentsUrl, subreddit, domain, link_url, post_id, post_title, posted_by)) )

    if previewimage: needs_preview=False
    else:            needs_preview=True  #reddit has no thumbnail for this link. please get one

    ld=parse_reddit_link(link_url,reddit_says_is_video, needs_preview, False, preview_ar  )

    if previewimage=="":
        if domain.startswith('self.'):
            liz.setArt({"thumb": ld.thumb if ld else '', "banner": '' , })
        else:
            liz.setArt({"thumb": iconimage, "banner": ld.poster if ld else '' , })
    else:
        liz.setArt({"thumb": iconimage, "banner":previewimage,  })
    #log( '          reddit thumb[%s] ' %(iconimage ))
    #og( '          reddit preview[%s] ar=%f %dx%d' %(previewimage, preview_ar, preview_w,preview_h ))
    #if ld: log( '          new-thumb[%s] poster[%s] ' %( ld.thumb, ld.poster ))

    if ld:
        #use clearart to indicate the type of link(video, album, image etc.)
        clearart=ret_info_type_icon(ld.media_type, ld.link_action, domain )
        liz.setArt({ "clearart": clearart  })

        if iconimage in ["","nsfw", "default"]:
            iconimage=ld.thumb

        #we gathered a description from the link
        if ld.desctiption:
            liz.setInfo(type='video', infoLabels={'plot': il_description + '[CR]' + ld.desctiption, })

        if ld.dictlist:
            #log('****has album images')
            #listItem is not json serializable so dictlist_to_listItems() is done in the gui
            #image_listItems=dictlist_to_listItems(ld.dictlist)
            liz.setProperty('album_images', json.dumps( ld.dictlist ) ) # dictlist=json.loads(string)
            #overrride the preview_ar flag. (easier to do this here than have the xml figure it out in <visible>
            liz.setProperty('preview_ar', None )
            #log( liz.getProperty('album_images'))

        #link_action set in domains.py - parse_reddit_link
        if ld.link_action == sitesBase.DI_ACTION_PLAYABLE:
            property_link_type=ld.link_action
            DirectoryItem_url =ld.playable_url
        else:
            property_link_type='script'
            if ld.link_action=='viewTallImage' : #viewTallImage take different args
                DirectoryItem_url = build_script(mode=ld.link_action,
                                                 url=ld.playable_url,
                                                 name=str(preview_w),
                                                 type_=str(preview_h) )
            else:
                #log( '****' + repr( ld.dictlist ))
                DirectoryItem_url = build_script(mode=ld.link_action,
                                                 url=ld.playable_url,
                                                 name=post_title ,
                                                 type_=previewimage )

        #log('    action %s--%s' %( ld.link_action, DirectoryItem_url) )

        liz.setProperty('item_type',property_link_type)
        liz.setProperty('onClick_action',DirectoryItem_url)
    else:
        #unsupported type here:
        pass

    return liz


def listLinksInComment(url, name, type_):
    from guis import progressBG
    from reddit import reddit_request
    from utils import clean_str,remove_duplicates, is_filtered
    from default import comments_link_filter

    log('listLinksInComment:%s:%s' %(type_,url) )

    post_title=''
    global harvest
#    ShowOnlyCommentsWithlink=False
#    if type_=='linksOnly':
#        ShowOnlyCommentsWithlink=True

    #url='https://np.reddit.com/r/videos/comments/64j9x7/doctor_violently_dragged_from_overbooked_cia/dg2pbtj/?st=j1cbxsst&sh=2d5daf4b'
    #url=url.split('?', 1)[0]+'.json'+url.split('?', 1)[1]

    #log(repr(url.split('?', 1)[0]))
    #log(repr(url.split('?', 1)[1]))
    #log(repr(url.split('?', 1)[0]+'.json?'+url.split('?', 1)[1]))

    #url='https://www.reddit.com/r/Music/comments/4k02t1/bonnie_tyler_total_eclipse_of_the_heart_80s_pop/' + '.json'
    #only get up to "https://www.reddit.com/r/Music/comments/4k02t1".
    #   do not include                                            "/bonnie_tyler_total_eclipse_of_the_heart_80s_pop/"
    #   because we'll have problem when it looks like this: "https://www.reddit.com/r/Overwatch/comments/4nx91h/ever_get_that_feeling_dÃ©jÃ _vu/"
    #url=re.findall(r'(.*/comments/[A-Za-z0-9]+)',url)[0]
    #UPDATE you need to convert this: https://www.reddit.com/r/redditviewertesting/comments/4x8v1k/test_test_what_is_déjà_vu/
    #                        to this: https://www.reddit.com/r/redditviewertesting/comments/4x8v1k/test_test_what_is_d%C3%A9j%C3%A0_vu/
    #
    #use safe='' argument in quoteplus to encode only the weird chars part
    url=urllib.quote_plus(url,safe=':/?&')

    if '?' in url:
        url=url.split('?', 1)[0]+'.json?'+url.split('?', 1)[1]
    else:
        url+= '.json'

    xbmc_busy()

    loading_indicator=progressBG('Loading...')
    loading_indicator.update(0,'Retrieving comments')
    content = reddit_request(url)
    loading_indicator.update(10,'Parsing')

    if not content:
        loading_indicator.end()
        return

    try:
        xbmc_busy()
        content = json.loads(content)

        del harvest[:]
        #harvest links in the post text (just 1)
        r_linkHunter(content[0]['data']['children'])

        #submitter=content[0]['data']['children'][0]['data']['author']
        submitter=clean_str(content,[0,'data','children',0,'data','author'])

        #the post title is provided in json, we'll just use that instead of messages from addLink()
        #post_title=content[0]['data']['children'][0]['data']['title']
        post_title=clean_str(content,[0,'data','children',0,'data','title'])

        #harvest links in the post itself
        r_linkHunter(content[1]['data']['children'])
        #for i, h in enumerate(harvest):
        #    log( '  %d %s %.4d -%s   link[%s]' % ( i, h[7].ljust(8)[:8], h[0], h[3].ljust(20)[:20],h[2] ) )


        comments_count_orig=len(harvest)
        #log(' len harvest1 '+repr(len(harvest)))
        #remove duplicate links
        def k2(x): return (x[2],x[3])
        harvest=remove_duplicates(harvest,k2)
        comments_count_rd=len(harvest)
        #log(' len harvest2 '+repr(len(harvest)))

        loading_indicator.update(15,'Removed %d duplicates' %(comments_count_orig-comments_count_rd) )

        c_threads=[]
        q_liz=Queue()
        comments_count=len(harvest)
        filtered_posts=0
        for idx, h in enumerate(harvest):
            comment_score=h[0]
            link_url=h[2]
            if comment_score < int_CommentTreshold:
                log('    comment score %d < %d, skipped' %(comment_score,int_CommentTreshold) )
                filtered_posts+=1
                continue

            if is_filtered(comments_link_filter,link_url):
                log('    [{}] is hidden by comments_link_filter'.format(link_url))
                filtered_posts+=1
                continue

            #have threads process each comment post
            t = threading.Thread(target=reddit_comment_worker, args=(idx, h,q_liz,submitter), name='#t%.2d'%idx)
            c_threads.append(t)
            t.start()

        #loading_indicator.update(20,'Filtered %d comments' %(filtered_posts) )

        #check the queue to determine progress
        break_counter=0 #to avoid infinite loop
        expected_listitems=(comments_count-filtered_posts)
        if expected_listitems>0:
            loading_indicator.set_tick_total(expected_listitems)
            last_queue_size=0
            while q_liz.qsize() < expected_listitems:
                if break_counter>=100:
                    break
                #each change in the queue size gets a tick on our progress track
                if last_queue_size < q_liz.qsize():
                    items_added=q_liz.qsize()-last_queue_size
                    loading_indicator.tick(items_added,'Parsing')
                else:
                    break_counter+=1

                last_queue_size=q_liz.qsize()
                xbmc.sleep(50)

        #wait for all threads to finish before collecting the list items
        for idx, t in enumerate(c_threads):
            #log('    joining %s' %t.getName())
            t.join(timeout=20)

        xbmc_busy(False)

        #compare the number of entries to the returned results
        #log( "queue:%d entries:%d" %( q_liz.qsize() , len(content['data']['children'] ) ) )
        if q_liz.qsize() != expected_listitems:
            log('some threads did not return a listitem. total comments:%d expecting(%d) but only got(%d)' %(comments_count, expected_listitems, q_liz.qsize()))

        #for t in threads: log('isAlive %s %s' %(t.getName(), repr(t.isAlive()) )  )
        li=[ liz for idx,liz in sorted(q_liz.queue) ]
        #log(repr(li))

        with q_liz.mutex:
            q_liz.queue.clear()

    except Exception as e:
        log('  ' + str(e) )

    loading_indicator.end() #it is important to close xbmcgui.DialogProgressBG
# this portion is abandoned for now. initial plan was to textbox with auto-height in a grouplist to mimic the comment tree but cannot figure out how links can be followed.
    from guis import comments_GUI2
    ui = comments_GUI2('view_464_comments_grouplist.xml' , addon_path, defaultSkin='Default', defaultRes='1080i', listing=li, id=55)
    #ui = comments_GUI2('aaa.xml' , addon_path, defaultSkin='Default', defaultRes='1080i', listing=li, id=55)
    ui.title_bar_text=post_title
    ui.doModal()
    del ui
    return

def reddit_comment_worker(idx, h, q_out,submitter):
    from domains import parse_reddit_link, sitesBase
    from utils import format_description, ret_info_type_icon, build_script, is_filtered
    from ContextMenus import build_youtube_context_menu_entries, build_reddit_context_menu_entries, build_link_in_browser_context_menu_entries, build_open_browser_to_pair_context_menu_entries

#         h[0]=score,
#         h[1]=link_desc,
#         h[2]=link_http,
#         h[3]=post_text,
#         h[4]=post_html,
#         h[5]=d,
#         h[6]="t1",
#         h[7]=author,
#         h[8]=created_utc,
    try:
        #log(str(i)+"  score:"+ str(h[0]).zfill(5)+" "+ h[1] +'|'+ h[3] )
        comment_score=h[0]
        #log("score %d < %d (%s)" %(comment_score,int_CommentTreshold, CommentTreshold) )
        link_url=h[2]
        desc100=h[3].replace('\n',' ')[0:100] #first 100 characters of description

        kind=h[6] #reddit uses t1 for user comments and t3 for OP text of the post. like a poster describing the post.
        d=h[5]   #depth of the comment
        tab=" "*d if d>0 else "-"
        author=h[7]

        domain=''
        if link_url.startswith('/r/'):
            domain='subreddit'
        elif link_url.startswith('/u/'):
            domain='redditor'
        elif link_url.startswith('#'): #some sort of css flair
            link_url=''
        else:
            domain = '{uri.netloc}'.format( uri=urlparse.urlparse( link_url ) )

        if link_url:
            log( '  comment %s TITLE:%s... link[%s]' % ( str(d).zfill(3), desc100.ljust(20)[:20],link_url ) )

        ld=parse_reddit_link(link_url=link_url, assume_is_video=False, needs_preview=True, get_playable_url=True )

        plot=format_description(h[3])

        if author==submitter:#add a submitter tag
            author="[COLOR cadetblue][B]%s[/B][/COLOR][S]" %author
            plot="[B][OP][/B] "+plot
        else:
            author="[COLOR cadetblue]%s[/COLOR]" %author

        if kind=='t1':
            t_prepend=r"%s" %( tab )
        elif kind=='t3':
            t_prepend=r"[B]Post text:[/B]"

        liz=xbmcgui.ListItem(label=t_prepend + author + ': '+ desc100 ,
                             label2="")
        liz.setInfo( type="Video", infoLabels={ "Title": h[1], "plot": plot, "studio": domain, "votes": str(comment_score), "director": author } )
        liz.setProperty('comment_depth',str(d))
        liz.setProperty('plot',plot)    #cannot retrieve infolabels in the gui. we put 'plot' here too.
        liz.setProperty('author',author)#                     and 'author' too.

        #force all links to ytdl to see if it can be played
        if link_url:
            #log('      there is a link from %s' %domain)
            if not ld:
                #log('      link is not supported ')
                liz.setProperty('item_type','script')
                liz.setProperty('onClick_action', build_script('playYTDLVideo', link_url) )
                plot= "[COLOR greenyellow][%s] %s"%('?', plot )  + "[/COLOR]"
                liz.setLabel(tab+plot)
                liz.setProperty('link_url', link_url )  #just used as text at bottom of the screen

                clearart=ret_info_type_icon('', '')
                liz.setArt({ "clearart": clearart  })
        if ld:
            #use clearart to indicate if link is video, album or image. here, we default to unsupported.
            #clearart=ret_info_type_icon(setInfo_type, mode_type)
            clearart=ret_info_type_icon(ld.media_type, ld.link_action, domain )
            liz.setArt({ "clearart": clearart  })

            if ld.link_action == sitesBase.DI_ACTION_PLAYABLE:
                property_link_type=ld.link_action
                DirectoryItem_url =ld.playable_url
            else:
                property_link_type='script'
                DirectoryItem_url = build_script(mode=ld.link_action,
                                                 url=ld.playable_url,
                                                 name='' ,
                                                 type_='' )

            #(score, link_desc, link_http, post_text, post_html, d, )
            #list_item_name=str(h[0]).zfill(3)

            #log(str(i)+"  score:"+ str(h[0]).zfill(5)+" desc["+ h[1] +']|text:['+ h[3]+']' +link_url + '  videoID['+videoID+']' + 'playable:'+ setProperty_IsPlayable )
            #log( h[4] + ' -- videoID['+videoID+']' )
            #log("sss:"+ supportedPluginUrl )

            #fl= re.compile('\[(.*?)\]\(.*?\)',re.IGNORECASE) #match '[...](...)' with a capture group inside the []'s as capturegroup1
            #result = fl.sub(r"[B]\1[/B]", h[3])              #replace the match with [B] [/B] with capturegroup1 in the middle of the [B]'s

            #turn link green
            if DirectoryItem_url:
                plot= "[COLOR greenyellow][%s] %s"%(domain, plot )  + "[/COLOR]"
                liz.setLabel(tab+plot)

                #liz.setArt({"thumb": thumb_url, "poster":thumb_url, "banner":thumb_url, "fanart":thumb_url, "landscape":thumb_url   })
                liz.setArt({"thumb": ld.thumb,"banner":ld.poster })

                liz.setProperty('item_type',property_link_type)   #script or playable
                liz.setProperty('onClick_action', DirectoryItem_url)  #<-- needed by the xml gui skin
                liz.setProperty('link_url', link_url )  #just used as text at bottom of the screen
                #liz.setPath(DirectoryItem_url)

                context_menu_list=[]
                context_menu_list.extend(build_youtube_context_menu_entries(type_='',youtube_url=link_url,video_id=None))
                context_menu_list.extend(build_reddit_context_menu_entries(link_url))
                context_menu_list.extend(build_link_in_browser_context_menu_entries(link_url))
                context_menu_list.extend(build_open_browser_to_pair_context_menu_entries(link_url))

                liz.setProperty('context_menu', str(context_menu_list) )

                #directory_items.append( (DirectoryItem_url, liz,) )
        else:
            #this section are for comments that have no links or unsupported links
            #if not ShowOnlyCommentsWithlink:
                #directory_items.append( ("", liz, ) )
            pass
            #END section are for comments that have no links or unsupported links

        q_out.put( [idx, liz] )

    except Exception as e:
        log('EXCEPTION comments_worker '+ str(e))

harvest=[]
def r_linkHunter(json_node,d=0):
    from utils import clean_str
    #recursive function to harvest stuff from the reddit comments json reply
    prog = re.compile('<a href=[\'"]?([^\'" >]+)[\'"]>(.*?)</a>')
    for e in json_node:
        link_desc=""
        link_http=""
        author=""
        created_utc=""
        e_data=e.get('data')
        score=e_data.get('score',0)
        if e['kind']=='t1':     #'t1' for comments   'more' for more comments (not supported)
            #log("replyid:"+str(d)+" "+e['data']['id'])
            #body=e['data']['body'].encode('utf-8')

            #log("reply:"+str(d)+" "+body.replace('\n','')[0:80])
            try: replies=e_data.get('replies')['data']['children']
            except (AttributeError,TypeError): replies=""

            post_text=clean_str(e_data,['body'])
            post_text=post_text.replace("\n\n","\n")

            post_html=clean_str(e_data,['body_html'])

            created_utc=e_data.get('created_utc','')

            author=clean_str(e_data,['author'])

            #i initially tried to search for [link description](https:www.yhotuve.com/...) in the post_text but some posts do not follow this convention
            #prog = re.compile('\[(.*?)\]\((https?:\/\/.*?)\)')
            #result = prog.findall(post_text)

            result = prog.findall(post_html)
            if result:
                #store the post by itself and then a separate one for each link.
                harvest.append((score, link_desc, link_http, post_text, post_html, d, "t1",author,created_utc,)   )

                for link_http,link_desc in result:
                    harvest.append((score, link_desc, link_http, link_desc, post_html, d, "t1",author,created_utc,)   )
            else:
                harvest.append((score, link_desc, link_http, post_text, post_html, d, "t1",author,created_utc,)   )

            d+=1 #d tells us how deep is the comment in
            r_linkHunter(replies,d)
            d-=1

        if e['kind']=='t3':     #'t3' for post text (a description of the post)
            self_text=clean_str(e_data,['selftext'])
            self_text_html=clean_str(e_data,['selftext_html'])

            result = prog.findall(self_text_html)
            if len(result) > 0 :
                harvest.append((score, link_desc, link_http, self_text, self_text_html, d, "t3",author,created_utc, )   )

                for link_http,link_desc in result:
                    harvest.append((score, link_desc, link_http, link_desc, self_text_html, d, "t3",author,created_utc, )   )
            else:
                if len(self_text) > 0: #don't post an empty titles
                    harvest.append((score, link_desc, link_http, self_text, self_text_html, d, "t3",author,created_utc,)   )



if __name__ == '__main__':
    pass
