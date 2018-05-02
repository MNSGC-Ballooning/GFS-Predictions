class Location:
	''' A class to hold a lat, lon, alt, and time data along with the simulation resolution '''

	def __init__(self, time, timestep, alt):
		self.timestep = timestep
		self.time = time
		self.alt = alt
		self.lat = None
		self.lon = None

	def setLat(self, lat):
		self.lat = lat

	def setLon(self, lon):
		self.lon = lon

	def getTime(self):
		return self.time.strftime('%Y%m%d %H:%M:%S')

def createBurstAltPlan(timestep,startAlt,maxAlt,ascentRate,descentRate):
	'''
	Creates an altitude profile using constant ascent and descent rates from a starting
	altitude and time
	'''

	# # Create the datetime timedelta for the timestep
	# timedelta = datetime.timedelta(0,timestep)

	altPlan = []
	altPlan.append(Location(0, timestep, startAlt))

	curAlt = startAlt
	curTime = 0

	while curAlt < maxAlt:
		curAlt += ascentRate*timestep
		curTime += timestep
		altPlan.append(Location(curTime,timestep,curAlt))


	while curAlt > startAlt:
		curAlt -= descentRate*timestep
		curTime += timestep
		altPlan.append(Location(curTime,timestep,curAlt))

	return altPlan

def createFloatAltPlan(timestep,startAlt,floatAlt,floatTime,ascentRate,descentRate):
	'''
	Creates an altitude profile using constant ascent and descent rates from a starting
	altitude and time, with a single, explicit length float section
	'''

	# # Create the datetime timedelta for the timestep
	# timedelta = datetime.timedelta(0,timestep)

	altPlan = []
	altPlan.append(Location(0, timestep, startAlt))

	curAlt = startAlt
	curTime = 0

	# Ascent Section
	while curAlt <= floatAlt:
		curAlt += ascentRate*timestep
		curTime += timestep
		altPlan.append(Location(curTime,timestep,curAlt))

	# Float Section
	floatStartTime = curTime;
	while curTime < (floatTime+floatStartTime):
		curTime += timeStep
		altPlan.append(Location(curTime,timestep,curAlt))

	# Descent Section
	while curAlt > startAlt:
		curAlt -= descentRate*timestep
		curTime += timestep
		altPlan.append(Location(curTime,timestep,curAlt))

	return altPlan

def saveAltPlanToFile(altPlan,filename):
	''' 
	Saves an altitude profile to a file in the required format
	'''

	f = open(filename,'w')

	for each in altPlan:
		f.write(str(each.timestep) + ',' + str(each.time) + ',' + str(each.alt) + '\n')

	f.close()

if __name__ == '__main__':

	profileType = raw_input('Float or Burst Profile? (F/B) ')
	filename = raw_input('Alt Profile Name: ')

	if profileType == 'B':
		timeStep = float(raw_input('Timestep: '))
		startAlt = float(raw_input('Start Alt: '))
		maxAlt = float(raw_input('Max Alt: '))
		ascentRate = float(raw_input('Ascent Rate: '))
		descentRate = float(raw_input('Descent Rate: '))
		altPlan = createBurstAltPlan(timeStep,startAlt,maxAlt,ascentRate,descentRate)
	elif profileType == 'F':
		timeStep = float(raw_input('Timestep: '))
		startAlt = float(raw_input('Start Alt: '))
		floatAlt = float(raw_input('Float Alt: '))
		floatTime = float(raw_input('Float Time: '))
		ascentRate = float(raw_input('Ascent Rate: '))
		descentRate = float(raw_input('Descent Rate: '))
		altPlan = createFloatAltPlan(timeStep,startAlt,floatAlt,floatTime,ascentRate,descentRate)

	# timeStep = 30
	# startAlt = 300
	# maxAlt = 33000
	# ascentRate = 5
	# descentRate = 7

	# altPlan = createBurstAltPlan(timeStep,startAlt,maxAlt,ascentRate,descentRate)
	saveAltPlanToFile(altPlan,filename)