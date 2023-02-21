#!/usr/bin/env python
import signal, sys, argparse, time
import config

def signal_handler(sig, frame):
	print("Caught Ctrl-C")
	print("Shutting down services...")
	for sensor in meteoSensors:
		sensor.stopMonitor()
	sys.exit()

	
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

	if args.service: service = True
	if args.config is None:
		print("Please specify a config file.")
		sys.exit()

	config = config.config(args.config, debug = False)
	config.load()

	meteoSensors = []
	for sensor in config.sensors:
		if sensor['type']=="meteo":
			import meteosensors
 
			if sensor['sensor'] == 'bme280':
				sensorObject = meteosensors.sensor_bme280(config = sensor)
				meteoSensors.append(sensorObject)
				information("Added sensor '%s' of type '%s'"%(sensor['name'], sensor['sensor']))
	
	# Start the sensor monitors
	for sensor in meteoSensors:
		sensor.startMonitor()

	counter = 0
	while True:
		counter+=1
		information("in loop cycle %d"%counter)
		time.sleep(500)
	
