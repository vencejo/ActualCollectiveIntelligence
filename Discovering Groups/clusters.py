from math import sqrt

def pearson(v1,v2):
	# simple sums
	sum1=sum(v1)
	sum2=sum(v2)

	# sums of the squares
	sum1Sq=sum([pow(v,2) for v in v1])
	sum2Sq=sum([pow(v,2) for v in v2])

	# Sum of the products
	pSum=sum([v1[i]*v2[i] for i in range(len(v1))])

	# Calculate r (Pearson score)
	num=pSum-(sum1*sum2/len(v1))
	den=sqrt((sum1Sq-pow(sum1,2)/len(v1))*(sum2Sq-pow(sum2,2)/len(v1)))
	if den == 0: return 0

	return 1.0-num/den 


def readfile(filename):
	lines=[line for line in file(filename)]

	# First line is the column titles
	colnames=lines[0].strip().split('\t')[1:]
	# Second the rows
	rownames=[]
	data=[]
	for line in lines[1:]:
		p=line.strip().split('\t')
		# First column in each row is the rownames
		rownames.append(p[0])
		# The data for this row is the remainder of the row
		data.append([float(x) for x in p[1:]])

	return rownames,colnames,data 

class bicluster	:
	""" Each cluster in a hierarchical clustering algorithm is either a point in the tree with
	two branches, or an endpoint associated with an actual row from the dataset (in this
	case, a blog). Each cluster also contains data about its location, which is either the
	row data for the endpoints or the merged data from its two branches for other node
	types. You can create a class called bicluster that has all of these properties, which
	you’ll use to represent the hierarchical tree """

	def __init__(self, vec,left=None,right=None,distance=0.0,id=None):
		self.left = left
		self.right = right
		self.vec = vec
		self.id=id
		self.distance=distance

def hcluster(rows,distance=pearson):
	""" The algorithm for hierarchical clustering begins by creating a group of clusters that
		are just the original items. The main loop of the function searches for the two best
		matches by trying every possible pair and calculating their correlation. The best pair
		of clusters is merged into a single cluster. The data for this new cluster is the average
		of the data for the two old clusters. This process is repeated until only one cluster
		remains. It can be very time consuming to do all these calculations, so it’s a good
		idea to store the correlation results for each pair, since they will have to be calcu-
		lated again and again until one of the items in the pair is merged into another cluster.
	"""
	distances={}
	currentclustid=-1

	# Clusters are initially just the rows
	clust=[bicluster(rows[i],id=i) for i in range(len(rows))]

	while len(clust)>1:
		lowestpair=(0,1)
		closest=distance(clust[0].vec,clust[1].vec)

		# Loop through every pair looking for the smallest distance
		for i in range(len(clust)):
			for j in range(i+1, len(clust)):
				# distances is the cache of distance calculations
				if (clust[i].id, clust[j].id) not in distances:
					distances[(clust[i].id, clust[j].id)] = distance(clust[i].vec, clust[j].vec)

				d=distances[(clust[i].id, clust[j].id)]

				if d<closest:
					closest=d
					lowestpair=(i,j)

		# Calculate the average of the tow clusters
		mergevec=[ (clust[lowestpair[0]].vec[i] + clust[lowestpair[1]].vec[i])/2.0 for i in range(len(clust[0].vec))]

		# Create the new cluster
		newcluster=bicluster(mergevec, left=clust[lowestpair[0]], 
										right=clust[lowestpair[1]],
										distance=closest,
										id=currentclustid)

		# Cluster ids that were'nt in the original set are negative
		currentclustid-=1
		del clust[lowestpair[1]]
		del clust[lowestpair[0]]
		clust.append(newcluster)

	return clust[0]
