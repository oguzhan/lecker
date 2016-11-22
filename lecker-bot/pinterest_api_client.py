#!/usr/bin/env python

## Forked from: https://github.com/creotiv/python-pinterest-api/blob/master/pinterest.py ##

import time
import urllib
import urllib2
import re
import cookielib
import cStringIO
import gzip
import sys
import json

class Pinterest(object):

    def __init__(self,cookie=None):
        self.cookieJar           = cookie
        self.csrfmiddlewaretoken = None
        self.http_timeout        = 15
        self.boards              = {}

    def getCookies(self):
        return self.cookieJar

    def search(self,query):
        """
        Searches according to given parameters like it does on Pinterest.
        """
        query = urllib.quote(query)
        bookmark = ''

        url =  'http://www.pinterest.com/resource/SearchResource/get/?source_url=%2Fsearch%2Fpins%2F%3Fq%3Dart%26rs%3Dac%26len%3D1&data=%7B%22options%22%3A%7B%22show_scope_selector%22%3Anull%2C%22scope%22%3A%22pins%22%2C%22constraint_string%22%3Anull%2C%22bookmarks%22%3A%5B%22'+bookmark+'%22%5D%2C%22query%22%3A%22'+query+'%22%7D%2C%22context%22%3A%7B%22app_version%22%3A%22da919e8%22%2C%22https_exp%22%3Afalse%7D%2C%22module%22%3A%7B%22name%22%3A%22GridItems%22%2C%22options%22%3A%7B%22scrollable%22%3Atrue%2C%22show_grid_footer%22%3Atrue%2C%22centered%22%3Atrue%2C%22reflow_all%22%3Atrue%2C%22virtualize%22%3Atrue%2C%22item_options%22%3A%7B%22show_pinner%22%3Atrue%2C%22show_pinned_from%22%3Afalse%2C%22show_board%22%3Atrue%7D%2C%22layout%22%3A%22variable_height%22%2C%22track_item_impressions%22%3Atrue%7D%7D%2C%22append%22%3Atrue%2C%22error_strategy%22%3A1%7D&module_path=App()%3EHeader()%3Eui.SearchForm()%3Eui.TypeaheadField(enable_recent_queries%3Dtrue%2C+name%3Dq%2C+view_type%3Dsearch%2C+class_name%3DinHeader%2C+prefetch_on_focus%3Dtrue%2C+value%3D%22%22%2C+populate_on_result_highlight%3Dtrue%2C+search_delay%3D0%2C+search_on_focus%3Dtrue%2C+placeholder%3DSearch%2C+tags%3Dautocomplete)&_='+str(int(time.time())*10*10*10)

        res,headers,cookies = self.request(url, referrer='https://pinterest.com/search/pins/?q=%s' % query, ajax=True)

        data = json.loads(res)
        posts = data['module']['tree']['children']
        res = []
        for p in posts:
            desc = ''
            for i in p['children']:
                if i['id'] == 'sendPinButton':
                    desc = i['options']['module']['options']['object_description']
                    break
            res.append({
                'id': p['id']
                ,'img': p['data']['images']['orig']['url']
                ,'link': p['data']['link']
                ,'desc': desc
            })

        return res


    def request(self,url,post_data=None,referrer='http://google.com/',ajax=False):
        """
        Download url with urllib2.

        Return downloaded data
        """
        handlers = []

        urllib2.HTTPRedirectHandler.max_redirections = 10

        if not self.cookieJar:
            self.cookieJar = cookielib.CookieJar()

        cookie_handler = urllib2.HTTPCookieProcessor(self.cookieJar)
        handlers.append(cookie_handler)
        opener = urllib2.build_opener(*handlers)

        opener.addheaders = [
            ('User-Agent', 'Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.1 \
                      (KHTML, like Gecko) Chrome/21.0.1180.89 Safari/537.1'),
            ('Accept', 'image/png,image/*;q=0.8,*/*;q=0.5'),
            ('Accept-Language', 'en-us,en;q=0.5'),
            ('Accept-Encoding', 'gzip,deflate'),
            ('Accept-Charset', 'ISO-8859-1,utf-8;q=0.7,*;q=0.7'),
            ('Keep-Alive', '3600'),
            ('Host','www.pinterest.com'),
            ('Origin','http://www.pinterest.com'),
            ('Connection', 'keep-alive'),
            ('Referer', referrer),
            ('X-NEW-APP','1')
        ]

        if ajax:
            opener.addheaders.append(('X-Requested-With','XMLHttpRequest'))
        if self.csrfmiddlewaretoken:
            opener.addheaders.append(('X-CSRFToken',self.csrfmiddlewaretoken))

        error_happen = False
        html = ''

        try:
            req = urllib2.Request(url, post_data)
            r = opener.open(req,timeout=self.http_timeout)
            html = r.read()
        except DownloadTimeoutException,e:
            sys.exc_clear()
            error_happen = e
        except Exception,e:
            sys.exc_clear()
            error_happen = e

        if error_happen:
            return error_happen,{},{}

        headers = r.info()
        # If we get gzipped data the unzip it
        if ('Content-Encoding' in headers.keys() and headers['Content-Encoding']=='gzip') or \
           ('content-encoding' in headers.keys() and headers['content-encoding']=='gzip'):
            data = cStringIO.StringIO(html)
            gzipper = gzip.GzipFile(fileobj=data)
            # Some servers may return gzip header, but not zip data.
            try:
                html_unzipped = gzipper.read()
            except:
                sys.exc_clear()
            else:
                html = html_unzipped

        cookies = {cookie.name:cookie.value for cookie in self.cookieJar}
        self.csrfmiddlewaretoken = cookies['csrftoken']

        return html,headers,cookies
