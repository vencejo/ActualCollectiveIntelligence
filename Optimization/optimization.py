import time
import random
import math


people = [('Seymour', 'BOS'),
		  ('Franny', 'DAL'),
		  ('Zooey', 'CAK'),
		  ('Walt', 'MIA'),
		  ('Buddy', 'ORD'),
		  ('Les', 'OMA')]

# LaGuardia airport in New York
destination = 'LGA'

# Loading the data of schedule.txt
flights = {}

for line in file('schedule.txt'):
	origin,dest,depart,arrive,price = line.strip().split(',')
	flights.setdefault((origin, dest),[])

	# Add deatils to the list of possible flights
	flights[(origin,dest)].append((depart,arrive,int(price)))


def getminutes(t):
	""" calculates how many minutes into the day a given time is. This makes it easy to calculate flight
	times and waiting times. """
	x = time.strptime(t, '%H:%M')
	return x[3] * 60 + x[4]

def printschedule(r):
	""" prints all the flights that people decide to take in a nice table 
	r is a list of numbers. In this case, each number can represent which
	flight a person chooses to take, where 0 is the first flight of the day, 1 is the second,
	and so on. Since each person needs an outbound flight and a return flight, the length
	of this list is twice the number of people.
	"""
	for d in range(len(r)/2):
		name = people[d][0]
		origin = people[d][1]
		out = flights[(origin,destination)][r[d]]
		ret = flights[(destination, origin)][r[d+1]]
		print '%10s%10s %5s-%5s $%3s %5s-%5s $%3s' % (name, origin,
												      out[0],out[1],out[2],
												      ret[0],ret[1],ret[2])

def schedulecost(sol):
	totalprice = 0
	latestarrival = 0
	earliestdep = 24*60

	for d in xrange(len(sol)/2):
		# Get the inbound and outbound flights
		origin = people[d][1]
		outbound = flights[(origin, destination)][sol[d]]
		returnf = flights[(destination, origin)][sol[d+1]]

		# Total price is the price of all otubound and return flights
		totalprice += outbound[2]
		totalprice += returnf[2]

		# Track the latest arrival and earliest departure
		if latestarrival < getminutes(outbound[1]):
			latestarrival = getminutes(outbound[1])
		if earliestdep > getminutes(returnf[0]):
			earliestdep = getminutes(returnf[0])

	# Every person must wait at the airport until the latest person arrives.
	# They also must arrive at the same time and wait for their return flights.
	totalwait = 0
	for d in range(len(sol)/2):
		origin = people[d][1]
		outbound = flights[(origin, destination)][sol[d]]
		returnf = flights[(destination, origin)][sol[d+1]]
		totalwait += latestarrival - getminutes(outbound[1])
		totalwait += getminutes(returnf[0]) - earliestdep

	# Does this solution require an extra day of car rental? That will be $50
	if latestarrival > earliestdep:
		totalprice += 50

	return totalprice + totalwait

def randomoptimize(domain, costf):
	best = 9999999999
	bestr = None
	for i in range(1000):
		# Create a random solution
		r = [random.randint(domain[j][0], domain[j][1]) for j in range(len(domain)) ]

		# Get the cost
		cost = costf(r)

		# Compare it to the best one so far
		if cost < best:
			best = cost
			bestr = r

	return bestr 

