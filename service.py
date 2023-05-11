#!/usr/bin/env python

# Standard Python libraries
import signal, argparse, time, sys, logging
import loggers
from systemd import journal

# Custom skyWATCH libraries
import camera, config, ephemeris

def signal_handler(sig, frame):
	print("Caught Ctrl-C")
	print("Shutting down services...")
	stopServices()
	sys.exit()

def stopServices():
	for sensor in meteoSensors:
		sensor.stopMonitor()
	camera.stopMonitor()

	
def information(message):
	global log, service
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

	if args.service: 
		service = True
		log = logging.getLogger('skywatch.service')
		log.addHandler(journal.JournaldLogHandler())
		log.setLevel(logging.INFO)
		logLine = "Starting the skyWATCH system daemon."
		log.info(logLine)
	if args.config is None:
		print("Please specify a config file.")
		sys.exit()

	config = config.config(args.config, debug = False)
	config.load()

	# Initiliase the sensors
	meteoSensors = []
	for sensor in config.sensors:
		if sensor['type']=="meteo":
			import meteosensors
 
			if sensor['sensor'] == 'bme280':
				sensorObject = meteosensors.sensor_bme280(config = sensor)
				meteoSensors.append(sensorObject)
				information("Added sensor '%s' of type '%s'"%(sensor['name'], sensor['sensor']))
		if sensor['type']=="CPU":
			cpuSensor = meteosensors.cpuSensor(config = sensor)
			meteoSensors.append(cpuSensor)

		time.sleep(1)
	

	# Create an ephemeris object
	if hasattr(config, "ephemeris"):
		print("Ephemeris: ", config.ephemeris)
		ephem = ephemeris.ephemeris(config.ephemeris)
		time.sleep(1)
	
	# Create a camera object
	if hasattr(config, "camera"):
		print(config.camera)
		camera = camera.camera(config.camera, config.installPath, args.config)
		camera.attachEphem(ephem)
		time.sleep(1)

	# Create the web uploader logger
	meteouploader = loggers.meteoUploader(config = config.meteoUpload)
	for sensor in meteoSensors:
		meteouploader.attachSensor(sensor)


	# Start the sensor monitors
	for sensor in meteoSensors:
		sensor.startMonitor()
		time.sleep(1)

	# Start the camera
	camera.startMonitor()

	# Start the meteo uploader
	meteouploader.startMonitor()
	

	counter = 0
	limit = 1E6
	while counter<limit:
		counter+=1
		information("in loop cycle %d"%counter)
		time.sleep(500)
	
	stopServices()	
