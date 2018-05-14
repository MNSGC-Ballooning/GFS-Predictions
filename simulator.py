from ui_mainwindow import Ui_MainWindow
import PyQt4
from PyQt4 import *
from PyQt4 import QtCore
from PyQt4.QtCore import QThread
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtWebKit import *
from PyQt4 import QtGui
import sys
import numpy as np
import datetime
import csv
import threading
import webbrowser, os
import time
import scipy.io

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar)

from html import *

googleMapsApiKey = ''			# https://developers.google.com/maps/documentation/javascript/get-api-key

class MyThread(QThread):
    def run(self):
        self.exec_()

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

class GFS(object):
	''' A class to hold the GFS sets needed for predictions '''

	def __init__(self):
		self.latset = None
		self.lonset = None
		self.altset = None
		self.uset = None
		self.vset = None
		self.gfsdatetime = None
		self.latOffset = None
		self.lonOffset = None
		self.timeOffset = None

class GFSRetriever(QtCore.QObject):
	""" A class that holds the signals and function for running the simulation """

	updateLatLonRange = pyqtSignal(list)
	updateTimeRange = pyqtSignal(list)
	startRetrieval = pyqtSignal()
	interruptSignal = pyqtSignal()

	def __init__(self, MainWindow):
		super(GFSRetriever, self).__init__()
		self.mainWindow = MainWindow
		self.latMin = None
		self.latMax = None
		self.lonMin = None
		self.lonMax = None
		self.dateTimeMin = None
		self.dateTimeMax = None

		# Slots
		self.mainWindow.datasets.connect(self.mainWindow.getDatasetsFinished)
		self.mainWindow.updateBrowser.connect(self.mainWindow.updateDownloadBrowser)

	def run(self):
		'''
		Retrieves the GFS datasets for the latitude, longitude and time ranges
		'''

		# Get the base GFS Url
		gfsdatetime = datetime.datetime.now()
		#gfsdatetime = self.dateTimeMin
		baseurl, gfsdatetime = self.getGFSUrl(gfsdatetime)
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
		self.mainWindow.updateBrowser.emit('Latitiude Set Length: ' + str(len(latset)))

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
		self.mainWindow.updateBrowser.emit('Longitude Set Length: ' + str(len(lonset)))

		# Get Latitude, Longitude,and time index ranges
		latIndexMin, lonIndexMin = self.findLatLonIndex(latset, lonset, self.latMin, self.lonMin)
		latIndexMax, lonIndexMax = self.findLatLonIndex(latset, lonset, self.latMax, self.lonMax)
		timeIndexMin = self.findTimeIndex(gfsdatetime,self.dateTimeMin)
		timeIndexMax = self.findTimeIndex(gfsdatetime,self.dateTimeMax)
		print('Latitude Index Range: ' + str(latIndexMin) + ' - ' + str(latIndexMax))
		self.mainWindow.updateBrowser.emit('Latitude Index Range: ' + str(latIndexMin) + ' - ' + str(latIndexMax))
		print('Longitude Index Range: ' + str(lonIndexMin) + ' - ' + str(lonIndexMax))
		self.mainWindow.updateBrowser.emit('Longitude Index Range: ' + str(lonIndexMin) + ' - ' + str(lonIndexMax))
		print('Time Index Range: ' + str(timeIndexMin) + ' - ' + str(timeIndexMax))
		self.mainWindow.updateBrowser.emit('Time Index Range: ' + str(timeIndexMin) + ' - ' + str(timeIndexMax))


		## Get the Altitude Set
		timestart = time.time()
		altset = self.getGFSAltset(baseurl, timeIndexMin, timeIndexMax, latIndexMin, latIndexMax, lonIndexMin, lonIndexMax)
		print('Time to Retrive Altitude Set: ' + str(time.time() - timestart))
		self.mainWindow.updateBrowser.emit('Time to Retrive Altitude Set: ' + str(time.time() - timestart) + ' seconds')


		## Get the Wind Sets
		timestart = time.time()
		uset, vset = self.getWindSets(baseurl, timeIndexMin, timeIndexMax, latIndexMin, latIndexMax, lonIndexMin, lonIndexMax)
		print('Time to Retrive Wind Sets: ' + str(time.time() - timestart))
		self.mainWindow.updateBrowser.emit('Time to Retrive Wind Sets: ' + str(time.time() - timestart) + ' seconds')
	
		# Create a GFS object to store the sets
		self.gfs = GFS()
		self.gfs.latset = latset
		self.gfs.lonset = lonset
		self.gfs.altset = altset
		self.gfs.uset = uset
		self.gfs.vset = vset
		self.gfs.gfsdatetime = gfsdatetime
		self.gfs.latOffset = latIndexMin
		self.gfs.lonOffset = lonIndexMin
		self.gfs.timeOffset = timeIndexMin

		# Send the result to the main window
		self.mainWindow.datasets.emit(self.gfs)

	def getGFSUrl(self, GFSDate):
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

	def findTimeIndex(self, gfsdatetime, predictionDateTime):
		'''
		Determines the time index in the GFS dataset for the time of the prediction
		'''

		diff = predictionDateTime - gfsdatetime

		#GFS data is incremented every 3 hours
		return int(np.round((diff.total_seconds()/3600)/3))

	def findLatLonIndex(self, latset, lonset, lat, lon):
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

	def getGFSAltset(self, baseurl, timeIndexMin, timeIndexMax, latIndexMin, latIndexMax, lonIndexMin, lonIndexMax):
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

	def getWindSets(self, baseurl, timeIndexMin, timeIndexMax, latIndexMin, latIndexMax, lonIndexMin, lonIndexMax):
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

	def setLatLonRange(self, latLon):

		self.latMin = latLon[0]
		self.latMax = latLon[1]
		self.lonMin = latLon[3]
		self.lonMax = latLon[2]

	def setTimeRange(self, times):
		self.dateTimeMin = times[0]
		self.dateTimeMax = times[1]

	def setInterrupt(self):
		self.interrupt = True

class Simulator(QtCore.QObject):
	""" A class that holds the signals and function for running the simulation """

	updateGFS = pyqtSignal(GFS)
	updateAltProfile = pyqtSignal(list)
	updateStartLat = pyqtSignal(float)
	updateStartLon = pyqtSignal(float)
	startSimulation = pyqtSignal()
	interruptSignal = pyqtSignal()

	def __init__(self, MainWindow):
		super(Simulator, self).__init__()
		self.mainWindow = MainWindow
		self.gfs = None
		self.altProfile = None
		self.startLat = None
		self.startLon = None
		self.startTime = None
		self.interrupt = False

		# Slots
		self.mainWindow.locations.connect(self.mainWindow.simulationFinished)
		self.mainWindow.progress.connect(self.mainWindow.updateSimulationProgress)

	def runSimulation(self):
		'''
		Predicts the latitude and longitude of the balloon for each altitude in the 
		alt plan
		'''

		# Get the initial conditions
		self.altProfile[0].lat = self.startLat
		self.altProfile[0].lon = self.startLon

		progress = 0
		simRes = []

		# Iterate through the altitude plan
		i = 0
		while i < len(self.altProfile)-1 and not self.interrupt:
			
			# Process events in each loop
			QtGui.QApplication.processEvents()
			
			# Get the lat, lon, and time indeces
			lat_index, lon_index = self.findLatLonIndex(self.altProfile[i].lat, self.altProfile[i].lon)
			lat_index = lat_index - self.gfs.latOffset
			lon_index = lon_index - self.gfs.lonOffset

			time_index = self.findTimeIndex(self.altProfile[i].time)
			time_index = time_index - self.gfs.timeOffset

			alt_index = self.findAltIndex(time_index, lat_index, lon_index, self.altProfile[i].alt)

			# Determine the wind speeds
			w_spd, w_dir = self.getWindSpeedAndDirection(time_index, lat_index, lon_index, alt_index)

			# Calculate the next latitude and longitude positions
			distance = w_spd*self.altProfile[i].timestep/1000 # in km
			self.altProfile[i+1].lat, self.altProfile[i+1].lon = self.destination(distance,w_dir,self.altProfile[i].lat,self.altProfile[i].lon)

			print(self.altProfile[i].getTime(),self.altProfile[i].lat,self.altProfile[i].lon,self.altProfile[i].alt)
			simRes.append(self.altProfile[i])
			i+=1
			self.mainWindow.progress.emit(int(progress), int(len(self.altProfile)-1))

		# Send the result to the main window
		self.mainWindow.locations.emit(simRes)

	def findTimeIndex(self,predictionDateTime):
		'''
		Determines the time index in the GFS dataset for the time of the prediction
		'''

		diff = predictionDateTime - self.gfs.gfsdatetime

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
		for i in range(len(self.gfs.latset)):
			error_lat = abs(lat - self.gfs.latset[i])
			if error_lat < previous_error_lat:
				index_i = i
				previous_error_lat = error_lat
		for j in range(len(self.gfs.lonset)):
			error_lon = abs(lon - self.gfs.lonset[j])
			if error_lon < previous_error_lon:
				index_j=j = j
				previous_error_lon = error_lon
		return index_i, index_j	

	def findAltIndex(self, timeIndex, latIndex, lonIndex, alt):
		error = 0
		previous_error = 9999
		index_k = 0
		for k in range(self.gfs.altset.shape[1]):
			error = abs(alt - self.gfs.altset[timeIndex][k][latIndex][lonIndex])
			if  error < previous_error:
				index_k = k
				previous_error = error
		return index_k

	def getWindSpeedAndDirection(self, timeIndex, latIndex, lonIndex, altIndex):

		U = self.gfs.uset[timeIndex][altIndex][latIndex][lonIndex]
		V = self.gfs.vset[timeIndex][altIndex][latIndex][lonIndex]
		if U > 100:
			U = 0
		if V > 100:
			V = 0
		windDir = 180.0/np.pi * np.arctan2(U, V)
		windSpd = np.sqrt(U**2 + V**2)
		return windSpd, windDir

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

	def setStartLat(self, lat):
		self.startLat = lat

	def setStartLon(self, lon):
		self.startLon = lon

	def setStartTime(self, datetime):
		self.startTime = datetime

	def setGFS(self, gfs):
		self.gfs = gfs

	def setAltProfile(self, altProfile):
		self.altProfile = altProfile

	def setInterrupt(self):
		self.interrupt = True


class WebView(PyQt4.QtWebKit.QWebPage):
	""" A class that allows messages from JavaScript being run in a QWebView to be retrieved """

	def javaScriptConsoleMessage(self, message, line, source):
		if source:
			print('line(%s) source(%s): %s' % (line, source, message))
		else:
			print(message)


class Proxy(PyQt4.QtCore.QObject):
	""" Helps get the info from the JavaScript to the main window """

	@PyQt4.QtCore.pyqtSlot(float, float)
	def showLocation(self, latitude, longitude):
		self.parent().edit.setText('%s, %s' % (latitude, longitude))


class MainWindow(QMainWindow,Ui_MainWindow):
	""" The main GUI window """

	# Simulator Signals
	progress = pyqtSignal(int, int)
	locations = pyqtSignal(list)

	# GFS Retriever Signals
	datasets = pyqtSignal(GFS)
	updateBrowser = pyqtSignal(str)

	def __init__(self, parent=None):
		super(MainWindow, self).__init__(parent)
		self.ui = Ui_MainWindow()			# Set up the GUI window from the file ui_mainwindow.py
		self.setupUi(self)

		self.gfsDataPath = ''
		self.altProfileFile = ''
		self.gfs = GFS()
		self.altProfile = []

		# Create and start a side thread to run the simulation in
		self.simulationThread = MyThread()
		self.simulationThread.start()

		# Create and start a side thread to collect datasets in
		self.datasetThread = MyThread()
		self.datasetThread.start()

		# Create the Simulator and connect the signals
		self.simulator = Simulator(self)
		self.simulator.moveToThread(self.simulationThread)
		self.simulator.updateStartLat.connect(self.simulator.setStartLat)
		self.simulator.updateStartLon.connect(self.simulator.setStartLon)
		self.simulator.updateGFS.connect(self.simulator.setGFS)
		self.simulator.updateAltProfile.connect(self.simulator.setAltProfile)
		self.simulator.startSimulation.connect(self.simulator.runSimulation)
		self.simulator.interruptSignal.connect(self.simulator.setInterrupt)

		# Create the GFSRetriever and connect the signals
		self.gfsRetriever = GFSRetriever(self)
		self.gfsRetriever.moveToThread(self.datasetThread)
		self.gfsRetriever.updateLatLonRange.connect(self.gfsRetriever.setLatLonRange)
		self.gfsRetriever.updateTimeRange.connect(self.gfsRetriever.setTimeRange)
		self.gfsRetriever.startRetrieval.connect(self.gfsRetriever.run)
		self.gfsRetriever.interruptSignal.connect(self.gfsRetriever.setInterrupt)

		# Button Function Link Setup
		self.getGFSDataFile.clicked.connect(self.selectGFS)
		self.getAltProfileButton.clicked.connect(self.selectAltProfile)
		self.runSimulationButton.clicked.connect(self.simulationButtonPress)
		self.getDatasetsButton.clicked.connect(self.getDatasetsButtonPress)
		self.simulationRunning = False
		self.gettingDatasets = False

		# Initialize the datetime entries to current
		self.launchDateTimeEntry.setDateTime(datetime.datetime.now())
		self.timeMinEdit.setDateTime(datetime.datetime.now())
		self.timeMaxEdit.setDateTime(datetime.datetime.now() + datetime.timedelta(1))

		# Alt Profile Graph Setup
		self.figure = Figure()
		self.canvas = FigureCanvas(self.figure)
		self.canvas.setParent(self.altProfileWidget)
		self.canvas.setFocusPolicy(Qt.StrongFocus)
		self.canvas.setFocus()
		self.mpl_toolbar = NavigationToolbar(self.canvas, self.altProfileWidget)
		vbox = QVBoxLayout()
		vbox.addWidget(self.canvas)  			# the matplotlib canvas
		vbox.addWidget(self.mpl_toolbar)
		self.altProfileWidget.setLayout(vbox)

		self.tabWidget.setCurrentIndex(0)		# Set the tab to the inputs tab when you open

	def handleLoadFinished(self, ok):
		""" Connects things from JavaScript to the proxy class """

		self.map.addToJavaScriptWindowObject('qt', self._proxy)		# Connect the load finished to the proxy

	def makePlot(self):
		""" Generates the plots based on the file selected and the ground station location """
		
		# Reset the arrays
		altProfileTime = np.array([])
		altProfileAlt = np.array([])

		# Fill the arrays with the data
		for each in self.altProfile:
			altProfileTime = np.append(altProfileTime,each.time)
			altProfileAlt = np.append(altProfileAlt,each.alt)

		try:
			# create an axis
			ax = self.figure.add_subplot(111)
			ax.clear()
			
			# plot data for predictions
			ax.plot(altProfileTime,altProfileAlt,'r-')
			ax.set_ylabel('Altitude (m)')
			ax.set_xlabel('Time (s)')

			# refresh canvas
			self.canvas.draw()

		except Exception, e:
			print(str(e))

	def updatePinLocation(self):
		""" Updates the instance variables, and determines the altitude """

		# Set the class variables for latitude and longitude, and set the display text
		self.pinLat = float(str(self.edit.text()).split(',')[0])
		self.trackerLat.setText(str(self.pinLat))
		self.pinLon = float(str(self.edit.text()).split(',')[1][1:])
		self.trackerLon.setText(str(self.pinLon))

		# Use Google Maps Api to get the altitude of the latitude and longitude
		elevation = getAltitude(self.pinLat,self.pinLon, googleMapsApiKey)
		self.pinAlt = elevation
		self.trackerAlt.setText(str(self.groundAlt))		# Set the display text
		self.dragged = True 				# The ground location has been set at least once

	def updateLaunchSiteDisplay(self):
		self.trackerLat.setText(str(self.pinLat))
		self.trackerLon.setText(str(self.pinLon))
		elevation = getAltitude(self.pinLat, self.pinLon, googleMapsApiKey)
		self.pinAlt = elevation
		self.trackerAlt.setText(str(self.groundAlt))

	def simulationFinished(self,simResults):
		self.runSimulationButton.setText('Run Simulation')
		self.simulationRunning = False
		html = getHTML(simResults,googleMapsApiKey)

		f = open('simResults.html','w')
		f.write(html)
		f.close()

		self.openHTMLinWebBrowser('simResults.html')

	def openHTMLinWebBrowser(self,path):

		webbrowser.open('file://' + os.path.realpath(path))

	def updateSimulationProgress(self, progress, total):
		percentage = float(progress)/float(total) * 100
		self.simulationProgress.setValue(percentage)

	def simulationButtonPress(self):
		if not self.simulationRunning:
			self.simulationRunning = True

			# Get the simulation starting conditions
			if not self.latEntryBox.text() == '':
				startLat = self.latEntryBox.text()
			else:
				startLat = self.latEntryBox.placeholderText()

			if not self.lonEntryBox.text() == '':
				startLon = self.lonEntryBox.text()
			else:
				startLon = self.lonEntryBox.placeholderText()

			startTime = self.launchDateTimeEntry.dateTime().toPyDateTime()

			# Update the time in each point in the altitude profile to reflect the starting time
			for each in self.altProfile:
				timedelta = datetime.timedelta(0,each.time)
				each.time = startTime + timedelta

			self.simulationProgress.setValue(0)
			self.simulator.updateStartLat.emit(float(startLat))
			self.simulator.updateStartLon.emit(float(startLon))
			self.simulator.updateGFS.emit(self.gfs)
			self.simulator.updateAltProfile.emit(self.altProfile)
			self.simulator.startSimulation.emit()

			self.runSimulationButton.setText('Stop')

		else:
			self.simulator.interruptSignal.emit()
			self.runSimulationButton.setText('Run Simulation')
			self.simulationRunning = False
			self.simulationProgress.setValue(0)
			return

	def getDatasetsButtonPress(self):
		if not self.gettingDatasets:
			self.gettingDatasets = True

			# Get the dataset ranges
			if not self.latMinEdit.text() == '':
				latMin = float(self.latMinEdit.text())
			else:
				latMin = float(self.latMinEdit.placeholderText())

			if not self.latMaxEdit.text() == '':
				latMax = float(self.latMaxEdit.text())
			else:
				latMax = float(self.latMaxEdit.placeholderText())

			if not self.lonMinEdit.text() == '':
				lonMin = float(self.lonMinEdit.text())
			else:
				lonMin = float(self.lonMinEdit.placeholderText())

			if not self.lonMaxEdit.text() == '':
				lonMax = float(self.lonMaxEdit.text())
			else:
				lonMax = float(self.lonMaxEdit.placeholderText())

			dateTimeMin = self.timeMinEdit.dateTime().toPyDateTime()
			dateTimeMax = self.timeMaxEdit.dateTime().toPyDateTime()


			self.gfsRetriever.updateLatLonRange.emit([latMin,latMax,lonMin,lonMax])
			self.gfsRetriever.updateTimeRange.emit([dateTimeMin,dateTimeMax])
			self.gfsRetriever.startRetrieval.emit()
			self.getDatasetsButton.setText('Stop')

		else:
			self.simulator.interruptSignal.emit()
			self.getDatasetsButton.setText('Get Datasets')
			self.gettingDatasets = False
			return


	def getDatasetsFinished(self, gfs):
		'''
		Saves the datasets from a GFS object to files in a labeled directory
		'''

		self.getDatasetsButton.setText('Get Datasets')
		self.gettingDatasets = False

		latset = gfs.latset
		lonset = gfs.lonset
		altset = gfs.altset
		uset = gfs.uset
		vset = gfs.vset
		gfsdatetime = gfs.gfsdatetime
		latOffset = gfs.latOffset
		lonOffset = gfs.lonOffset
		timeOffset = gfs.timeOffset

		# Save the Data
		datestr = gfsdatetime.strftime("%Y%m%d_%H%M")
		saveAdr = 'GFSdata_' + datestr
		if not os.path.exists(saveAdr):
			os.makedirs(saveAdr)

		# Create an offsets file to recognize what the ranges of the sets are
		f = open(saveAdr+'/offsets.txt','w')
		f.write(str(gfsdatetime) + '\n')
		f.write(str(latOffset) + '\n')
		f.write(str(lonOffset) + '\n')
		f.write(str(timeOffset) + '\n')
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

		# Save the latset and lonset as txt files
		f = open(saveAdr+'/latset.txt','w')
		f.write(str(latset))
		f.close()
		f = open(saveAdr+'/lonset.txt','w')
		f.write(str(lonset))
		f.close()

		# Save all sets as .npy files
		np.save(saveAdr + '/latset',latsetnp)
		print("Latset Saved")
		np.save(saveAdr + '/lonset',lonsetnp)
		print("Lonset Saved")
		np.save(saveAdr + '/altset',altset)
		print("Altset Saved")
		np.save(saveAdr + '/uset',uset)
		print("USet Saved")
		np.save(saveAdr + '/vset',vset)
		print("VSet Saved")
		self.updateDownloadBrowser("Datasets Saved to " + saveAdr)

		# Save all sets as .mat files
		scipy.io.savemat(saveAdr + '/latset.mat', mdict = {'latset': latset})		
		scipy.io.savemat(saveAdr + '/lonset.mat', mdict = {'lonset': lonset})		
		scipy.io.savemat(saveAdr + '/altset.mat', mdict = {'altset': altset})
		scipy.io.savemat(saveAdr + '/uset.mat', mdict = {'uset': uset})
		scipy.io.savemat(saveAdr + '/vset.mat', mdict = {'vset': vset})

	def importDatasets(self, path):
		'''
		Gets the datasets
		'''
		# Get the data file
		f = open(path + '/offsets.txt')
		gfsdatetime = f.readline()
		gfsdatetime = gfsdatetime.replace('\n','')
		print(gfsdatetime)
		gfsdatetime = datetime.datetime.strptime(gfsdatetime,'%Y-%m-%d %H:%M:%S')
		latOffset = int(f.readline())
		lonOffset = int(f.readline())
		timeOffset = int(f.readline())
		f.close()

		# Import the datasets
		latset = np.load(path + '/latset.npy')
		lonset = np.load(path + '/lonset.npy')
		altset = np.load(path + '/altset.npy')
		uset = np.load(path + '/uset.npy')
		vset = np.load(path + '/vset.npy')

		# Save the sets the the GFS object
		self.gfs.latset = latset
		self.gfs.lonset = lonset
		self.gfs.altset = altset
		self.gfs.uset = uset
		self.gfs.vset = vset
		self.gfs.gfsdatetime = gfsdatetime
		self.gfs.latOffset = latOffset
		self.gfs.lonOffset = lonOffset
		self.gfs.timeOffset = timeOffset

	def readAltProfileFromFile(self, altProfileFilePath):
		
		f = open(altProfileFilePath,'r')
		
		altProfile = []
		for each in f:
			each = each.split(',')
			altProfile.append(Location(float(each[1]),float(each[0]),float(each[2])))
		
		f.close()

		return altProfile
	
	def selectGFS(self):
		""" Lets you use a file browser to select the file you want to open """

		self.gfsDataPath = str(QFileDialog.getExistingDirectory())			# Opens the file browser, the selected file is saved in self.dataFile
		print(self.gfsDataPath)

		if not self.gfsDataPath == '':
			self.gfsDataLabel.setText(self.gfsDataPath)					# Display the file path
			self.importDatasets(self.gfsDataPath)

	def selectAltProfile(self):
		""" Lets you use a file browser to select the file you want to open """

		self.altProfileFile = str(QFileDialog.getOpenFileName())			# Opens the file browser, the selected file is saved in self.dataFile
		print(self.altProfileFile)

		if not self.altProfileFile == '':
			self.altProfile = self.readAltProfileFromFile(self.altProfileFile)
			self.altProfileLabel.setText(self.altProfileFile)					# Display the file path
			self.makePlot()

	def updateDownloadBrowser(self, text):
		self.downloadBrowser.append(text)

if __name__ == "__main__":

	app = QtGui.QApplication.instance()		# checks if QApplication already exists
	if not app:		# create QApplication if it doesnt exist 
		app = QtGui.QApplication(sys.argv)

	with open('api_key') as f:
		googleMapsApiKey = f.readline().strip()

	mGui = MainWindow()		# Create the main GUI window
	mGui.showMaximized()	# Show the GUI maximized (full screen)
	app.exec_()				# Run the GUI