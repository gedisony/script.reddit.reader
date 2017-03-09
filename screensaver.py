#!/usr/bin/python
# -*- coding: utf-8 -*-
import xbmc
import xbmcaddon

import urllib

addon = xbmcaddon.Addon()

default_frontpage    = addon.getSetting("screensaver_subreddit")

from resources.lib.utils import assemble_reddit_filter_string, this_is_a_multihub


if __name__ == '__main__':
    xbmc.log('starting reddit_reader screensaver',xbmc.LOGNOTICE)
    reddit_url=assemble_reddit_filter_string(search_string='',subreddit=default_frontpage )

    #xbmc.executescript("script.reddit.reader,mode=autoSlideshow&url=https%3A%2F%2Fwww.reddit.com%2F.json%3F%26nsfw%3Ano%2B%26limit%3D10&name=&type=")
    xbmc.executebuiltin("RunAddon(script.reddit.reader,mode=autoSlideshow&url=%s&name=&type=%s)" %(urllib.quote_plus(reddit_url), 'screensaver') )


