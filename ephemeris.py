	
import ephem

class ephemeris:
	def __init__(self, config):
		print(config, flush=True)
	
	
	def getSunMoon(locationInfo): 
		
		night = False
		meteoLocation = ephem.Observer()
		meteoLocation.lon = str(locationInfo['longitude'])
		meteoLocation.lat = str(locationInfo['latitude'])
		meteoLocation.elevation = locationInfo['elevation']
		d = datetime.datetime.utcnow()
		localTime = ephem.localtime(ephem.Date(d))
		information("local time: " + str(localTime))
		information("universal time: " + str(d))
		meteoLocation.date = ephem.Date(d)
		sun = ephem.Sun(meteoLocation)
		moon = ephem.Moon(meteoLocation)
		# information("Sun azimuth: %s altitude: %s"%(sun.az, sun.alt))
		altitude = sun.alt*180/3.14125
		information("Sun elevation is: %.2f"%altitude)
		currentDate = ephem.Date(d)
		timeToNewMoon = ephem.next_new_moon(currentDate) - currentDate
		timeSinceLastNewMoon = currentDate - ephem.previous_new_moon(currentDate)
		period = timeToNewMoon + timeSinceLastNewMoon
		phase = timeSinceLastNewMoon / period
		information("Moon elevation is: %.2f and illumination is: %.2f"%(moon.alt*180/3.14125, moon.phase))
		if altitude<-5: 
			# information("will take night exposure...")
			night = True
			
		results = {
			"night" : night,
			"sunElevation" : altitude,
			"moonIllumination": moon.phase, 
			"moonElevation": (moon.alt*180/3.14125)
		}
		return results

