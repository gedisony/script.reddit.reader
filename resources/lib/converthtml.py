
#import re
import requests 
import bs4
import pprint

from default import log

def parseHTML(link_url, a, b):
    
    log('parseHTML')

    page = requests.get( link_url )
    #log( repr( page.text ))
    
    soup = bs4.BeautifulSoup(page.text) 
    log( repr( soup.title ))
    
    #log( repr(soup.p) )


    p=soup.find_all('p')
    log( repr(p) )
    
    text = soup.get_text()
    tl=text.split('\n')
    
    log( pprint.pformat(tl) )

if __name__ == '__main__':
    pass
