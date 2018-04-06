import numpy as np
import time
import datetime
import urllib2
import os
import scipy.io

def getGFSUrl(GFSDate):
	baseURL = 'http://nomads.ncep.noaa.gov:9090/dods/gfs_0p25/'
	gfshour = GFSDate.hour
	GFSDate = int(GFSDate.strftime("%Y%m%d"))

	#GFS data isn't uploaded until roughly 4.5 hours after the hour of prediction
	gfsTimeHeader = 'gfs_0p25_'
	if gfshour > 22:
		timeURL = gfsTimeHeader + '18z'
		GFSTime = 18
	elif gfshour > 16:
		timeURL = gfsTimeHeader + '12z'
		GFSTime = 12
	elif gfshour > 10:
		timeURL = gfsTimeHeader + '06z'
		GFSTime = 6
	elif gfshour > 4:
		timeURL = gfsTimeHeader + '00z'
		GFSTime = 0
	else:
		timeURL = gfsTimeHeader + '18z'
		GFSTime = 18
		GFSDate -= 1
	GFSDate = str(GFSDate)
	GFSDateTime = datetime.datetime(int(GFSDate[:4]),int(GFSDate[4:6]),int(GFSDate[6:]),GFSTime, 0, 0)
	dateURL = 'gfs' + GFSDate + '/'
	url = baseURL + dateURL + timeURL
	return url, GFSDateTime

def findTimeIndex(gfsdatetime,predictionDateTime):
	'''
	Determines the time index in the GFS dataset for the time of the prediction
	'''

	diff = predictionDateTime - gfsdatetime

	#GFS data is incremented every 3 hours
	return int(np.round((diff.total_seconds()/3600)/3))
	

def findLatLonIndex(latset, lonset, lat, lon):
	'''
	Determines the latitude and longitude index in the GFS dataset for a given lat and lon
	'''

	if lon < 0:
		lon = 360 + lon
	error_lat = 0
	error_lon = 0
	previous_error_lat = 9999
	previous_error_lon = 9999
	index_i=0
	index_j=0
	for i in range(len(latset)):
		error_lat = abs(lat - latset[i])
		if error_lat < previous_error_lat:
			index_i = i
			previous_error_lat = error_lat
	for j in range(len(lonset)):
		error_lon = abs(lon - lonset[j])
		if error_lon < previous_error_lon:
			index_j=j = j
			previous_error_lon = error_lon
	return index_i, index_j	

def getGFSAltset(baseurl, timeIndexMin, timeIndexMax, latIndexMin, latIndexMax, lonIndexMin, lonIndexMax):
	'''
	Creates a data structure containing the altitudes in the grid for each lat, lon, and time in the range
	'''

	timeindexstr = '[' + str(timeIndexMin)+':'+str(timeIndexMax)+']'
	latindexstr = '[' + str(latIndexMin)+':'+str(latIndexMax)+']'
	lonindexstr = '[' + str(lonIndexMin)+':'+str(lonIndexMax)+']'

	alturl = baseurl + '.ascii?hgtprs'+timeindexstr+'[1:30]'+latindexstr+lonindexstr
	print('Retrieving Data From: '+'\n'+alturl)
	response = urllib2.urlopen(alturl)
	altset = response.read()
	altset = altset.split('\n')

	# Get the parameter ID and dimensions of the set retreived
	paramID = altset[0].split(',')[0]
	altdim = altset[0].split(',')[1].strip()

	print('ParamID: ' + str(paramID))
	print('Dimension: ' + str(altdim))

	# Convert the dimensions to an array of integers (for access) and create an np stuct of that size
	altdim = altdim.replace('[','')
	altdim = altdim.split(']')
	altdim = altdim[0:-1]
	i = 0
	for each in altdim:
		altdim[i] = int(each)
		i+=1

	# Create the data structure of the appropriate size
	altStruct = np.zeros((altdim[0],altdim[1],altdim[2],altdim[3]))

	# Remove the ID and dimensions from the set
	altset = altset[2:]

	# Iterate through the set to create the data structure
	check = 0
	for each in altset:

		# The set ends when there are three consecutive blank lines
		if each == '':
			if check == 0:
				check = 1
				continue
			if check == 1:
				check = 2
				continue
			if check == 2:
				break

		# Reset the check if it is not the end
		check = 0

		# Split on commas
		each = each.split(',')

		# The first entry is the location in the set, extract it and convert to integers
		loc = each[0]
		loc = loc.replace('[','')
		loc = loc.split(']')
		loc = loc[0:-1]
		i = 0
		for every in loc:
			loc[i] = int(every)
			i+=1

		# Remove the location
		each = each[1:]

		# Put the data into the struct at the correct location
		i = 0
		while i < altdim[3]:
			altStruct[loc[0]][loc[1]][loc[2]][i] = float(each[i])
			i+=1

	return altStruct

def getWindSets(baseurl, timeIndexMin, timeIndexMax, latIndexMin, latIndexMax, lonIndexMin, lonIndexMax):
	'''
	Create data structures containing the U and V wind components in the grid for each lat, lon, time, and altitude in the range
	'''

	timeindexstr = '[' + str(timeIndexMin)+':'+str(timeIndexMax)+']'
	latindexstr = '[' + str(latIndexMin)+':'+str(latIndexMax)+']'
	lonindexstr = '[' + str(lonIndexMin)+':'+str(lonIndexMax)+']'

	uurl = baseurl + '.ascii?ugrdprs'+timeindexstr+'[1:30]'+latindexstr+lonindexstr
	print('Retrieving Data From: '+'\n'+uurl)
	response = urllib2.urlopen(uurl)
	uset = response.read()
	uset = uset.split('\n')

	# Get the parameter ID and dimensions of the set retreived
	paramID = uset[0].split(',')[0]
	udim = uset[0].split(',')[1].strip()

	print('ParamID: ' + str(paramID))
	print('Dimension: ' + str(udim))

	# Convert the dimensions to an array of integers (for access) and create an np stuct of that size
	udim = udim.replace('[','')
	udim = udim.split(']')
	udim = udim[0:-1]
	i = 0
	for each in udim:
		udim[i] = int(each)
		i+=1

	# Create the data structure of the appropriate size
	uStruct = np.zeros((udim[0],udim[1],udim[2],udim[3]))

	# Remove the ID and dimensions from the set
	uset = uset[2:]

	# Iterate through the set to create the data structure
	check = 0
	for each in uset:

		# The set ends when there are three consecutive blank lines
		if each == '':
			if check == 0:
				check = 1
				continue
			if check == 1:
				check = 2
				continue
			if check == 2:
				break

		# Reset the check if it is not the end
		check = 0

		# Split on commas
		each = each.split(',')

		# The first entry is the location in the set, extract it and convert to integers
		loc = each[0]
		loc = loc.replace('[','')
		loc = loc.split(']')
		loc = loc[0:-1]
		i = 0
		for every in loc:
			loc[i] = int(every)
			i+=1

		# Remove the location
		each = each[1:]

		# Put the data into the struct at the correct location
		i = 0
		while i < udim[3]:
			uStruct[loc[0]][loc[1]][loc[2]][i] = float(each[i])
			i+=1

	vurl = baseurl + '.ascii?vgrdprs'+timeindexstr+'[1:30]'+latindexstr+lonindexstr
	print('Retrieving Data From: '+'\n'+vurl)
	response = urllib2.urlopen(vurl)
	vset = response.read()
	vset = vset.split('\n')

	# Get the parameter ID and dimensions of the set retreived
	paramID = vset[0].split(',')[0]
	vdim = vset[0].split(',')[1].strip()

	print('ParamID: ' + str(paramID))
	print('Dimension: ' + str(vdim))

	# Convert the dimensions to an array of integers (for access) and create an np stuct of that size
	vdim = vdim.replace('[','')
	vdim = vdim.split(']')
	vdim = vdim[0:-1]
	i = 0
	for each in vdim:
		vdim[i] = int(each)
		i+=1

	vStruct = np.zeros((vdim[0],vdim[1],vdim[2],vdim[3]))

	# Remove the ID and dimensions from the set
	vset = vset[2:]

	# Iterate through the set to create the data structure
	check = 0
	for each in vset:

		# The set ends when there are three consecutive blank lines
		if each == '':
			if check == 0:
				check = 1
				continue
			if check == 1:
				check = 2
				continue
			if check == 2:
				break

		# Reset the check if it is not the end
		check = 0

		# Split on commas
		each = each.split(',')

		# The first entry is the location in the set, extract it and convert to integers
		loc = each[0]
		loc = loc.replace('[','')
		loc = loc.split(']')
		loc = loc[0:-1]
		i = 0
		for every in loc:
			loc[i] = int(every)
			i+=1

		# Remove the location
		each = each[1:]

		# Put the data into the struct at the correct location
		i = 0
		while i < vdim[3]:
			vStruct[loc[0]][loc[1]][loc[2]][i] = float(each[i])
			i+=1

	return uStruct,vStruct

##def findGFSAltIndex(gfs, timeIndex, index_i, index_j, alt):
def findGFSAltIndex(ALT, alt):
##	ALT = gfs.variables["hgtprs"][timeIndex,:,index_j,index_i]
	error = 0
	previous_error = 9999
	index_k = 0
	for k in range(len(ALT)):
		error = abs(alt - ALT[k])
		if  error < previous_error:
			index_k = k
			previous_error = error
	return index_k

def getWindSpeedAndDirection(timeIndex, index_i, index_j, index_k, web=True, grib1=False):
	if web:
		#Historic data has u/vgrnd while current has u/vugrdprs
		U = self.GFS.variables["ugrdprs"][timeIndex, index_k, index_j, index_i]
		V = self.GFS.variables["vgrdprs"][timeIndex, index_k, index_j, index_i]
	else:
		if(grib1):
			U = -self.GFS.variables['U_GRD_3_ISBL'][index_k, index_j, index_i]
			V = -self.GFS.variables['V_GRD_3_ISBL'][index_k, index_j, index_i]
		else:
			U = self.GFS.variables['UGRD_P0_L100_GLL0'][index_k, index_j, index_i]
			V = self.GFS.variables['VGRD_P0_L100_GLL0'][index_k, index_j, index_i]
	if U > 100:
		U = 0
	if V > 100:
		V = 0
	windDir = self.RADIANS_TO_DEGREES * np.arctan2(U, V)
	windSpd = np.sqrt(U**2 + V**2)
	return windSpd, windDir


if __name__ == '__main__':

	## Inputs
	startLat = 45
	startLon = -93
	latRange = 5
	lonRange = 5
	startTime = datetime.datetime.now()
	endTime = startTime + datetime.timedelta(1)

	# Get the base GFS Url
	gfsdatetime = datetime.datetime.now()
	baseurl, gfsdatetime = getGFSUrl(gfsdatetime)
	print(baseurl)
	print(gfsdatetime)

	## Get the Latitude and Longitude Sets
	laturl = baseurl + '.ascii?lat'
	response = urllib2.urlopen(laturl)
	latset = response.read()
	latset = latset.split('\n')
	latset = latset[1].split(',')
	i = 0
	while i<len(latset):
		latset[i] = float(latset[i])
		i+=1
	print('Latitiude Set Length: ' + str(len(latset)))

	lonurl = baseurl + '.ascii?lon'
	response = urllib2.urlopen(lonurl)
	lonset = response.read()
	lonset = lonset.split('\n')
	lonset = lonset[1].split(',')
	i = 0
	while i<len(lonset):
		lonset[i] = float(lonset[i])
		i+=1
	print('Longitude Set Length: ' + str(len(lonset)))

	# Get the Latitude Ranges
	minLat = startLat - latRange
	maxLat = startLat + latRange

	# Get the Longitude Ranges
	minLon = startLon - lonRange
	maxLon = startLon + lonRange

	# Get Latitude, Longitude,and time index ranges
	latIndexMin, lonIndexMin = findLatLonIndex(latset, lonset, minLat, minLon)
	latIndexMax, lonIndexMax = findLatLonIndex(latset, lonset, maxLat, maxLon)
	timeIndexMin = findTimeIndex(gfsdatetime,startTime)
	timeIndexMax = findTimeIndex(gfsdatetime,endTime)
	print('Latitude Index Range: ' + str(latIndexMin) + ' - ' + str(latIndexMax))
	print('Longitude Index Range: ' + str(lonIndexMin) + ' - ' + str(lonIndexMax))
	print('Time Index Range: ' + str(timeIndexMin) + ' - ' + str(timeIndexMax))

	## Get the Altitude Set
	timestart = time.time()
	altset = getGFSAltset(baseurl, timeIndexMin, timeIndexMax, latIndexMin, latIndexMax, lonIndexMin, lonIndexMax)
	print('Time to Retrive Altitude Set: ' + str(time.time() - timestart))

	## Get the Wind Sets
	timestart = time.time()
	uset, vset = getWindSets(baseurl, timeIndexMin, timeIndexMax, latIndexMin, latIndexMax, lonIndexMin, lonIndexMax)
	print('Time to Retrive Wind Sets: ' + str(time.time() - timestart))

	# Save the Data
	datestr = datetime.datetime.now().strftime("%Y%m%d_%H%M")
	saveAdr = 'GFSdata_' + datestr
	if not os.path.exists(saveAdr):
		os.makedirs(saveAdr)

	# Create an offsets file to recognize what the ranges of the sets are
	f = open(saveAdr+'/offsets.txt','w')
	f.write(str(gfsdatetime) + '\n')
	f.write(str(latIndexMin) + '\n')
	f.write(str(lonIndexMin) + '\n')
	f.write(str(timeIndexMin) + '\n')
	f.close()

	# Save the lat and lon sets as .npy files
	latsetnp = np.zeros((len(latset)))
	i = 0
	for each in latset:
		latsetnp[i] = latset[i]
		i+=1
	lonsetnp = np.zeros((len(lonset)))
	i = 0
	for each in lonset:
		lonsetnp[i] = lonset[i]
		i+=1

	np.save(saveAdr + '/latset',latsetnp)
	np.save(saveAdr + '/lonset',lonsetnp)
	
	f = open(saveAdr+'/latset.txt','w')
	f.write(str(latset))
	f.close()
	f = open(saveAdr+'/lonset.txt','w')
	f.write(str(lonset))
	f.close()

	# Save the alt, u, and v sets as .npy files
	np.save(saveAdr + '/altset',altset)
	np.save(saveAdr + '/uset',uset)
	np.save(saveAdr + '/vset',vset)

	# Save the alt, u, and v sets as .mat files
	scipy.io.savemat(saveAdr + '/altset.mat', mdict = {'altset': altset})
	scipy.io.savemat(saveAdr + '/uset.mat', mdict = {'uset': uset})
	scipy.io.savemat(saveAdr + '/vset.mat', mdict = {'vset': vset})









