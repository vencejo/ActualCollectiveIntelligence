from math import tanh
from sqlite3 import dbapi2 as sqlite

class searchnet:
	"""docstring for searchnet"""
	def __init__(self, dbname):
		self.con = sqlite.connect(dbname)

	def __del__(self):
		self.con.close()

	def maketables(self):
		self.con.execute('create table hiddennode(create_key)')
		self.con.execute('create table wordhidden(fromid,toid,strength)')
		self.con.execute('create table hiddenurl(fromid,toid,strength)')
		self.con.commit()

	def getstrength(self, fromid, toid, layer):
		"""Getstrength, determines the current strength of a connection. Because new
		connections are only created when necessary, this method has to return a default
		value if there are no connections. For links from words to the hidden layer, the
		default value will be –0.2 so that, by default, extra words will have a slightly negative
		effect on the activation level of a hidden node. For links from the hidden layer to
		URLs, the method will return a default value of 0.
		"""
		if layer == 0:
			table = 'wordhidden'
		else:
			table = 'hiddenurl'

		res = self.con.execute('select strength from %s where fromid=%d and toid=%d' % (table,fromid,toid)).fetchone()

		if res == None:
			if layer == 0: 
				return -0.2
			if layer == 1:
				return 0
		return res[0]

	def setstrength(self, fromid, toid, layer, strength):
		if layer == 0:
			table = 'wordhidden'
		else:
			table = 'hiddenurl'

		res = self.con.execute('select rowid from %s where fromid=%d and toid=%d' % (table,fromid,toid)).fetchone()

		if res == None:
			self.con.execute('insert into %s (fromid,toid,strength) values (%d,%d,%f)' % (table, fromid, toid, strength))
		else:
			rowid = res[0]
			self.con.execute('update %s set strength=%f where rowid=%d' % (table,strength,rowid))

	def generatehiddennode(self, wordids, urls):
		"""will be faster and simpler to create new hidden nodes as they are needed.
		This function will create a new node in the hidden layer every time it is passed a
		combination of words that it has never seen together before. The function then
		creates default-weighted links between the words and the hidden node, and between
		the query node and the URL results returned by this query. """

		if len(wordids) > 3:
			return None
		# Check if we already created a node for this set of words
		createkey = '_'.join(sorted([str(wi) for wi in wordids]))
		res = self.con.execute("select rowid from hiddennode where create_key='%s'" % createkey).fetchone()
		# If not, create it
		if res == None:
			cur = self.con.execute("insert into hiddennode (create_key) values ('%s')" % createkey)
			hiddenid = cur.lastrowid
			# Put in some default weights
			for wordid in wordids:
				self.setstrength(wordid, hiddenid,0,1.0/len(wordids))
			for urlid in urls:
				self.setstrength(hiddenid, urlid, 1, 0.1)
			self.con.commit()

	def getallhiddenids(self, wordids, urlids):
		""" connections in the database, and build, in memory, the portion of the network that
		is relevant to a specific query. The first step is to create a function that finds all the
		nodes from the hidden layer that are relevant to a specific query—in this case, they
		must be connected to one of the words in the query or to one of the URLs in the
		results. Since the other nodes will not be used either to determine an outcome or to
		train the network, it’s not necessary to include them: """

		l1 = {}
		for wordid in wordids:
			cur = self.con.execute('select toid from wordhidden where fromid=%d' % wordid)
			for row in cur: 
				l1[row[0]] = 1
		for urlid in urlids:
			cur = self.con.execute('select fromid from hiddenurl where toid=%d' % urlid)
			for row in cur:
				l1[row[0]] = 1

		return l1.keys()

	def setupnetwork(self, wordids, urlids):
		""" You will also need a method for constructing the relevant network with all the cur-
		rent weights from the database. This function sets a lot of instance variables for this
		class—the list of words, query nodes and URLs, the output level of every node, and
		the weights of every link between nodes. The weights are taken from the database
		using the functions that were defined earlier.
		"""
		# value lists
		self.wordids = wordids
		self.hiddenids = self.setallhiddenids(wordids, urlids)
		self.urlids = urlids

		# node outputs
		self.ai = [1.0]*len(self.wordids)
		self.ah = [1.0]*len(self.hiddenids)
		self.ao = [1.0]*len(self.urlids)

		# create weights matrix
		self.wi = [[self.getstrength(wordid,hiddenid,0) for hiddenid in self.hiddenids] for wordid in self.wordids]
		self.wo = [[self.getstrength(hiddenid,urlid,1) for urlid in self.urlids] for hiddenid in self.hiddenids]


	def feedforward(self):
		""" the feedforward algorithm. This takes a list of inputs,
		pushes them through the network, and returns the output of all the nodes in the out-
		put layer. In this case, since you’ve only constructed a network with words in the
		query, the output from all the input nodes will always be 1:
		"""
		# The only inputs are the query words
		for i in range(len(self.wordids)):
			self.ai[i] = 1.0

		# Hidden activations
		for j in range(len(self.hiddenids)):
			sum = 0.0
			for i in range(len(self.wordids)):
				sum =sum + self.ai[i] * self.wi[i][j]
			self.ah[j] = tanh(sum)

		# output activations
		for k in range(len(self.urlids)):
			sum = 0.0
			for j in range(len(self.hiddenids)):
				sum = sum + self.ah[j] * self.wo[j][k]
			self.ao[k] = tanh(sum)

		return self.ao[:]  # Return a copy of self.ao 

	def getresult(self, wordids, urlids):
		self.setupnetwork(wordids,urlids)
		return self.feedforward()