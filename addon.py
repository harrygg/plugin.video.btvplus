import sys, os
from xbmcswift2 import Plugin
from resources.lib.scrapper import Scrapper

#append_pydev_remote_debugger
__DEBUG__ = False
if __DEBUG__:
  sys.path.append(os.environ['PYSRC'])
  import pydevd
  pydevd.settrace('localhost', stdoutToServer=False, stderrToServer=False)
#end_append_pydev_remote_debugger	

reload(sys)  
sys.setdefaultencoding('utf8')
plugin = Plugin()
r = Scrapper(plugin)

@plugin.route('/')
def index():
	r.update('browse', 'Categories')
	items = r.get_navigation()
	return build_list(items)

@plugin.route('/products/<url>/')
def show_products(url):
	if 'live' in url:
		products = get_live_products(url)
	else:
		products = get_products(url)
	mode = 500 if 'produkt/seriali' not in url and 'live' not in url else 50
	return plugin.finish(products, view_mode=mode)
	
@plugin.route('/stream/<url>/')
def show_streams(url):
	return plugin.finish(get_streams(url), view_mode=50)

@plugin.route('/play/<url>/')
def play(url):
	plugin.set_resolved_url(url)

###@plugin.cached(60)
def get_products(url):
	items = r.get_products(url)
	return build_list(items)

#not cahced due to EPG constant changes
def get_live_products(url):
	items = r.get_products(url)
	return build_list(items)
	
###@plugin.cached(60)
def get_streams(url):
	items = r.get_streams(url)
	return build_list(items)

def build_list(items):
	return	[{
		'label': i.title, 
		'path': i.url, 
		'icon': i.logo,
		'thumbnail': i.logo,
		'properties': {'fanart_image': i.logo}, 
		'is_playable': i.playable
		} for i in items]

### Run plugin
if __name__ == '__main__':
    plugin.run()
