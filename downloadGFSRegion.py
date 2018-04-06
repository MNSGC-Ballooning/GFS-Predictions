from netCDF4 import Dataset
import nio
import numpy as np
import time
import datetime
import GFSReader
import Calculations

class GFSReader:

	def __init__(self):
		#CONSTANTS
		self.DEGREES_TO_RADIANS = np.pi/180.0
		self.RADIANS_TO_DEGREES = 180.0/np.pi

		# Placeholders for a GFS dataset
		self.GFS = None
		self.GFSDateTime = None

	def accessGFS(self, GFSDate):
		'''
		Acquires the GFS dataset for the given date and time
		'''

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
		print url

		attempts = 0
		while attempts < 3:
			attempts += 1
			try:
				GFS = Dataset(url,diskless=True)
				attempts = 3
				self.GFS = GFS
				self.GFSDateTime = GFSDateTime
				return
			except:
				print 'Failure to access GFS server. (attempt: %s)' %attempts

	def accessHistoricGFS(self, year, month, day, hour):
		'''
		Acquires the GFS dataset for a previous date and time
		'''

		GFSYear = str(year)
		GFSMonth = str(month).zfill(2)
		GFSDay = str(day).zfill(2)
		GFSDate = GFSYear + GFSMonth + GFSDay
		baseURL = 'http://nomads.ncdc.noaa.gov/dods/NCEP_GFS/%s/%s/' %(GFSYear + GFSMonth, GFSDate)
		#GFS data isn't uploaded until roughly 4.5 hours after the hour of prediction
		gfsFileHeader = 'gfs_3_%s_' %(GFSDate)
		if hour > 17 and hour < 24:
			timeURL = gfsFileHeader + '1800_fff'
			GFSTime = 18
		elif hour > 11:
			timeURL = gfsFileHeader + '1200_fff'
			GFSTime = 12
		elif hour > 5:
			timeURL = gfsFileHeader + '0600_fff'
			GFSTime = 6
		elif hour >= 0:
			timeURL = gfsFileHeader + '0000_fff'
			GFSTime = 0
		else:
			print 'Incorrect hour entry'
		GFSDateTime = datetime.datetime(int(GFSYear),int(GFSMonth),int(GFSDay),GFSTime, 0, 0)
		url = baseURL + timeURL

		attempts = 0
		while attempts < 3:
			attempts += 1
			try:
				GFS = Dataset(url)
				attempts = 3
				return GFS, GFSDateTime
			except:
				print 'Failure to access GFS server. (attempt: %s)' %attempts


	def findGFSTimeIndex(self, predictionDateTime):
		'''
		Determines the time index in the GFS dataset for the time of the prediction
		'''

		diff = predictionDateTime - self.GFSDateTime

		#GFS data is incremented every 3 hours
		return int(np.round((diff.total_seconds()/3600)/3))
		

	def findGFSLatLonIndex(self, lat, lon):
		'''
		Determines the latitude and longitude index in the GFS dataset for a given lat and lon
		'''

		if lon < 0:
			lon = 360 + lon
		lats = self.GFS.variables['lat'][:]
		lons = self.GFS.variables['lon'][:]
		error_lat = 0
		error_lon = 0
		previous_error_lat = 9999
		previous_error_lon = 9999
		index_i=0
		index_j=0
		for j in range(len(lats)):
			error_lat = abs(lat - lats[j])
			if error_lat < previous_error_lat:
				index_j = j
				previous_error_lat = error_lat
		for i in range(len(lons)):
			error_lon = abs(lon - lons[i])
			if error_lon < previous_error_lon:
				index_i = i
				previous_error_lon = error_lon
		return index_i, index_j

	def getTerrainHeight(self, gfs, timeIndex, index_i, index_j):
		'''
		Determines the terrain height at a given latitude, longitude and time index in a GFS dataset
		'''

		return self.GFS.variables['hgtsfc'][timeIndex, index_j, index_i]

	def getGFSAlts(self, timeIndex, index_i, index_j):
		#Historic data has hgt current data has hgtprs
		ALT = self.GFS.variables["hgtprs"][timeIndex,:,index_j,index_i]
		return ALT

	##def findGFSAltIndex(gfs, timeIndex, index_i, index_j, alt):
	def findGFSAltIndex(self, ALT, alt):
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

	def getWindSpeedAndDirection(self, timeIndex, index_i, index_j, index_k, web=True, grib1=False):
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
		
	def openGFS(self, main_directory, file_name):
		try:
			gfs = nio.open_file(main_directory + file_name, 'r')
			return gfs
		except:
			print 'Something went wrong'

	def findNetCDFLatLonIndex(self, gfs, lat, lon):
		if lon < 0:
			lon = 360 + lon
		lats = gfs.variables['lat_0'][:]
		lons = gfs.variables['lon_0'][:]
		error_lat = 0
		error_lon = 0
		previous_error_lat = 9999
		previous_error_lon = 9999
		index_i=0
		index_j=0
		for j in range(len(lats)):
			error_lat = abs(lat - lats[j])
			if error_lat < previous_error_lat:
				index_j = j
				previous_error_lat = error_lat
		for i in range(len(lons)):
			error_lon = abs(lon - lons[i])
			if error_lon < previous_error_lon:
				index_i = i
				previous_error_lon = error_lon
		return index_i, index_j

	def findNetCDFAltIndex(self, gfs, index_i, index_j, alt):
		PH = gfs.variables["lv_ISBL0"][:] * .01 #hPa
		ALT = [(1-(PH[i]/1013.25)**0.190284)*145366.45*.3048 for i in range(len(PH)-1)] #m
		error = 0
		previous_error = 9999
		index_k = 0
		for k in range(len(ALT)):
			error = abs(alt - ALT[k])
			if  error < previous_error:
				index_k = k
				previous_error = error
		return index_k

	def findGribLatLonIndex(self, gfs, lat, lon):
		lats = gfs.variables['lat_3'][:]
		lons = gfs.variables['lon_3'][:]
		error_lat = 0
		error_lon = 0
		previous_error_lat = 9999
		previous_error_lon = 9999
		index_i=0
		index_j=0
		for j in range(len(lats)):
			error_lat = abs(lat - lats[j])
			if error_lat < previous_error_lat:
				index_j = j
				previous_error_lat = error_lat
		for i in range(len(lons)):
			error_lon = abs(lon - lons[i])
			if error_lon < previous_error_lon:
				index_i = i
				previous_error_lon = error_lon
		return index_i, index_j

	def findGribAltIndex(self, gfs, index_i, index_j, alt):
		PH = gfs.variables["lv_ISBL3"][:] #hPa
		ALT = [(1-(PH[i]/1013.25)**0.190284)*145366.45*.3048 for i in range(len(PH)-1)] #m
		error = 0
		previous_error = 9999
		index_k = 0
		for k in range(len(ALT)):
			error = abs(alt - ALT[k])
			if  error < previous_error:
				index_k = k
				previous_error = error
		return index_k



if __name__ == '__main__':

	## Create the GFSReader object
	gfsReader = GFSReader()
	gfsReader.accessGFS(datetime.datetime.now())

	## Inputs
	startLat = 45
	startLon = -93
	latRange = 5
	lonRange = 5
	startTime = datetime.datetime.now()
	endTime = startTime + datetime.timedelta(1)

	# Get the Latitude Ranges
	minLat = startLat - latRange
	maxLat = startLat + latRange

	# Get the Longitude Ranges
	minLon = startLon - lonRange
	maxLon = startLon + lonRange

	# Get Latitude and Longitude indeces
	lat_index_min, lon_index_min = gfsReader.findGFSLatLonIndex(minLat, minLon)
	lat_index_max, lon_index_max = gfsReader.findGFSLatLonIndex(maxLat, maxLon)
	time_index_min = gfsReader.findGFSTimeIndex(startTime)
	time_index_max = gfsReader.findGFSTimeIndex(endTime)

	print time_index_min, time_index_max
	print lat_index_min, lat_index_max
	print lon_index_min, lon_index_max

	## Populate a dataset with the wind speed and direction data
	dataset = []
	t = time_index_min
	while t <= time_index_max:
		dataset.append([])
		i = lat_index_min
		while i <= lat_index_max:
			dataset[t-time_index_min].append([])
			j = lon_index_min
			while j <= lon_index_max:
				dataset[t-time_index_min][i-lat_index_min].append([])
				ALTS = gfsReader.getGFSAlts(t, i, j)
				print(len(ALTS))
				k = 0
				while k < len(ALTS):
					print(t,i,j,k)
					w_spd, w_dir = gfsReader.getWindSpeedAndDirection(t, i, j, k)
					dataset[t-time_index_min][i-lat_index_min][j-lon_index_min].append((w_spd, w_dir))
					k += 1
				j+=1
			i+=1
		t+=1

	print dataset[t-time_index_min][i-lat_index_min][j-lon_index_min][k]











