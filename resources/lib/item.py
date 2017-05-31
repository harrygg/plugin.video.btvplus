from mode import Mode

class Item:
	stripped_text = ['bTV Новините в', 'bTV Новините - ', 'емисия ', 
									'България търси талант - ', 'Мама готви по-добре - ']

	def __init__(self, title, url = '', logo = '', func = Mode.show_products, views = 0):
		self.title = title.decode('utf-8')
		self.url = url
		self.logo = logo
		self.func = func
		self.playable = func == Mode.play
		self.views = views
		self._strip_extra_text()
	
	def _strip_extra_text(self):
		for text in self.stripped_text:
			self.title = self.title.replace(text, '')
