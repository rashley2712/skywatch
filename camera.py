#!/usr/bin/env python
import signal, sys, argparse, time, datetime, threading, os, json
import config
import ephem
	

class ephemeris:
	def __init__(self, config):
		information("ephemeris location is %s"%config['location'])
		self.location = self.getLocation(config['location'], config['locationFile'])
		self.getSunMoon()

	def getLocation(self, locationName, filename):
		print("opening location data: ", filename)
		locationFile = open(filename, 'rt')
		locations = json.loads(locationFile.read())['locations']
		locationFile.close()
		for l in locations:
			if l['name'] == locationName:
				locationData = l
				print(locationData)
				return locationData
		
		print("Error: location %s not found in the locations config %s."%(locationName, filename))
		return { "name" : "unknown" } 
		

	def getSunMoon(self): 
		night = False
		meteoLocation = ephem.Observer()
		meteoLocation.lon = str(self.location['longitude'])
		meteoLocation.lat = str(self.location['latitude'])
		meteoLocation.elevation = self.location['elevation']
		d = datetime.datetime.utcnow()
		localTime = ephem.localtime(ephem.Date(d))
		#information("local time: " + str(localTime))
		information("universal time: " + str(d))
		meteoLocation.date = ephem.Date(d)
		sun = ephem.Sun(meteoLocation)
		moon = ephem.Moon(meteoLocation)
		# information("Sun azimuth: %s altitude: %s"%(sun.az, sun.alt))
		altitude = sun.alt*180/3.14125
		#information("Sun elevation is: %.2f"%altitude)
		currentDate = ephem.Date(d)
		timeToNewMoon = ephem.next_new_moon(currentDate) - currentDate
		timeSinceLastNewMoon = currentDate - ephem.previous_new_moon(currentDate)
		period = timeToNewMoon + timeSinceLastNewMoon
		phase = timeSinceLastNewMoon / period
		#information("Moon elevation is: %.2f and illumination is: %.2f"%(moon.alt*180/3.14125, moon.phase))
		if altitude<-5: 
			night = True
			
		results = {
			"night" : night,
			"sunElevation" : round(altitude,2),
			"moonIllumination": round(moon.phase, 2), 
			"moonElevation": round((moon.alt*180/3.14125), 2)
		}
		return results



class camera:
	def __init__(self, config):
		from picamera2 import Picamera2
		self.status = "init"
		self.picam2 = Picamera2()
		self.width = int(config['width'])
		self.height = int(config['height'])
		self.camera_config = self.picam2.create_still_configuration(main={"size": ( self.width, self.height)}, lores={"size": (640, 480)}, display="lores")
		self.logData = {}
		self.monitorCadence = config['cadence']
		self.outputpath = config['outputpath']
		self.name = config['name']
		self.exit = False
		self.status = "idle"

	def attachEphem(self, ephemeris):
		self.ephemeris = ephemeris

	def takeImage(self, sunMoon, filename="default"):
		now = datetime.datetime.now()
		timeString = now.strftime("%Y%m%d_%H%M%S")
		self.logData['timestamp'] = timeString
		if filename=="default":
			filename = os.path.join(self.outputpath, timeString + ".jpg")
		self.picam2.configure(self.camera_config)
		self.status = "exposing"
		self.picam2.start()
		self.picam2.annotate_text="test"
		time.sleep(2)
		self.picam2.capture_file(filename)
		information("Camera captured file: %s"%filename)
		self.logData['metadata'] = self.picam2.capture_metadata()
		self.logData['mostrecent'] = filename
		self.picam2.stop()
		self.status = "idle"
	
	def writeMetadata(self):
		import imagedata
		imageData = imagedata.imagedata(debug=True)
		imageData.setFilename(os.path.splitext(self.logData['mostrecent'])[0] + ".json")
		imageData.setProperty("timestamp", self.logData['timestamp'])
		imageData.setProperty("filename", self.logData['mostrecent'].split('/')[-1])
		imageData.setProperty("camera", self.logData['metadata'])
		
		print("writing metadata to: %s"%imageData._filename)
		imageData.save()
	
		
	def monitor(self):
		while not self.exit:
			sunMoon = self.ephemeris.getSunMoon()
			information(sunMoon)
			self.takeImage(sunMoon)
			self.writeMetadata()
			time.sleep(self.monitorCadence)
		print("%s monitor stopped."%self.name)
	
		
	def startMonitor(self):
		self.monitorThread = threading.Thread(name='non-block', target=self.monitor)
		self.monitorThread.start()
			
	def stopMonitor(self):
		print("Stopping %s monitor. Will take up to %d seconds."%(self.name, self.monitorCadence), flush=True)
		self.exit = True



	############### END of the camera class #######################
	

def signal_handler(sig, frame):
	print("Caught Ctrl-C")
	print("Shutting down services...")
	sys.exit()

	
def information(message, service=False):
	global log
	if service: log.info(message)
	else: 
		print(message, flush=True)
	return

def error(message):
	global log, service
	if service: log.error(message)
	else: 
		print(message, flush=True)
	return


if __name__ == "__main__":
	signal.signal(signal.SIGINT, signal_handler)
	service = False
	parser = argparse.ArgumentParser(description='The operating service of the skyWATCH camera.')
	parser.add_argument('-c', '--config', type=str, help='Configuration file.' )
	parser.add_argument('--debug', action="store_true", default=False, help='Add debug information to the output.' )
	parser.add_argument('-s', '--service', action="store_true", default=False, help='Specify this option if running as a service.' )
	args = parser.parse_args()

	if args.service: service = True
	if args.config is None:
		print("Please specify a config file.")
		sys.exit()

	config = config.config(args.config, debug = False)
	config.load()

	print("Welcome to the camera driver....")

	cameraInstance = camera()
	cameraInstance.takeImage()