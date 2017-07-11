import re
import urllib
import urlparse

from main_listing import GCXM_hasmultipleauthor, GCXM_hasmultiplesubreddit, GCXM_hasmultipledomain, GCXM_actual_url_used_to_generate_these_posts, GCXM_reddit_query_of_this_gui
from default import addon
from reddit import assemble_reddit_filter_string, subreddit_in_favorites #, this_is_a_user_saved_list
from utils import log,translation, colored_subreddit, build_script, truncate

cxm_show_html_to_text     = addon.getSetting("cxm_show_html_to_text") == "true"
cxm_show_open_browser     = addon.getSetting("cxm_show_open_browser") == "true"
cxm_show_comments         = addon.getSetting("cxm_show_comments") == "true"

cxm_show_by_author        = addon.getSetting("cxm_show_by_author") == "true"
cxm_show_by_subreddit     = addon.getSetting("cxm_show_by_subreddit") == "true"
cxm_show_by_domain        = addon.getSetting("cxm_show_by_domain") == "true"

cxm_show_autoplay         = addon.getSetting("cxm_show_autoplay") == "true"
cxm_show_slideshow        = addon.getSetting("cxm_show_slideshow") == "true"

cxm_show_add_shortcuts    = addon.getSetting("cxm_show_add_shortcuts") == "true"
#cxm_show_new_from         = addon.getSetting("cxm_show_new_from") == "true"
cxm_show_filter           = addon.getSetting("cxm_show_filter") == "true"
cxm_show_search           = addon.getSetting("cxm_show_search") == "true"
#cxm_show_reddit_save      = addon.getSetting("cxm_show_reddit_save") == "true"
cxm_show_youtube_items    = addon.getSetting("cxm_show_youtube_items") == "true"
cxm_show_add_to_favorites = addon.getSetting("cxm_show_add_to_favorites") == "true"

def build_context_menu_entries(num_comments,commentsUrl, subreddit, domain, link_url, post_id, post_title, posted_by, onClick_action, thumbnail):
    s=truncate(subreddit,15)     #crop long subreddit names in context menu
    colored_subreddit_short=colored_subreddit( s )
    colored_domain_full=colored_subreddit( domain, 'tan',False )
    post_title_short=truncate(post_title,15)
    post_author=truncate(posted_by,15)

    label_view_comments=translation(32504)+' ({})'.format(num_comments)
    label_more_by_author=translation(32506).format(author=post_author)
    label_goto_subreddit=translation(32508).format(subreddit=subreddit)
    label_goto_domain=translation(32510).format(domain=domain)
    label_autoplay_after=translation(32513)+' '+colored_subreddit( post_title_short, 'gray',False )

    label_add_to_shortcuts=translation(32516).format(subreddit=subreddit)
    cxm_list=[]

    cxm_list.extend( build_link_in_browser_context_menu_entries(link_url) )
    cxm_list.extend( build_open_browser_to_pair_context_menu_entries(link_url) )

    if cxm_show_comments:
        cxm_list.append((label_view_comments , build_script('listLinksInComment', commentsUrl )  ))

    #more by author
    if GCXM_hasmultipleauthor and cxm_show_by_author:
        cxm_list.append( (label_more_by_author, build_script("listSubReddit", assemble_reddit_filter_string("","/user/"+posted_by+'/submitted'), posted_by)  ) )

    #more from r/subreddit
    if GCXM_hasmultiplesubreddit and cxm_show_by_subreddit:
        cxm_list.append( (label_goto_subreddit, build_script("listSubReddit", assemble_reddit_filter_string("",subreddit), subreddit)  ) )

    #more from domain
    if GCXM_hasmultipledomain and cxm_show_by_domain:
        cxm_list.append( (   label_goto_domain, build_script("listSubReddit", assemble_reddit_filter_string("",'','',domain), domain)  ) )

    #more random (no setting to disable this)
    if any(x in GCXM_actual_url_used_to_generate_these_posts.lower() for x in ['/random','/randnsfw']): #if '/rand' in GCXM_actual_url_used_to_generate_these_posts:
        cxm_list.append( (translation(32511) +' random', build_script('listSubReddit', GCXM_actual_url_used_to_generate_these_posts)) , )  #Reload

    #Autoplay all
    #Autoplay after post_title
    #slideshow
    if cxm_show_autoplay:
        cxm_list.extend( [
                        (translation(32512)    , build_script('autoPlay', GCXM_reddit_query_of_this_gui)),
                        (label_autoplay_after  , build_script('autoPlay', GCXM_reddit_query_of_this_gui.split('&after=')[0]+'&after='+post_id)),
                        ])

    if cxm_show_slideshow:
        cxm_list.append( (translation(32514)    , build_script('autoSlideshow', GCXM_reddit_query_of_this_gui)) )

    #Add %s to shortcuts
    if not subreddit_in_favorites(subreddit) and cxm_show_add_shortcuts:
        cxm_list.append( (label_add_to_shortcuts, build_script("addSubreddit", subreddit)  ) )

    #Add to subreddit/domain filter
    if cxm_show_filter:
        cxm_list.append( (translation(32519).format(colored_subreddit_short), build_script("addtoFilter", subreddit,'','subreddit')  ) )
        cxm_list.append( (translation(32519).format(colored_domain_full)    , build_script("addtoFilter", domain,'','domain')  ) )

    #Search / Other posts with this link
    cxm_list.extend( build_reddit_search_context_menu_entries(GCXM_hasmultiplesubreddit,subreddit,link_url) )

    if cxm_show_youtube_items:
        cxm_list.extend( build_youtube_context_menu_entries('', link_url, video_id=None, title=post_title ))

    cxm_list.extend( build_add_to_favourites_context_menu_entry(title=post_title, onClick_action=onClick_action,thumbnail=thumbnail) )

    return cxm_list

def build_reddit_search_context_menu_entries(hasmultiplesubreddit,subreddit,link_url ):
    cxm_list=[]
    colored_subreddit_full=colored_subreddit( subreddit )
    label_search=translation(32520)
    parts_of_link_url=urlparse.urlparse(link_url)

    if cxm_show_search:
        if GCXM_hasmultiplesubreddit:
            cxm_list.append( (label_search        , build_script("search", '', '')  ) )
        else:
            label_search+=' {}'.format(colored_subreddit_full)
            cxm_list.append( (label_search        , build_script("search", '', subreddit)  ) )
        #NOTE: can't use the entire link_url because it will work for www.reddit.com but not for oauth.reddit.com
        cxm_list.append( (translation(32531)    , build_script("listSubReddit", assemble_reddit_filter_string(parts_of_link_url.path,'','',''), 'Search')  ) )
    return cxm_list

def build_add_to_favourites_context_menu_entry(title, onClick_action, thumbnail=None):
    cxm_list=[]
    if cxm_show_add_to_favorites:
        cxm_list.append( (translation(32530) , build_script("addtoKodiFavorites", onClick_action,title,thumbnail)  ) )
    return cxm_list

def build_youtube_context_menu_entries(previous_listing_was_of_type, youtube_url,video_id=None,title=None,channel_id_from_previous_listing=None,channel_name=None):
    from domains import ClassYoutube
    cxm_list=[]

    try:
        match=re.compile( ClassYoutube.regex, re.I).findall( youtube_url )  #regex='(youtube.com/)|(youtu.be/)|(youtube-nocookie.com/)|(plugin.video.youtube/play)'
        if match:
            if channel_id_from_previous_listing:
                channel_url="https://youtube.com/channel/{}".format(channel_id_from_previous_listing)

            yt=ClassYoutube(youtube_url)
            url_type,id_=yt.get_video_channel_user_or_playlist_id_from_url(youtube_url)

            #log('previous_listing_was_of_type='+repr(previous_listing_was_of_type))

            cxm_list.append( (translation(32523)  , build_script("listRelatedVideo", youtube_url, title, 'related')  ) )

            if previous_listing_was_of_type=='channel':
                #cxm_list.append( (translation(32528)  , build_script("listRelatedVideo", channel_url, title, 'playlists')  ) ) #Playlists in this channel
                pass
            elif previous_listing_was_of_type=='playlist':
                cxm_list.append( (translation(32522)  , build_script("listRelatedVideo", youtube_url, title, 'channel')  ) )
            elif previous_listing_was_of_type=='playlists':
                pass
            else:
                if url_type=='video':
                    video_id=id_
                    cxm_list.append( (translation(32522)  , build_script("listRelatedVideo", youtube_url, title, 'channel')  ) )
                    cxm_list.append( (translation(32525)  , build_script("listRelatedVideo", youtube_url, title, 'links_in_description')  ) )
                elif url_type=='channel':
                    channel_id_from_url=id_
                    cxm_list.append( (translation(32522)  , build_script("listRelatedVideo", youtube_url, title, 'channel')  ) )
                elif url_type=='playlist':
                    #playlist_id_from_url=id_
                    if not previous_listing_was_of_type=='playlists':
                        cxm_list.append( (translation(32526)  , build_script("listRelatedVideo", youtube_url, title, 'playlist')  ) )  #Show playlist (YouTube)
                #elif url_type=='user':
                #    cxm_list.append( (translation(32523)  , build_script("listRelatedVideo", youtube_url, title, 'related')  ) )

            cxm_list.append( (translation(32529)  , build_script("listRelatedVideo", youtube_url, title, 'search')  ) )

            if channel_id_from_previous_listing:
                if not previous_listing_was_of_type=='playlists':
                    cxm_list.append( (translation(32528)  , build_script("listRelatedVideo", channel_url, title, 'playlists')  ) ) #Playlists in this channel
                cxm_list.append( ("{0}{1}".format(translation(32527),channel_name), build_script("addSubreddit", "{0}[{1}]".format(channel_url,channel_name))  ) )

            #Search reddit for this video ID"  #url+= "/search.json?q=" + urllib.quote_plus(search_string)
            if video_id:
                cxm_list.append( (translation(32524)    , build_script("listSubReddit", assemble_reddit_filter_string(video_id,'','',''), 'Search')  ) )

    except Exception as e:
        log('  EXCEPTION build_youtube_context_menu_entries():'+str(e))

    return cxm_list

#called from reddit_comment_worker()
def build_reddit_context_menu_entries(url):
    from domains import ClassReddit
    cxm_list=[]
    match=re.compile( ClassReddit.regex, re.I).findall( url ) 
    if match:
        subreddit=ClassReddit.get_video_id(url)
        if subreddit: # and cxm_show_by_subreddit:  Go to r/{subreddit}
            cxm_list.append( (translation(32508).format(subreddit=subreddit),
                              build_script("listSubReddit", assemble_reddit_filter_string("",subreddit), subreddit)  ) )

    return cxm_list

#Open links in browser
def build_link_in_browser_context_menu_entries(url):
    label_html_to_text=translation(32502)
    label_open_browser=translation(32503)
    cxm_list=[]
    if cxm_show_html_to_text:
        cxm_list.append((label_html_to_text , build_script('readHTML', url)         ))

    if cxm_show_open_browser:
        cxm_list.append((label_open_browser , build_script('openBrowser', url)         ))

    return cxm_list

def build_open_browser_to_pair_context_menu_entries(url):
    cxm_list=[]
    lcase_url=url.lower()
    if "openload.co" in lcase_url:
        pairing_url="https://olpair.com"
    if "thevideo.me" in lcase_url:
        pairing_url="https://thevideo.me/pair"

        if cxm_show_open_browser:
            cxm_list.append(("Go to [B][COLOR=cyan]{}[/COLOR][/B]".format(pairing_url), build_script('openBrowser', pairing_url)         ))

    return cxm_list

if __name__ == '__main__':
    pass