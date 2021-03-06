import os, sys, requests, string, json, logging
from datetime import datetime, timedelta
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import matplotlib.pyplot as plt	
from collections import Counter

dirname = os.path.dirname(os.path.abspath(sys.argv[0]))
logging.basicConfig(filename="{}/logging.log".format(dirname), level=logging.ERROR)


class InfoContainer:

	def __init__(self, container_type, manager, ticker_id):
		self._container_type = container_type
		self.manager = manager
		self._ticker_id = ticker_id
		self._data_lists = {}
		self._elements = 0
		self._file_init()
		self._errors = False

		for value in self._data_lists.values():
			value.sort()

	def __str__(self):
		return "{}-{}".format(self._container_type, self._ticker_id)

	def _file_init(self):
		# Make folder if it does not exists
		if not os.path.exists(self.folder_path()):
			os.makedirs(self.folder_path())

		# Make file if it does not exists
		if not os.path.isfile(self.file_path()):
			open(self.file_path(), 'w').close()

		# Read data in file
		with open(self.file_path()) as file:
			for line in file:
				data = line.strip().split(",")
				i = 1
				while i < len(data):
					try:
						date = datetime.strptime("{} {}".format(data[0], data[i]), "%y/%m/%d %H:%M:%S")
					except ValueError as ve:
						date = datetime.strptime("{} {}".format(data[0], data[i]), "%Y/%m/%d %H:%M:%S")
					
					try:
						self._add_data_to_lists(i, date, data)					
					except Exception as e:
						print("Error in {}:{}._add_data_to_lists: {}".format(self._container_type, self._ticker_id, e))
						logging.error("Error in {}:{}._add_data_to_lists: {}".format(self._container_type, self._ticker_id, e))
						self._errors = True
						return
					i += self._lines_per_update()
					self._elements += 1

	def get_ticker_id(self):
		return self._ticker_id

	def get_container_type(self):
		return self._container_type

	def prettyprint(self):
		print("{} - {}".format(self._container_type, self._ticker_id))
		for key, value in self._data_lists.items():
			print(key)
			
			year = -1
			month = -1
			day = -1
			for item in value:
				date = item[0]
				if date.year != year or date.month != month or date.day != day:
					year = date.year
					month = date.month
					day = date.day
					print("\t * {}-{}-{}".format(year, month, day))
				print("\t\t   {}:{}:{} - {}".format(date.hour, date.minute, date.second, item[1]))
			
	def write_to_file(self):
		if self._errors:
			print("Previosly encountered error. Returning.")
			logging.error("Previosly encountered error. Returning.")
			return
		try:		
			s = ""
			year = -1
			month = -1
			day = -1
			dates = next(iter(self._data_lists.values()))
			for i in range(0, self._elements):
				date = dates[i][0]
				if date.year != year or date.month != month or date.day != day:
					if year != -1:
						s += "\n"
					year = date.year
					month = date.month
					day = date.day
					s+= "{}/{}/{}".format(year, month, day)
				
				info = self._get_write_info(i)
				s += "," + info
				#print(info)
			open(self.file_path(), 'w').write(s)
		except Exception as e:
			print("Error in {}:{}.write_to_file: {}".format(self._container_type, self._ticker_id, e))
			logging.error("Error in {}:{}.write_to_file: {}".format(self._container_type, self._ticker_id, e))
	# General method for plotting simple containers. 
	# Must be overridden for most containers to work.
	def plot(self, savefile=None):
		for key, data_list in self._data_lists.items():
			plt.title(str(self))
			plt.ylabel(key)
			plt.xlabel("date")
			plt.plot(*zip(*data_list))
			plt.gcf().autofmt_xdate()
		
		self.save_plot(savefile)


	def save_plot(self, savefile):
		if savefile:
			path = os.path.join(self.directory_location(), 'plots')
			if not os.path.exists(path):
				os.makedirs(path)
			plt.savefig(os.path.join(path, savefile+'.png'))
			plt.savefig(os.path.join(path, savefile+'.pdf'))
			plt.close("all")
		else:
			plt.show()


	def update(self):
		try:
			date = datetime.now()
			data = self._get_update_data(date)
			if data == None:
				return
			assert self._lines_per_update() - 1 == len(data), "{} update expected {} data elements, but got {}.".format(self._ticker_id, self._lines_per_update() - 1, len(data))
			data = ["",""] + data
			self._add_data_to_lists(1, date, data)
			self._elements += 1
		except Exception as e:
			print("Error in {}:{}.update: {}".format(self._container_type, self._ticker_id, e))
			logging.error("Error in {}:{}.update: {}".format(self._container_type, self._ticker_id, e))
			self._errors = True
	'''
		returns: a list of information which is passed to _add_data_to_lists
	'''
	def _get_update_data(self, date):
		raise NotImplementedError
		
	def _get_write_info(self, i):
		raise NotImplementedError

	def _add_data_to_lists(self, i, date, data):
		raise NotImplementedError

	def _lines_per_update(self):
		raise NotImplementedError

	def directory_location(self):
		return os.path.dirname(os.path.abspath(sys.argv[0]))

	def folder_location(self):
		raise NotImplementedError

	def folder_path(self):
		return os.path.join(self.directory_location(), self.folder_location())

	def file_path(self):
		return os.path.join(self.folder_path(), self._ticker_id)

	def get_date(self, date_num):
		return datetime.strftime(datetime.now() + timedelta(date_num), "%x")

class SubredditContainer(InfoContainer):

	def __init__(self, parent_container, name):
		self._followers = []

		super().__init__("Subreddit", parent_container, name)

		self._data_lists["followers"] = self._followers
	
	def _get_update_data(self, date):
		request_string = 'http://www.reddit.com/r/' + self._ticker_id +'/about/.json'
		response = requests.get(request_string, headers = {'User-agent': 'floffbot'})
		data = response.json()
		return [data['data']['subscribers']]

	def _add_data_to_lists(self, i, date, data):
		info = (date, int(data[i+1]))
		self._followers.append(info)

	def _lines_per_update(self):
		return 2

	def _get_write_info(self, i):
		info = self._followers[i]
		date = info[0]
		return "{}:{}:{},{}".format(date.hour, date.minute, date.second, info[1])

	def folder_location(self):
		return "subred_data/"

	def folder_path(self):
		return os.path.join(self.directory_location(), self.folder_location())

class MarketcapContainer(InfoContainer):

	def __init__(self, parent_container, name):
		self._usd_value = []
		self._btc_value = []

		super().__init__("Marketcap", parent_container, name)

		self._data_lists["usd_value"] = self._usd_value
		self._data_lists["btc_value"] = self._btc_value

	def _get_update_data(self, date):
		data = self.manager.get_marketcap_data(self._ticker_id)
		if data == None:
			return data
		return [data['BTC'], data['USD']]

	def _add_data_to_lists(self, i, date, data):
			btc = (date, float(data[i+1]))
			usd = (date, float(data[i+2]))
			self._btc_value.append(btc)
			self._usd_value.append(usd)

	def _lines_per_update(self):
		return 3

	def _get_write_info(self, i):
		btc_info = self._btc_value[i]
		usd_info = self._usd_value[i]
		date = btc_info[0]
		return "{}:{}:{},{},{}".format(date.hour, date.minute, date.second, btc_info[1], usd_info[1])

	def folder_location(self):
		return "marketcap_data/"

	def folder_path(self):
		return os.path.join(self.directory_location(), self.folder_location())

	def plot(self, savefile=None):
		fig = plt.figure()

		host = fig.add_subplot(111)

		par1 = host.twinx()
		host.set_title(str(self))
		host.set_xlabel("date")
		host.set_ylabel("Bitcoin value")
		par1.set_ylabel("Dollar value")

		p1, = host.plot(*zip(*self._data_lists["btc_value"]), color='orange', label="{}/BTC".format(self._ticker_id))
		p2, = par1.plot(*zip(*self._data_lists["usd_value"]), color='blue', label="{}/USD".format(self._ticker_id))
		plt.gcf().autofmt_xdate()
		lns = [p1, p2]
		host.legend(handles=lns, loc='best')
		host.yaxis.label.set_color(p1.get_color())
		par1.yaxis.label.set_color(p2.get_color())
		self.save_plot(savefile)

class SubredditSentimentAverageContainer(InfoContainer):
	def __init__(self, parent_container, name):
		self._title_sentiment = []
		self._text_sentiment = []
		self._comment_sentiment = []
		self._limit = 50 # 25 / 50 / 75 / 100

		super().__init__("SubredditSentimentAverage", parent_container, name)

		self._data_lists["title_sentiment"] = self._title_sentiment
		self._data_lists["text_sentiment"] = self._text_sentiment
		self._data_lists["comment_sentiment"] = self._comment_sentiment
		self._analyser = SentimentIntensityAnalyzer()	

	def _sentiment_analyzer_scores(self, sentence):
		score = self._analyser.polarity_scores(sentence)
		return score
	
	def plot(self, savefile=None):
		
		tot_neg = []
		tot_pos = []
		start = True
		for key in ["title_sentiment", "text_sentiment", "comment_sentiment"]:
			tit_neg = []
			tit_neu = []
			tit_pos = []
			tit_compound = []
			tit_neg_neu_pos = []
			
			i = 0
			for data in self._data_lists[key]:
				tit_neg.append((data[0], float(data[1]["neg"])))
				tit_neu.append((data[0], float(data[1]["neu"])))
				tit_pos.append((data[0], float(data[1]["pos"])))
				tit_compound.append((data[0], float(data[1]["compound"])))
				if start:
					tot_neg.append((data[0], float(data[1]["neg"])))
					tot_pos.append((data[0], float(data[1]["pos"])))
				else:
					tot_neg[i] = (tot_neg[i][0], tot_neg[i][1] + float(data[1]["neg"]))
					tot_pos[i] = (tot_pos[i][0], tot_pos[i][1] + float(data[1]["pos"]))
				
				i += 1

			start = False
				
			fig = plt.figure()

			host = fig.add_subplot(111)
			host.set_ylim(0,1)

			par1 = host.twinx()
			host.set_title(str(self) + " " + key)
			host.set_xlabel("date")
			host.set_ylabel("Pos/Neg trend")
			#par1.set_ylabel("neu")

			p1, = host.plot(*zip(*tit_neg), color='red', label="Negative")
			p2, = host.plot(*zip(*tit_pos), color='green', label="Positive")
			#p3, = par1.plot(*zip(*tit_compound), color='gray', label="Compound title")
			plt.gcf().autofmt_xdate()
			lns = [p1, p2]
			host.legend(handles=lns, loc='best')
			host.yaxis.label.set_color(p1.get_color())
			#par1.yaxis.label.set_color(p3.get_color())
			self.save_plot(savefile + "_" + key)

		fig = plt.figure()

		host = fig.add_subplot(111)
		host.set_ylim(0,1)

		par1 = host.twinx()
		host.set_title(str(self) + " " + "total")
		host.set_xlabel("date")
		host.set_ylabel("Pos/Neg trend")
		#par1.set_ylabel("neu")

		p1, = host.plot(*zip(*tot_neg), color='red', label="Negative")
		p2, = host.plot(*zip(*tot_pos), color='green', label="Positive")
		#p3, = par1.plot(*zip(*tit_compound), color='gray', label="Compound title")
		plt.gcf().autofmt_xdate()
		lns = [p1, p2]
		host.legend(handles=lns, loc='best')
		host.yaxis.label.set_color(p1.get_color())
		#par1.yaxis.label.set_color(p3.get_color())
		self.save_plot(savefile + "_" + "total")

	def _average_scores(self, score1, score2):
		if not score1 or not score2:
			return score2

		score_fin = {}
		score_fin['neg'] = (score1['neg'] + score2['neg']) / 2
		score_fin['neu'] = (score1['neu'] + score2['neu']) / 2
		score_fin['pos'] = (score1['pos'] + score2['pos']) / 2
		score_fin['compound'] = (score1['compound'] + score2['compound']) / 2
		return score_fin

	def _score_to_list(self, score):
		if not score:
			return [0,0,0,0]

		return [score['neg'], score['neu'], score['pos'], score['compound']]

	def _get_update_data(self, date):
		request_string = 'https://www.reddit.com/r/{}/new/.json?limit=50'.format(self._ticker_id)
		response = requests.get(request_string, headers = {'User-agent': 'floffbot'})
		data = response.json()
		average_selftext = None
		average_title = None
		average_comment = None
		for post in data['data']['children']:
			selftext = post['data']['selftext']
			title = post['data']['title']
			url = "https://www.reddit.com" + post['data']['permalink'] + ".json"

			url_response = requests.get(url, headers = {'User-agent': 'floffbot'})
			url_data = url_response.json()
			average_comment_score = None
			for url_comment in url_data[1]['data']['children']:
				try:
					comment = url_comment['data']['body']
					comment_score = self._sentiment_analyzer_scores(comment)
				
					average_comment_score = self._average_scores(average_comment_score, comment_score)
				except:
					continue

			selftext_score = self._sentiment_analyzer_scores(selftext)
			title_score = self._sentiment_analyzer_scores(title)

			average_selftext = self._average_scores(average_selftext, selftext_score)
			average_title = self._average_scores(average_title, title_score)
			average_comment = self._average_scores(average_comment, average_comment_score)
			

		return self._score_to_list(average_title) + self._score_to_list(average_selftext) + self._score_to_list(average_comment)

	def _add_data_to_lists(self, i, date, data):
		
		title = (date,{'neg':data[i+1], 'neu':data[i+2], 'pos': data[i+3], 'compound': data[i+4]})
		selftext = (date,{'neg':data[i+5], 'neu':data[i+6], 'pos': data[i+7], 'compound': data[i+8]})
		comment = (date,{'neg':data[i+9], 'neu':data[i+10], 'pos': data[i+11], 'compound': data[i+12]})
		
		self._title_sentiment.append(title)
		self._text_sentiment.append(selftext)
		self._comment_sentiment.append(comment)

	def _lines_per_update(self):
		return 13

	def _score_to_csv(self, score):
		return "{},{},{},{}".format(score['neg'], score['neu'], score['pos'], score['compound'])

	def _get_write_info(self, i):
		title_info = self._title_sentiment[i]
		text_info = self._text_sentiment[i]
		comment_info = self._comment_sentiment[i]

		date = title_info[0]
		title_csv = self._score_to_csv(title_info[1])
		text_csv = self._score_to_csv(text_info[1])
		comment_csv = self._score_to_csv(comment_info[1])

		return "{}:{}:{},{},{},{}".format(date.hour, date.minute, date.second, title_csv, text_csv, comment_csv)



	def folder_location(self):
		return "subreddit_sentiment_average"

	def folder_path(self):
		return os.path.join(self.directory_location(), self.folder_location())

class HypePredictor(InfoContainer):

	def __init__(self, parent_container, name):
		
		self._limit = 100
		self._watchlist_file = os.path.join(self.directory_location(), "all_cryptos.csv")
		self._posts = []
		self._comments = []
		super().__init__("HypePredictor", parent_container, name)
		
		self._data_lists["posts"] = self._posts
		self._data_lists["comments"] = self._comments
		# Name : CODE		
		self._watchlist = {}
		with open(self._watchlist_file) as file:
			for line in file:
				line = line.lower()
				data = line.strip().split(",")
				code = data[0]
				for word in data:
					self._watchlist[word] = code


	def _get_update_data(self, date):
		total = Counter({})
		total_comments = Counter({})


		request_string = 'https://www.reddit.com/r/{}/new/.json?limit={}'.format(self._ticker_id, self._limit)
		response = requests.get(request_string, headers = {'User-agent': 'floffbot'})
		data = response.json()

		
		for post in data['data']['children']:
			selftext = post['data']['selftext']
			selftext_count = Counter(self.countwords(selftext.lower()))
			title = post['data']['title']
			title_count = Counter(self.countwords(title.lower()))

			total += selftext_count + title_count
			url = "https://www.reddit.com" + post['data']['permalink'] + ".json"

			url_response = requests.get(url, headers = {'User-agent': 'floffbot'})
			url_data = url_response.json()
			
			for url_comment in url_data[1]['data']['children']:
				try:
					comment = url_comment['data']['body']
					#comment_score = self._sentiment_analyzer_scores(comment)
					total_comments += Counter(self.countwords(comment.lower()))
					#average_comment_score = self._average_scores(average_comment_score, comment_score)
				except:
					continue
		
		request_string = 'https://www.reddit.com/r/{}/top/.json?limit={}'.format(self._ticker_id, self._limit)
		response = requests.get(request_string, headers = {'User-agent': 'floffbot'})
		data = response.json()

		
		for post in data['data']['children']:
			selftext = post['data']['selftext']
			selftext_count = Counter(self.countwords(selftext.lower()))
			title = post['data']['title']
			title_count = Counter(self.countwords(title.lower()))

			total += selftext_count + title_count
			url = "https://www.reddit.com" + post['data']['permalink'] + ".json"

			url_response = requests.get(url, headers = {'User-agent': 'floffbot'})
			url_data = url_response.json()
			
			for url_comment in url_data[1]['data']['children']:
				try:
					comment = url_comment['data']['body']
					#comment_score = self._sentiment_analyzer_scores(comment)
					total_comments += Counter(self.countwords(comment.lower()))
					#average_comment_score = self._average_scores(average_comment_score, comment_score)
				except:
					continue

		out = [str(dict(total)).replace(",","ÅÅ"), str(dict(total_comments)).replace(",","ÅÅ")]
		return out

	def _add_data_to_lists(self, i, date, data):
		p1 = data[i+1].replace("ÅÅ",",")
		json_acceptable_string = p1.replace("'", "\"")
		d = json.loads(json_acceptable_string)

		posts = (date, d)
		
		p2 = data[i+2].replace("ÅÅ",",")
		json_acceptable_string = p2.replace("'", "\"")
		d2 = json.loads(json_acceptable_string)

		comments = (date, d2)
		
		self._posts.append(posts)
		self._comments.append(comments)

	def _get_write_info(self, i):
		posts = self._posts[i]
		comments = self._comments[i]
		
		date = posts[0]
		posts_txt = str(posts[1]).replace(",","ÅÅ")
		comment_txt = str(comments[1]).replace(",","ÅÅ")

		return "{}:{}:{},{},{}".format(date.hour, date.minute, date.second, posts_txt, comment_txt)


	def _lines_per_update(self):
		return 3
	
	def prettyprint(self):
		print("{} - {}".format(self._container_type, self._ticker_id))
		for key, value in self._data_lists.items():
			print(key)
			
			year = -1
			month = -1
			day = -1
			for item in value:
				date = item[0]
				if date.year != year or date.month != month or date.day != day:
					year = date.year
					month = date.month
					day = date.day
					print("\t * {}-{}-{}".format(year, month, day))
				print("\t\t   {}:{}:{}".format(date.hour, date.minute, date.second))
				for line in item[1]:
					print("\t\t\t   {} - {}".format(line, item[1][line]))
			
	def countwords(self, my_string):
		"""refactor to functions at some point"""
		# thanks internet

		output = []

		# remove punctuation from string
		for char in my_string:
			if char not in string.punctuation:
				output.append(char)

		# convert string to list
		output = ("".join(output)).split()

		my_dict = {}
		# create dictionary from list and put word count as value
		for word in output:
			if word in self._watchlist:
				my_dict.update({word: output.count(word)})

		return my_dict

	def folder_location(self):
		return "subreddit_hype_predictor"


