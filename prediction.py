import numpy as np
import time
import datetime
import urllib2
import os
import scipy.io

class Location:
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

class Predictor:

	def __init__(self):

		# Iniitialize the datasets
		self.latset = None
		self.lonset = None
		self.altset = None
		self.uset = None
		self.vset = None
		self.altPlan = None

	def findTimeIndex(self,predictionDateTime):
		'''
		Determines the time index in the GFS dataset for the time of the prediction
		'''

		diff = predictionDateTime - self.gfsdatetime

		#GFS data is incremented every 3 hours
		return int(np.round((diff.total_seconds()/3600)/3))

	def findLatLonIndex(self, lat, lon):
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
		for i in range(len(self.latset)):
			error_lat = abs(lat - self.latset[i])
			if error_lat < previous_error_lat:
				index_i = i
				previous_error_lat = error_lat
		for j in range(len(self.lonset)):
			error_lon = abs(lon - self.lonset[j])
			if error_lon < previous_error_lon:
				index_j=j = j
				previous_error_lon = error_lon
		return index_i, index_j	

	def findAltIndex(self, timeIndex, latIndex, lonIndex, alt):
		error = 0
		previous_error = 9999
		index_k = 0
		for k in range(self.altset.shape[1]):
			error = abs(alt - self.altset[timeIndex][k][latIndex][lonIndex])
			if  error < previous_error:
				index_k = k
				previous_error = error
		return index_k

	def getWindSpeedAndDirection(self, timeIndex, latIndex, lonIndex, altIndex):

		U = self.uset[timeIndex][altIndex][latIndex][lonIndex]
		V = self.vset[timeIndex][altIndex][latIndex][lonIndex]
		if U > 100:
			U = 0
		if V > 100:
			V = 0
		windDir = 180.0/np.pi * np.arctan2(U, V)
		windSpd = np.sqrt(U**2 + V**2)
		return windSpd, windDir

	def createAltPlan(self,timestep,startTime,startAlt,maxAlt,ascentRate,descentRate):
		'''
		Creates an altitude profile using constant ascent and descent rates from a starting
		altitude and time
		'''

		# Create the datetime timedelta for the timestep
		timedelta = datetime.timedelta(0,timestep)

		altPlan = []
		altPlan.append(Location(startTime, timestep, startAlt))

		curAlt = startAlt
		curTime = startTime

		while curAlt < maxAlt:
			curAlt += ascentRate*timestep
			curTime += timedelta
			altPlan.append(Location(curTime,timestep,curAlt))


		while curAlt > startAlt:
			curAlt -= descentRate*timestep
			curTime += timedelta
			altPlan.append(Location(curTime,timestep,curAlt))

		self.altPlan = altPlan

	def getAltPlan(self):
		return self.altPlan

	def importDatasets(self):
		'''
		Gets the datasets
		'''
		# Get the data file
		f = open('offsets.txt')
		gfsdatetime = f.readline()
		gfsdatetime = gfsdatetime.replace('\n','')
		print(gfsdatetime)
		self.gfsdatetime = datetime.datetime.strptime(gfsdatetime,'%Y-%m-%d %H:%M:%S')
		self.latOffset = int(f.readline())
		self.lonOffset = int(f.readline())
		self.timeOffset = int(f.readline())
		f.close()

		# Import the datasets
		self.latset = np.load('latset.npy')
		self.lonset = np.load('lonset.npy')
		self.altset = np.load('altset.npy')
		self.uset = np.load('uset.npy')
		self.vset = np.load('vset.npy')

	def destination(self, distance, bearing, lat, lon):
	    #http://www.movable-type.co.uk/scripts/latlong.html
	    #distance must be entered as km since EARTH_RADIUS is in km
	    DEGREES_TO_RADIANS = np.pi/180.0
	    RADIANS_TO_DEGREES = 180.0/np.pi
	    EARTH_RADIUS = 6371

	    lat *= DEGREES_TO_RADIANS
	    lon *= DEGREES_TO_RADIANS
	    bearing *= DEGREES_TO_RADIANS

	    end_lat = np.arcsin(np.sin(lat) * np.cos(distance/EARTH_RADIUS) + np.cos(lat) * np.sin(distance/EARTH_RADIUS) * np.cos(bearing))
	    end_lon = lon + np.arctan2(np.sin(bearing) * np.sin(distance/EARTH_RADIUS) * np.cos(lat), np.cos(distance/EARTH_RADIUS) - np.sin(lat) * np.sin(end_lat))
	    end_lon = (end_lon + np.pi) % (2. * np.pi) - np.pi #normalise to -180...+180

	    end_lat *= RADIANS_TO_DEGREES
	    end_lon *= RADIANS_TO_DEGREES
	    return end_lat, end_lon

	def runPrediction(self,startLat,startLon):
		'''
		Predicts the latitude and longitude of the balloon for each altitude in the 
		alt plan
		'''

		# Get the initial conditions
		self.altPlan[0].lat = startLat
		self.altPlan[0].lon = startLon

		# Iterate through the altitude plan
		i = 0
		while i < len(self.altPlan)-1:

			# Get the lat, lon, and time indeces
			lat_index, lon_index = self.findLatLonIndex(self.altPlan[i].lat, self.altPlan[i].lon)
			lat_index = lat_index - self.latOffset
			lon_index = lon_index - self.lonOffset

			time_index = self.findTimeIndex(self.altPlan[i].time)
			time_index = time_index - self.timeOffset

			alt_index = self.findAltIndex(time_index, lat_index, lon_index, self.altPlan[i].alt)

			# Determine the wind speeds
			w_spd, w_dir = self.getWindSpeedAndDirection(time_index, lat_index, lon_index, alt_index)

			# Calculate the next latitude and longitude positions
			distance = w_spd*self.altPlan[i].timestep/1000 # in km
			self.altPlan[i+1].lat, self.altPlan[i+1].lon = self.destination(distance,w_dir,self.altPlan[i].lat,self.altPlan[i].lon)

			print(self.altPlan[i].getTime(),self.altPlan[i].lat,self.altPlan[i].lon,self.altPlan[i].alt)
			i+=1
		return

if __name__ == '__main__':
	predictor = Predictor()
	predictor.createAltPlan(30,datetime.datetime.now(),300,33000,5,7)
	predictor.importDatasets()
	predictor.runPrediction(45,-93)

