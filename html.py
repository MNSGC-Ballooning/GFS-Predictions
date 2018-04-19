import urllib2

def getHTML(locations, apiKey):
	""" Creates an HTML and JavaScript file with the flight path plotted,
		as well as a draggable marker representing the ground station location
	"""

	### For every point in the list, format it into a string that can be inserted in to the JavaScript function
	allPoints = ''
	for each in locations:
		temp = '{lat: ' + str(each.lat) + ', lng: ' + str(each.lon) + '},'
		allPoints += temp
	allPoints = allPoints[:-1]


	### The HTML and JavaScript is a formatted string, this allows for a Google Maps widget ###
	html = '''
	<html>
	<head>
	<meta name="viewport" content="initial-scale=1.0, user-scalable=no" />
	<style type="text/css">
	    html { height: 100% }
	    body { height: 100%; margin: 0; padding: 0 }
	    #map { width: 100%; height: 100% }
	</style>

	<script async defer
	        src="https://maps.googleapis.com/maps/api/js?key=''' + str(apiKey) + '''&callback=initialize">
	</script>

	</head>
	<body> <div id="map"/>

	<script type="text/javascript">
	    var map;
	    function initialize() {
	        map = new google.maps.Map(document.getElementById("map"), {
	            center: {lat: ''' + str(locations[0].lat) + ''', lng: ''' + str(locations[0].lon) + '''},
	            zoom: 10,
	            mapTypeId: 'terrain'
	        });

            var locations = [''' + str(allPoints) + '''];
			var flightPath = new google.maps.Polyline({
                map: map,
                path: locations,
                geodesic: true,
                strokeColor: '#FF0000',
                strokeOpacity: 1.0,
                strokeWeight: 2
            });
	    }
	</script>

	</body>
	</html>
	'''

	return html


def getAltitude(lat, lon, apiKey):
	""" Uses the google api to determine the altitude (in feet) of the location by latitude and longitude """

	url = 'https://maps.googleapis.com/maps/api/elevation/json?locations='+str(lat)+','+str(lon)+'&key='+apiKey		# Site that returns the elevation of latitude and longitude
	response = urllib2.urlopen(url)
	pageTxt = str(response.read())		# Get the text of the page from the URL
	elevation = pageTxt[pageTxt.find('elevation')+len('elevation')+4:pageTxt.find(',')]		# Parse the text on the page
	alt = float(elevation)

	return alt*3.2808		# Convert to ft