#!/usr/bin/python

from collections import defaultdict
import SharedAlgorithm


class Product(object):
	"""
	has String member id, int members priority, revisedPriority
	"""

	def __init__(self, productId, priority):
		self.id = productId
		self.priority = priority
		self.revisedPriority = priority

	def __str__(self):
		#return (u"productId=" + self.productId + u", " + u"p0riority=" + self.priority)
		return (u'productId={0}, priority={1}, revisedPriority={2}'.format(self.id, self.priority,self.revisedPriority))


def produceRequirements(productDependencies):
	# Requirements are list of pairs (install_prior, install_posterior)
	# We treat only setup requirements
	setupRequirements = []

	for dependency in productDependencies:
		if dependency.productAction != u"setup":
			continue
		if dependency.requiredInstallationStatus != u"installed" and dependency.requiredAction != u"setup":
			continue
		if dependency.requirementType == u"before":
			setupRequirements.append((dependency.requiredProductId, dependency.productId))
		elif dependency.requirementType == u"after":
			setupRequirements.append((dependency.productId, dependency.requiredProductId))
			
	
	return setupRequirements
		
def modifySortingClassesForAlgorithm1(products, setupRequirements):
	# idea:
	# we reconstruct the priority chain
	# by pushing the products upwards into it when required by a dependency

	recursionNecessary = False

	fId2Prod = {}
	for prod in products:
		fId2Prod[prod.id] = prod
		print(u"prod  %s " % prod)

	fLevel2Prodlist = {}
	# state of priorityClasses
	for px in reversed(range(BOTTOM, 101)):
		fLevel2Prodlist[px] = []

	for prod in products:
		fLevel2Prodlist[prod.revisedPriority].append(prod)

	requsByPosterior = {}
	for requ in setupRequirements:
		if requ[1] not in requsByPosterior:
			requsByPosterior[requ[1]] = []

		requsByPosterior[requ[1]].append(requ)

	for px in range(BOTTOM, 101):
		#print(u"we are about to correct level %s ..." % px)
		if not fLevel2Prodlist[px]:
			#print(u"no elements in this level")
			pass
		else:
			for posti in fLevel2Prodlist[px]:
				print(u"posti %s " % posti)
				if posti.id in requsByPosterior:
					removeRequs = []
					for requ in requsByPosterior[posti.id]:
						if requ[0] not in fId2Prod:
							print(u"error: product '%s' should be arranged before product '%s' but is no available" % (requ[0], requ[1]))
							removeRequs.append(requ)
						else:
							if fId2Prod[requ[0]].revisedPriority < px:
								print(u"warning: product %s must be pushed upwards from level %s to level %s, the level of %s , to meet the requirement first %s, later %s" % (requ[0], fId2Prod[requ[0]].revisedPriority, px, posti.id, requ[0], requ[1]))
								fId2Prod[requ[0]].revisedPriority = px
								recursionNecessary = True

					for requ in removeRequs:
						requsByPosterior[posti.id].remove(requ)

	return recursionNecessary
	
"""
def modifySortingClassesForAlgorithm1(products, setupRequirements):
	# idea:
	# we reconstruct the priority chain
	# by pushing the products upwards into it when required by a dependency
	
	modified = False #recursion necessary?
	
	fLevel2Prodlist = {}
	
	#state of priorityClasses
	prioRange = list(reversed(range(BOTTOM, 101)))
	for px in prioRange:
		fLevel2Prodlist[px]=[]
	for prod in products:
		fLevel2Prodlist[prod.revisedPriority].append(prod)
	
	prioRangeFromBottom = list(range(BOTTOM, 101))	
	for px in prioRangeFromBottom:
		#print(u"we are about to correct level %s ................." % px)
		if not fLevel2Prodlist[px]:
			#print(u"no elements in this level")
			pass
		else:        
			 for posti in  fLevel2Prodlist[px]:
			 	 print(u"posti %s " %posti) 
			 	 if requsByPosterior.has_key(posti.id):
					 for requ in requsByPosterior[posti.id]:
						 if fId2Prod[requ[0]].revisedPriority < px:
							print(u"warning: %s must be pushed upwards from level %s to level %s, the level of %s , to meet the requirement first %s,  later %s " % (requ[0], fId2Prod[requ[0]].revisedPriority,px, posti.id, requ[0], requ[1]) )  
							fId2Prod[requ[0]].revisedPriority = px
							modified = True
			 	 	 	

	return modified	 	 	 
			 	 
"""

def generateProductSequence_algorithm1(availableProducts, productDependencies):
	
	setupRequirements = produceRequirements(productDependencies)
	generateProductSequence_algorithm1a(availableProducts, setupRequirements)

	
		

def generateProductSequence_algorithm1a(availableProducts, setupRequirements):
	sortedList = []
	# produce data structures
	
	# idea:
	# we build the priority chain
	# we push the products into it when required by a dependency
	# we sort on each level
	
	
	
	return sortedList
	

def generateProductSequence_algorithmX1(availableProducts, productDependencies):
	
	setupRequirements = produceRequirements(productDependencies)
	
	generateProductSequence_algorithm1a(availableProducts, setupRequirements)
	
	

print ("start-----------")
#BOTTOM =  50
BOTTOM = -100

availProducts = []
def prodSet1():
	availProducts.append(Product("p01", 100))
	availProducts.append(Product("p02", 100))
	availProducts.append(Product("p03", 90))
	availProducts.append(Product("p04", 90))
	availProducts.append(Product("p09", 90))
	availProducts.append(Product("p05", 92))
	availProducts.append(Product("p06", 80))
	availProducts.append(Product("p07", 82))
	availProducts.append(Product("p08", 82))
	availProducts.append(Product("p10", 92))
	availProducts.append(Product("p100", BOTTOM))
	
def  prodSet2():
	availProducts.append(Product("p01",50))
	availProducts.append(Product("p02",52))
	availProducts.append(Product("p03",52))
	availProducts.append(Product("p04",52))
	availProducts.append(Product("p05",50))
	availProducts.append(Product("p05",100))


def prodSet3():
	""""
	#productsCircularDependencies
	availProducts.append(Product("client-agent-sequ",95))
	availProducts.append(Product("firefox-sequ",0))
	availProducts.append(Product("flashplayer-sequ",0))
	availProducts.append(Product("javavm-sequ",0))
	availProducts.append(Product("jedit-sequ",0))
	availProducts.append(Product("sysessential-sequ",55))
	availProducts.append(Product("ultravnc-sequ",0))
	""" 
	
	#productsWithContradictingPrioritiesAndDependencies
	availProducts.append(Product("client-agent-sequ",95))
	availProducts.append(Product("flashplayer-sequ",0))
	availProducts.append(Product("javavm-sequ",0))
	availProducts.append(Product("jedit-sequ",0))
	availProducts.append(Product("sysessential-sequ",55))
	availProducts.append(Product("ultravnc-sequ",0))

prodSet3()

for prod in availProducts:
	print("prod %s %s " % (prod.id, prod.priority))
	
fId2Prod = {}

for prod in availProducts:
	fId2Prod[prod.id] = prod
	print(u"prod  %s " % prod)

setupRequirements = []

def requSet1():
	setupRequirements.append(("p01", "p02"))
	setupRequirements.append(("p03", "p02"))
	setupRequirements.append(("p09", "p04"))
	setupRequirements.append(("p04", "p02"))
	setupRequirements.append(("p05", "p04"))
	# in this state of affairs, p5 does not get before p4
	setupRequirements.append(("p06", "p02"))
	setupRequirements.append(("p07", "p08"))
	setupRequirements.append(("p08", "p07"))
	setupRequirements.append(("p10", "p05"))
	
def requSet2():
	setupRequirements.append(("p02", "p01"))
	setupRequirements.append(("p02", "p03"))
	setupRequirements.append(("p02", "p04"))
	setupRequirements.append(("p04", "p05"))
	setupRequirements.append(("p03", "p06"))
	
def requSet3():
	
	#requs for productsWithContradictingPrioritiesAndDependencies
	setupRequirements.append(("firefox-sequ", "flashplayer-sequ"))
	setupRequirements.append(("firefox-sequ", "javavm-sequ"))
	setupRequirements.append(("javavm-sequ", "jedit-sequ"))
	setupRequirements.append(("ultravnc-sequ", "sysessential-sequ"))
	setupRequirements.append(("javavm-sequ", "ultravnc-sequ"))
	
	
	"""
	#requs for productsCircularDependencies
	setupRequirements.append(("ultravnc-sequ", "firefox-sequ"))
	setupRequirements.append(("firefox-sequ", "flashplayer-sequ"))
	setupRequirements.append(("firefox-sequ", "javavm-sequ" ))
	setupRequirements.append(("javavm-sequ", "jedit-sequ"))
	setupRequirements.append(("ultravnc-sequ", "sysessential-sequ"))
	setupRequirements.append(("javavm-sequ", "ultravnc-sequ"))
	"""
	

	
requSet3()

for requ in setupRequirements:
	print("req  %s %s " % (requ[0], requ[1]))
	
#generateProductSequence_algorithm1a(availProducts, setupRequirements)

requsByPosterior = {}
for requ in setupRequirements:
	if not requsByPosterior.has_key( requ[1] ):
		requsByPosterior[requ[1]] = []
		
	requsByPosterior[requ[1]].append(requ)
	
requsByPrior = {}
for requ in setupRequirements:
	if not requsByPrior.has_key( requ[0] ):
		requsByPrior[requ[0]] = []
		
	requsByPrior[requ[0]].append(requ)



prioRangeFromBottom = list(range(BOTTOM, 101))
#for p in prioRangeFromBottom:
#	print(u" counting upwards %s " % p)

for prod in availProducts:
	print(u"product %s in class %s " %(prod.id,prod.revisedPriority))
	
ready = False
while not ready:
	ready = not modifySortingClassesForAlgorithm1(availProducts, setupRequirements)
	if ready:
		print(u"recursion finished")
	else:
		print(u"try recursion")



print(u"")
print(u"====")

print(u"original priorities ")
for prod in availProducts:
	print(u"product %s in class %s " %(prod.id, prod.priority))
print(u"")
print(u"revised priorities for algorithm1")
for prod in availProducts:
	print(u"product %s in class %s " %(prod.id, prod.revisedPriority))

print(u"")
print(u"")
for requ in setupRequirements:
	print("req  %s < %s " % (requ[0], requ[1]))



print(u"")
print(u"")
print(u"resulting")
print(u"====")
print(u"apply sort1")
sortedList1 = SharedAlgorithm.generateProductSequenceFromRequPairs_algorithm1(availProducts, setupRequirements)


i = 0
for prod in sortedList1:
	i = i+1
	print(u"product %i:  %s " %(i, prod))

print(u"")
print(u"apply sort2")
sortedList2 = SharedAlgorithm.generateProductSequenceFromRequPairs_algorithm2(availProducts, setupRequirements)


i = 0
for prod in sortedList2:
	i = i+1
	print(u"product %i: %s  " %(i, prod))

