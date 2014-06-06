import urllib2
import re
from bs4 import BeautifulSoup
from urlparse import urljoin
from sqlite3 import dbapi2 as sqlite

# Create a list of words to ignore
ignorewords=set(['the','of','to','and','a','in','is','it'])

class crawler():
	"""docstring for crawler"""
	
	def __init__(self, dbname):
		self.con=sqlite.connect(dbname)
	
	def __del__(self):
		self.con.close()	

	def dbcommit(self):
		self.con.commit()

	# Auxiliary function for getting an entry id and adding it
	# if its not present 
	def getentryid(self, table, field, value, createnew=True):
		cur = self.con.execute(
			"select rowid from %s where %s='%s'" % (table, field, value))
		res=cur.fetchone()
		if  res == None :
			cur = self.con.execute(
				"insert into %s (%s) values ('%s')" % (table,field,value))
			return cur.lastrowid
		else:
			#print res
			return res[0]



	# Index an individual page
	def addtoindex(self, url,soup):
		if self.isindexed(url):return
		print 'Indexing %s' % url

		#Get the individial words
		text=self.gettextonly(soup)
		words=self.separatewords(text)

		# Get the url id
		urlid = self.getentryid('urllist','url', url)

		# Link each word to this url
		for i in range(len(words)):
			word = words[i]
			if word in ignorewords: continue
			wordid=self.getentryid('wordlist', 'word', word)
			self.con.execute("insert into wordlocation(urlid,wordid,location) values (%d,%d,%d)" % (urlid, wordid,i))

	# Extract the text from an HTML page (no tags)
	def gettextonly(self,soup):
		v = soup.string # http://www.crummy.com/software/BeautifulSoup/bs4/doc/#string
		if v == None:
			c=soup.contents
			resulttext=''
			for t in c:
				subtext=self.gettextonly(t)
				resulttext+=subtext+'\n'
			return resulttext
		else:
			return v.strip()

	# Separate the words by any non-whitespace character
	#  it will suffice to consider anything that isnt a letter or a number to be a separator

	def separatewords(self,text):
		splitter=re.compile('\\W*')
		return [s.lower() for s in splitter.split(text) if s != '']

	# Return true if this url is already indexed
	def isindexed(self, url):
		u=self.con.execute("select rowid from urllist where url='%s'" % url).fetchone( )
		if u!=None:
			# Check if it has actually been crawled
			v=self.con.execute('select * from wordlocation where urlid=%d' % u[0]).fetchone( )
			if v!=None: return True
		return False


	# Add a link between two pages and store which words are actually used in that link
	def addlinkref(self,urlFrom,urlto,linkText):

		 # Get the urls ids
		 urlFromid = self.getentryid('urllist','url', urlFrom)
		 urltoid = self.getentryid('urllist','url', urlto)
		 
		 #filling link table
		 cur = self.con.execute("insert into link(fromid, toid) values (%d,%d)" % (urlFromid, urltoid))
		 linkid = cur.lastrowid

		 #filling linkwords
		 wordid=self.getentryid('wordlist', 'word', linkText)
		 self.con.execute("insert into linkwords(wordid, linkid) values (%s,%s)" % (wordid, linkid))




	# Starting with a list of pages, do a breadth
	# first search to the given depth, indexing pages
	# as we global
	def crawl(self,pages,depth=2):
		for i in range(depth):
			newpages=set()
			for page in pages:
				try:
					c=urllib2.urlopen(page)
				except:
					print "Could not open %s" % page
					continue
				soup=BeautifulSoup(c.read())
				self.addtoindex(page,soup)

				links=soup('a')
				for link in links:
					if ('href' in dict(link.attrs)):
						url=urljoin(page,link['href'])
						if url.find("'") != -1:	continue
						url=url.split('#')[0] #remove location portion
						if url[0:4] == 'http' and not self.isindexed(url):
							newpages.add(url)
						linkText=self.gettextonly(link)
						self.addlinkref(page, url, linkText)

				self.dbcommit()

			pages = newpages

	def calculatepagerank(self, iterations=20):
		# clear out the current PageRank tables
		self.con.execute('drop table if exists pagerank')
		self.con.execute('create table pagerank(urlid primary key, score)')

		# initialize every url with a PageRank of 1
		self.con.execute('insert into pagerank select rowid, 1.0 from urllist')
		self.dbcommit()

		for i in range(iterations):
			print "Iteration %d" % (i)
			for (urlid,) in self.con.execute('select rowid from urllist'):
				pr=0.15

				# Loop through all the pages that link to this one
				for (linker,) in self.con.execute('select distinct fromid from link where toid=%d'%urlid):
					# Get the PageRank of the linker
					linkingpr = self.con.execute('select score from pagerank where urlid=%d' % linker).fetchone()[0]
					# Get the total number of links from the linker
					linkingcount = self.con.execute('select count(*) from link where fromid=%d' % linker).fetchone()[0]
					pr += 0.85*(linkingpr/linkingcount)

				self.con.execute('update pagerank set score=%f where urlid=%d' % (pr, urlid))
				self.dbcommit()






	# Create the database tables
	def createindextables(self):
		self.con.execute('create table urllist(url)')
		self.con.execute('create table wordlist(word)')
		self.con.execute('create table wordlocation(urlid,wordid,location)')
		self.con.execute('create table link(fromid integer,toid integer)')
		self.con.execute('create table linkwords(wordid,linkid)')
		self.con.execute('create index wordidx on wordlist(word)')
		self.con.execute('create index urlidx on urllist(url)')
		self.con.execute('create index wordurlidx on wordlocation(wordid)')
		self.con.execute('create index urltoidx on link(toid)')
		self.con.execute('create index urlfromidx on link(fromid)')
		self.dbcommit( )







class searcher(object):
	"""docstring for searcher"""
	def __init__(self, dbname):
		self.con = sqlite.connect(dbname)

	def __del__(self):
		self.con.close()

	def getmatchrows(self, q):
		"""  A query function that takes a query string, splits it into separate words, 
		and constructs a SQL query to find only those URLs containing all the different words. 

		This function returns two list: 
			The first one has the url and the locations of the words in this url
			The second one has the list of the words ids 
		"""
		# Strings to build the query
		fieldlist = 'w0.urlid'
		tablelist = ''
		clauselist = ''
		wordids = []

		# Split the words by spaces
		words = q.split(' ')
		tablenumber = 0

		for word in words:
			# Get the word id
			wordrow = self.con.execute(
				"select rowid from wordlist where word='%s'" % word).fetchone()
			if wordrow != None:
				wordid = wordrow[0]
				wordids.append(wordid)
				if tablenumber > 0:
					tablelist += ','
					clauselist += ' and '
					clauselist += 'w%d.urlid=w%d.urlid and ' % (tablenumber - 1, tablenumber)
				fieldlist += ',w%d.location' % tablenumber
				tablelist += 'wordlocation w%d' % tablenumber
				clauselist += 'w%d.wordid=%d' % (tablenumber, wordid)
				tablenumber += 1

		# Create the query from the separate parts
		fullquery = 'select %s from %s where %s' % (fieldlist, tablelist, clauselist)
		cur = self.con.execute(fullquery)
		rows = [ row for row in cur]

		return rows, wordids


	def getscoredlist(self, rows, wordsids):	
		""" This method recives the parameters returned by getmatchrows:
				rows -> a list who has the url and the locations of the words in this url
				wordids ->  has the list of the words ids  """
		
		totalscores = dict([(row[0], 0) for row in rows] ) # row[0] has the url 

		# This is where  you'll later put the scoring functions
		weights = [(0.5, self.pagerankscore(rows)),
					(0.2, self.locationscore(rows)), 
					(0.2, self.frequencyscore(rows)),
					(0.1, self.distancescore(rows))] 

		for (weight, scores) in weights:
			for url in totalscores:
				totalscores[url] += weight * scores[url]

		return totalscores 

	def geturlname(self, id):
		return self.con.execute(
			"select url from urllist where rowid=%d" % id).fetchone()[0]

	def query(self, q):
		rows, wordids = self.getmatchrows(q)
		scores = self.getscoredlist(rows, wordids)
		rankedscores = sorted([(score,url) for (url,score) in scores.items()], reverse = 1)
		for (score, urlid) in rankedscores[0:10]:
			print '%f\t%s' % (score, self.geturlname(urlid))

	def normalizescores(self, scores, smallIsBetter=False):
		""" The normalization function will take a dictionary of IDs and scores and return a new
		dictionary with the same IDs, but with scores between 0 and 1. Each score is scaled
		according to how close it is to the best result, which will always have a score of 1. All
		you have to do is pass the function a list of scores and indicate whether a lower or
		higher score is better
		"""
		vsmall=0.00001 # Avoid division by zero errors
		if smallIsBetter:
			minscore = min(scores.values())
			return dict([(u, float(minscore)/max(vsmall,l)) for (u,l) in scores.items()])
		else:
			if scores.values() == []:
				maxscore = 0
			else:
				maxscore = max(scores.values())

			if maxscore == 0: 
				maxscore = vsmall
			return dict([(u,float(c)/maxscore) for (u,c) in scores.items()])

	def frequencyscore(self,rows):
		""" This function creates a dictionary with an entry for every unique URL ID in rows,
		and counts how many times each item appears. It then normalizes the scores (bigger
		is better, in this case) and returns the result.
		"""
		 # Remember that rows is a list who each element has the url and the locations of the words in this url
		counts = dict([row[0], 0] for row in rows) # row[0] is the url
		for row in rows:
			counts[row[0]] += 1 
		return self.normalizescores(counts)

	def locationscore(self,rows):
		"""  Usually, if a page is relevant to the search term, it will
		appear closer to the top of the page, perhaps even in the title. To take advantage of
		this, the search engine can score results higher if the query term appears early in the
		document. 
		Fortunately for us, when the pages were indexed earlier, the locations of
		the words were recorded, and the title of the page is first in the list.
 		"""
		locations = dict([(row[0], 100000) for row in rows])
		for row in rows:
			loc = sum(row[1:])
			if loc < locations[row[0]]:
				locations[row[0]] = loc

		return self.normalizescores(locations, smallIsBetter=True)

	def distancescore(self,rows):
		# If there's only one word, everyone wins
		if len(rows[0]) <= 2:
			return dict([(row[0], 1.0) for row in rows])

		# Initialize the dictionary with large values
		mindistance = dict([row[0], 1000000] for row in rows)

		for row in rows:
			dist = sum([abs(row[i]-row[i-1]) for row in range(2, len(row))])
			if dist < mindistance[row[0]]:
				mindistance[row[0]] = dist

		return self.normalizescores(mindistance, smallIsBetter=True)

	def inboundlinkscore(self, rows):
		""" The scoring function below creates a dictionary of counts by querying the link table
		for every unique URL ID in rows, and then it returns the normalized scores:
		rows -> a list who has the url and the locations of the words in this url"""
		uniqueurls = set([row[0] for row in rows])
		inboundcount = dict([(u, self.con.execute('select count(*) from link where toid=%d'%u).fetchone()[0])
							for u in uniqueurls])

		return self.normalizescores(inboundcount)

	def pagerankscore(self, rows):
		"""rows -> a list who has the url and the locations of the words in this url"""
	
		pageranks = dict([(row[0], self.con.execute('select score from pagerank where urlid=%d'% row[0]).fetchone()[0])
							for row in rows])

		maxrank=max(pageranks.values())
		normalizedscores = dict([(u,float(l)/maxrank) for (u,l) in pageranks.items()])

		return  normalizedscores