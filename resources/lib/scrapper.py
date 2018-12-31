import sys, re, base64, urllib2, urlparse, xbmc, requests, xbmcaddon, time
from bs4 import BeautifulSoup
from item import Item
from mode import Mode
from ga import ga

reload(sys)  
sys.setdefaultencoding('utf8')

plugin = None

class Scrapper:
  host = base64.b64decode("aHR0cDovL2J0dnBsdXMuYmcv")
  suburl = None
  url = None
  ua = None
  addon = xbmcaddon.Addon()
  user_agents = { 
    'pc': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.0 Safari/537.36', 
    'mobile': 'Dalvik/2.1.0 (Linux; U; Android 5.0;'
  }
  response = ''
  
  def __init__(self, plugin, ua='mobile'):
    self.plugin = plugin
    self.ua = self.user_agents[ua]
    
  def _parse_url(self, url):
    try:
      if self.host not in url:
        self.suburl = url
        self.url = urlparse.urljoin(self.host, url)
      else:
        self.url = url
        comps = urlparse.urlparse(url) 
        self.suburl = comps.path
    except Exception, er:
      self.plugin.log.error(str(er))
    
  def _do_request(self, url = ''):
    self._parse_url(url)
    try:    
      req = urllib2.Request(self.url)
      req.add_header('User-agent', self.ua)
      r = urllib2.urlopen(req)
      self.response = r.read()
      #self.plugin.log.info('self.response: ' + self.response)
      self.soup = BeautifulSoup(self.response, 'html5lib')
    except Exception, er:
      self.plugin.log.error(str(er))
  
  def get_navigation(self):
    items = []
    self._do_request()
    try:
      #el = self.soup.find(UL, id='tabs_links')
      el = self.soup.find(UL)
      links = el.find_all(A)
      for link in links:
        text = link.get_text()
        if 'Програма' not in text:
          item = Item(text, self.plugin.url_for(Mode.show_products, url=link[HREF].replace('/', '')))
          items.append(item)
    except Exception, er:
      self.plugin.log.error(str(er))
    finally:
      return items

  def get_products(self, url):
    products = []
    seasons = False
    self._do_request(url)
    try:
      self.plugin.log.error(str(self.suburl))
      if 'live' in self.suburl:
        products = self.get_live_products()
      elif 'produkt/seriali' in self.suburl:
        products = self.get_episodes()
      else:
        if 'produkt/predavaniya' in self.suburl:
          el = self.soup.find(DIV, class_="parent-products listing")
        else:
          el = self.soup.find(DIV, class_='bg-order')
          if not el:
            el = self.soup.find(DIV, class_='news-sl')

        imgs = el.find_all(IMG)
        regex = ''.join(filter(lambda x: not x.isdigit(), self.suburl)) #strip ID from suburl
        links = el.find_all(A, {HREF: re.compile(regex)})
        #links = el.find_all(DIV, class_='item_title')
        #if len(imgs) == len(links): #links are twice as much 
        for i in range(0, len(imgs)):
          if len(imgs) == len(links):
            j = i
            title = ' '
          else:
            j = i*2+1
            title = links[j].get_text()
          url = links[j][HREF]
          item = Item(title, url, HTTP + imgs[i][SRC])
          if not seasons and ('produkt/predavaniya' in self.suburl or 'novini' in self.suburl):
            item.func = Mode.show_streams
          if not item.playable: #if not direct link to resource, add direct link to resource
            item.url = self.plugin.url_for(item.func, url=item.url)
          products.append(item)
        #pagination:
        self._add_pagination(products)

    except Exception, er:
      self.plugin.log.error(str(er))
    finally:
      return products


  def _add_pagination(self, products):
    try:
      el = self.soup.find(LI, class_='page next')
      if el != None:
        item = Item(self.plugin.get_string(32001), self.plugin.url_for(Mode.show_products, url=el.a[HREF]))
        products.append(item)
    except Exception, er:
      self.plugin.log.error(str(er))

  def get_streams(self, url):
    items = []
    self._do_request(url)
    try:
      title = self.soup.title.get_text()
      m = self._find('src[:=\s\'\"]+(.*mp4)')
      if len(m)>0:
        stream = 'http:'+ m[0]
        m = self._find('poster[:\s\'"]+(http.*jpg)')
        logo = '' if len(m) == 0 else m[0]
        
        item = Item(title, stream, logo, Mode.play) 
        try: 
          item.views = self.soup.find(I, class_='icon-eye').findNext(SPAN).get_text()
          if item.views > 0:
            item.title += ' (%s гледания)' % item.views
        except: pass
      else:
        er = self.soup.find(DIV, class_='wrapper_voyo_content')
        title = self.plugin.get_string(32010) if er != None else self.plugin.get_string(32011)
        item = Item('[COLOR red]%s[/COLOR]' % title)

      items.append(item)
    except Exception, er:
      self.plugin.log.error(str(er))
    finally:
      return items

  def get_live_products(self):
    streams = []
    headers = {}
    s = requests.session()

    try:
      body = { "username": self.addon.getSetting("btv_username"), "password": self.addon.getSetting("btv_password") }
      headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
      r = s.post(base64.b64decode('aHR0cHM6Ly9idHZwbHVzLmJnL2xiaW4vc29jaWFsL2xvZ2luLnBocA=='), headers=headers, data=body)
      if r.json()["resp"] != "success":
        self.plugin.log.error("Unable to login to btv.bg")
        return None
        
      url = base64.b64decode('aHR0cHM6Ly9idHZwbHVzLmJnL2xiaW4vdjMvYnR2cGx1cy9wbGF5ZXJfY29uZmlnLnBocD9tZWRpYV9pZD0yMTEwMzgzNjI1Jl89JXM=')
      url = url % str(time.time() * 100)
      r = s.get(url, headers=headers)
      xbmc.log(r.text, 4)
      m = re.compile('(http.*\.m3u.*?)[\s\'"\\\\]+').findall(r.text)
      if len(m) > 0:
        stream = m[0].replace('\/', '/')
        item = Item("[B]bTV[/B]", stream, '', Mode.play)
        streams.append(item)
      else:
        xbmc.log("No match for playlist url found", xbmc.LOGNOTICE)
      
      #xbmc.log('Намерени %s съвпадения в %s' % (len(m), url), xbmc.LOGNOTICE)
      xbmc.log('Извлечен видео поток %s' % stream, xbmc.LOGNOTICE)
      
    except Exception as er:
      xbmc.log(str(er), 4)
    return streams
  
  def _find(self, regex):
    return re.compile(regex).findall(self.response)
    
  def _get_rtmp_args(self):
    try: swfUrl = urlparse.urljoin(self.host, self._find('url[\'"\s:]+(.*swf)')[0])
    except: swfUrl = urlparse.urljoin(self.host, '/static/bg/shared/app/flowplayer/flowplayer.rtmp-3.2.13.swf')
    try: 
      matches = self._find('(rtmp://.*[\'"]+.*[\'"]+)')
      tcurl = matches[0]
    except: tcurl = 'rtmp://hls.btv.bg.sof.cmestatic.com:80/alpha'
    try: playpath = re.compile('clip\s*:.*?url\s*:\s*[\'"](.+?)[\'"]', re.DOTALL).findall(self.response)[0]
    except: playpath = 'alpha'
    return "%s app=%s playpath=%s swfUrl=%s pageUrl=%s live=true" % (tcurl, playpath, playpath, swfUrl, self.host)
  
  def _get_m3u_args(self):
    try: 
      matches = self._find('http.*[\'"]+(.*?m3u8)')
      m3u = 'http://%s|User-agent=%s' % (matches[0], self.ua)
    except: m3u = "http://hls.btv.bg.sof.cmestatic.com/alpha/alpha/playlist.m3u8|User-agent=%s" % self.ua
    finally: return m3u
    
  def _get_epg_event(self):
    name = ''
    try:
      items = self.soup.find_all(LI, class_='item')
      for i in range(0, len(items)):
        start_time = items[i].span.get_text()
        end_time = items[i+1].span.get_text()
        try: #get the EET time
          from pytz import timezone
          from datetime import datetime
          eet = timezone('Europe/Sofia')
          date = datetime.now(eet)
          now = int('%s%s' % (date.hour, date.minute))
        except:
          import time
          now = int(time.strftime('%H%M'))
        #self.plugin.log.info(now)

        if now >= int(start_time.replace(':','')) and now < int(end_time.replace(':','')):
          name = '[COLOR green]%s [B]%s[/B][/COLOR]' % (self.plugin.get_string(32012), items[i].h1.get_text())
          if i+1 <= len(items): #if there is next item
            name += (' | [COLOR brown]%s (%sч.): [B]%s[/B][/COLOR]' % (self.plugin.get_string(32013), end_time, items[i+1].h1.get_text()))
          #return
    except Exception, er:
      self.plugin.log.error(str(er))
    finally:
      return name
          
          
  def get_episodes(self):
    items = []
    
    def _random_color(n):
      return 'gold' if n % 2 == 0 else 'brown' 
    try:
      seasons = self.soup.find_all(DIV, class_='season_wrapper')
      if len(seasons) > 0:
        n = 0
        for season in seasons:
          n += 1
          series = season.find_all(SPAN, class_='episode_title')
          expires = season.find_all(SPAN, class_='episode_expire')
          try: image = season.find(DIV, class_='season_image').img[SRC]
          except: image = ''
          if len(series) == len(expires):
            for i in range(0, len(series)):
              url = series[i].a[HREF]
              color = 'red' if 'неактивен' in expires[i].get_text() else 'green'
              expires_text = '[COLOR %s]%s[/COLOR]' % (color, expires[i].get_text())            
              title = "%s | %s" % (series[i].a.get_text().lstrip().rstrip(), expires_text)
              if len(seasons) > 1:
                title = '[COLOR %s]%s %s[/COLOR] | %s' % (self.plugin.get_string(32014), _random_color(n), n, title)
              item = Item(title, self.plugin.url_for(Mode.show_streams, url=url), image, Mode.show_streams)
              items.append(item)
      else: # There are no seasons
        wrapper = self.soup.find(DIV, class_='parent-products')
        if wrapper:
          series  = wrapper.find_all(LI)
          self.plugin.log.error("series: "+ str(len(series)))
          for serie in series:
            link = serie.find_all(A)[1]
            title = link.get_text()
            url = link[HREF]
            image = serie.img[SRC]
            item = Item(title, self.plugin.url_for(Mode.show_streams, url=url), image, Mode.show_streams)
            items.append(item)
    except Exception, er:
      self.plugin.log.error(str(er))
    finally:
      return items
      

  def update(self, name, location, crash=None):
    p = {}
    p['an'] = self.plugin.name
    p['av'] = self.plugin.addon.getAddonInfo('version')
    p['ec'] = 'Addon actions'
    p['ea'] = name
    p['ev'] = '1'
    p['ul'] = xbmc.getLanguage()
    p['cd'] = location
    ga('UA-79422131-4').update(p, crash)
    
        
###Literals
DIV = 'div'
SPAN = 'span'
HREF = 'href'
SRC = 'src'
UL = 'ul'
LI = 'li'
A = 'a'
IMG = 'img'
I = 'i'
HTTP = 'http:'