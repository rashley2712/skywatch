#!/usr/bin/env python
import signal, sys, argparse, time, datetime, threading, os, json, subprocess, socket
import config, ephemeris
import pprint
from picamera2 import Picamera2


def debugOut(message):
	if debug: print("DEBUG: %s"%message, flush=True)


def getMostRecentExposureTime():
	# Generate the list of files in the specified folder
	cameraPath = config.camera['outputpath']
	debugOut("Looking for the most recent file in %s"%cameraPath)
	import glob
	types = [ 'json' ]
	fileCollection = []
	for t in types:
		listing = glob.glob(cameraPath + "/*." + t)
		for f in listing:
			fdict = { "filename": os.path.join(cameraPath, f), "timestamp": os.path.getmtime(os.path.join(cameraPath, f))}
			fileCollection.append(fdict)

	fileCollection.sort(key=lambda item: item['timestamp'])
	imageFile = fileCollection[-1]
	debugOut("Most recent: %s"%imageFile)

class camera:
	def __init__(self, config, installPath, configFile):
		self.status = "init"
		self.width = int(config.camera['width'])
		self.height = int(config.camera['height'])
		self.width = 4608
		self.height = 2592
		self.logData = {}
		self.monitorCadence = config.camera['cadence']
		self.outputpath = config.camera['outputpath']
		self.name = config.camera['name']
		self.exit = False
		self.status = "idle"
		self.installPath = installPath
		self.configFile = configFile
		self.hostname = "unknown"
		self.config = config

	def setHostname(self, hostname):
		self.hostname = hostname

	def attachEphem(self, ephemeris):
		self.ephemeris = ephemeris

	def takeImage(self, sunMoon, filename="default"):
		self.picam2 = Picamera2()
		self.camera_config = self.picam2.create_still_configuration(main={"size": ( self.width, self.height)}, lores={"size": (640, 480)}, display="lores")
		self.picam2.configure(self.camera_config)
		
		now = datetime.datetime.now()
		timeString = now.strftime("%Y%m%d_%H%M%S")
		self.logData['timestamp'] = timeString
		if filename=="default":
			filename = os.path.join(self.outputpath, "%s_%s.jpg"%(self.hostname, timeString))
		self.status = "exposing"
		information("sunMoon: " + json.dumps(sunMoon))
		#sunMoon['night'] = True
		self.picam2.still_configuration.enable_raw()
		self.picam2.start("preview", show_preview=False)
		if sunMoon['night']:
			information("This is a night exposure.")
			self.mode = "night"
			self.config.load()
			texp = self.config.camera['suggestedTexp']
			print("suggested exposure time: %s seconds"%texp)
			self.picam2.still_configuration.controls.ExposureTime = int( texp * 1E6 )
			time.sleep(1)
			self.logData['exposure'] = texp
		else: 
			self.mode = "day"
			self.logData['exposure'] = -1
		
		self.picam2.switch_mode_and_capture_file("still", filename)
		
		self.logData['metadata'] = self.picam2.capture_metadata("still")
		self.picam2.close()
		information("Camera captured file: %s"%filename)
		self.logData['mostrecent'] = filename
		self.status = "idle"
		
	def writeMetadata(self):
		import imagedata
		imageData = imagedata.imagedata(debug=True)
		imageData.setFilename(os.path.splitext(self.logData['mostrecent'])[0] + ".json")
		imageData.setProperty("timestamp", self.logData['timestamp'])
		imageData.setProperty("filename", self.logData['mostrecent'].split('/')[-1])
		imageData.setProperty("ephemeris", self.logData['ephemeris'])
		imageData.setProperty("camera", self.logData['metadata'])
		imageData.setProperty("exposure", self.logData['exposure'])
		imageData.setProperty("mode", self.mode)
		
		print("writing metadata to: %s"%imageData._filename)
		imageData.save()
	
	def runPostProcessor(self, filename):
		information("starting image post processing...")			
		processorCommand = [ os.path.join(self.installPath, "postprocess.py"), "-c" , self.configFile, "-f", filename ] 
		commandLine =""
		for s in processorCommand:
			commandLine+= s + " "
		information("calling: %s"%commandLine)
		returnValue = subprocess.Popen(processorCommand)
		output = subprocess.Popen(processorCommand, stdout=subprocess.PIPE).communicate()[0]
		if "retake requested" in str(output):
			print("the camera has been asked for another exposure")
			time.sleep(1)
			self.nextIteration.cancel()
			self.nextIteration = threading.Timer(2, self.monitor)
			self.nextIteration.start()

	def monitor(self):
		startTime = datetime.datetime.now()
		sunMoon = self.ephemeris.getSunMoon()
		self.logData['ephemeris'] = sunMoon
		information(sunMoon)
		self.takeImage(sunMoon)
		self.writeMetadata()
		endTime = datetime.datetime.now()
		elapsedTime = float((endTime - startTime).total_seconds())
		waitTime = float(self.monitorCadence - elapsedTime)
		information("Time elapsed during camera operations %f seconds. Sleeping for %f seconds."%(elapsedTime, waitTime))
		if waitTime>0: 
			self.nextIteration = threading.Timer(waitTime, self.monitor)
			self.nextIteration.start()
		else: self.monitor()
		self.runPostProcessor(self.logData['mostrecent'])
		
	
		
	def startMonitor(self):
		self.monitorThread = threading.Thread(name='non-block', target=self.monitor)
		self.monitorThread.start()
			
	def stopMonitor(self):
		print("Stopping %s monitor."%(self.name), flush=True)
		try: 
			self.nextIteration.cancel()
		except AttributeError:
			print("exiting...")
		self.exit = True



	############### END of the camera class #######################
	

def signal_handler(sig, frame):
	print("Caught Ctrl-C")
	print("Shutting down services...")
	cameraInstance.stopMonitor()
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

	debug = args.debug

	if args.service: service = True
	if args.config is None:
		print("Please specify a config file.")
		sys.exit()

	config = config.config(args.config, debug = False)
	config.load()
	config.identity = socket.gethostname()
	print("Hostname: ", config.identity)

	print("Welcome to the camera driver....")

	cameraInstance = camera(config, config.installPath, args.config)
	ephem = ephemeris.ephemeris(config.ephemeris)
	cameraInstance.attachEphem(ephem)
	cameraInstance.setHostname(config.identity)
	cameraInstance.monitor()
	time.sleep(5)
	cameraInstance.stopMonitor()