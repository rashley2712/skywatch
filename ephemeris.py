	
import ephem, json, datetime

class ephemeris:
	def __init__(self, config):
		location = config['location']
		locationFile = open(config['locationFile'], "rt")
		locationDef = json.load(locationFile)
		#print("locations:", locationDef)
		for l in locationDef['locations']:
			if l['name'] == location: self.locationInfo = l

	
	def getSunMoon(self): 
		
		night = False
		meteoLocation = ephem.Observer()
		print("location info:", self.locationInfo)
		meteoLocation.lon = str(self.locationInfo['longitude'])
		meteoLocation.lat = str(self.locationInfo['latitude'])
		meteoLocation.elevation = self.locationInfo['elevation']
		d = datetime.datetime.utcnow()
		localTime = ephem.localtime(ephem.Date(d))
		print("local time: " + str(localTime))
		print("universal time: " + str(d))
		meteoLocation.date = ephem.Date(d)
		sun = ephem.Sun(meteoLocation)
		moon = ephem.Moon(meteoLocation)
		# information("Sun azimuth: %s altitude: %s"%(sun.az, sun.alt))
		altitude = round(sun.alt*180/3.14125, 2)
		print("Sun elevation is: %.2f"%altitude)
		currentDate = ephem.Date(d)
		timeToNewMoon = ephem.next_new_moon(currentDate) - currentDate
		timeSinceLastNewMoon = currentDate - ephem.previous_new_moon(currentDate)
		period = timeToNewMoon + timeSinceLastNewMoon
		phase = timeSinceLastNewMoon / period
		print("Moon elevation is: %.2f and illumination is: %.2f"%(moon.alt*180/3.14125, moon.phase))
		if altitude<-5: 
			# information("will take night exposure...")
			night = True
			
		results = {
			"night" : night,
			"sunElevation" : altitude,
			"moonIllumination": round(moon.phase, 2), 
			"moonElevation": round((moon.alt*180/3.14125), 2)
		}
		return results

