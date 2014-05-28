import feedparser
import re

def getwords(html):
	# Remove all the HTML tags
	txt = re.compile(r'<[^>]+>').sub('', html)

	# Split words by all non-alpha characters
	words = re.compile(r'[^A-Z^a-z]+').split(txt)

	# Convert to lowercase
	return [word.lower() for word in words if word != '']



# Returns title and dictionary of word counts for an RSS feed
def getwordcounts(url):
	#  Parse the feed
	d = feedparser.parse(url)
	wc = {}

	# Loop over all the entries
	for e in d.entries:
		if 'sumary' in e:
			sumary = e.sumary
		else:
			sumary = e.description

		# Extract a list of words
		words = getwords(e.title+' '+sumary)
		for word in words:
			wc.setdefault(word,0)
			wc[word] += 1

	try:
		return d['feed']['title'], wc
	except KeyError:
		return 'Sin titulo', wc
		

apcount = {}
wordcounts = {}
# Loops over erery line in feedlist.txt and generates the word counts for each blog
for feedurl in file('feedlist.txt'):
	title, wc = getwordcounts(feedurl)
	wordcounts[title] = wc
	# The number of blogs each word appeared in (apcount)
	for word, count in wc.items():
		apcount.setdefault(word,0)
		if count > 1:
			apcount[word]+=1

""" The next step is to generate the list of words that will actually be used in the counts
for each blog. Since words like *the* will appear in almost all of them, and others
like *flim-flam* might only appear in one, you can reduce the total number of words
included by selecting only those words that are within maximum and minimum
percentages. In this case, you can start with 10 percent as the lower bound and 50
percent as the upper bound, but its worth experimenting with these numbers if you 
find too many common words or too many strange words appearing:
"""
with open('feedlist.txt', 'r') as f:
	lines = f.readlines()
	numBlogs = len(lines)

wordlist = []
for w,bc in apcount.items():
	frac=float(bc)/numBlogs 
	if frac > 0.1 and frac < 0.5:
		wordlist.append(w)

"""
The final step is to use the list of words and the list of blogs to create a text file con-
taining a big matrix of all the word counts for each of the blogs:
"""
out = file('blogdata.txt','w')
out.write('Blog')
for word in wordlist: out.write('\t%s' % word)
out.write('\n')
for blog, wc in wordcounts.items():
	out.write(blog)
	for word in wordlist:
		if word in wc: 
			out.write('\t%d' % wc[word])
		else:
			out.write('\t0')
	out.write('\n')