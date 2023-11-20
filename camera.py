#!/usr/bin/env python
import signal, sys, argparse, time, datetime, threading, os, json, subprocess
import config, ephemeris

class camera:
	def __init__(self, config, installPath, configFile):
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
		self.installPath = installPath
		self.configFile = configFile

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
		information("sunMoon" + json.dumps(sunMoon))
		if sunMoon['night']:
			information("This is a night exposure.")
		self.picam2.start()
		time.sleep(2)
		self.picam2.capture_file(filename)
		self.logData['metadata'] = self.picam2.capture_metadata()
		self.picam2.stop()
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
		
		print("writing metadata to: %s"%imageData._filename)
		imageData.save()
	
	def runPostProcessor(self, filename):
		information("starting image post processing...(new thread)")			
		processorCommand = [ os.path.join(self.installPath, "postprocess.py"), "-c" , self.configFile, "-f", filename ] 
		commandLine =""
		for s in processorCommand:
			commandLine+= s + " "
		information("calling: %s"%commandLine)
		subprocess.Popen(processorCommand)
		
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
		self.runPostProcessor(self.logData['mostrecent'])
		information("Time elapsed during camera operations %f seconds. Sleeping for %f seconds."%(elapsedTime, waitTime))
		if waitTime>0: 
			self.nextIteration = threading.Timer(waitTime, self.monitor)
			self.nextIteration.start()
		else: self.monitor()

	
		
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

	cameraInstance = camera(config.camera, config.installPath, args.config)
	ephem = ephemeris.ephemeris(config.ephemeris)
	cameraInstance.attachEphem(ephem)
	cameraInstance.stopMonitor()
	cameraInstance.monitor()
	time.sleep(10)
	cameraInstance.stopMonitor()