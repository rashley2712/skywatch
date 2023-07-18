import threading, time, os, json, datetime, requests

debug = True

def debug(text):
	if debug: print(text, flush=True)


class webLogger():
	def __init__(self, hostname, config={}):
		self.hostname = hostname
		self.exit = False
		debug(config)
		try: 
			self.monitorCadence = config['cadence']
		except KeyError: 
			self.monitorCadence = 180
		
		try:
			if config['local']=="true": local=True
			else: local=False
		except KeyError: local=False
			
		try: 
			self.postURL = config['URL']
		except KeyError:
			self.postURL = "https://localhost:8080/postmeteo"
		
		if local: self.postURL = config['localURL']

		self.sensors = []

	def attachSensor(self, sensor):
		self.sensors.append(sensor)

	def monitor(self):
		while not self.exit:
			timeStamp = datetime.datetime.now()
			timeStampStr = timeStamp.strftime("%Y-%m-%d %H:%M:%S")
			logData = {"timestamp": timeStampStr, "hostname": self.hostname, "json" : {} }
			
			for s in self.sensors:
				logData['json'][s.name] = s.logData
			debug("uploading to %s: "%self.postURL + json.dumps(logData))
			if not self.sendData(self.postURL, logData):
				print("ERROR in uploading data!", flush=True)
			time.sleep(self.monitorCadence)
		print("%s monitor stopped."%self.name)
	
	def sendData(self, URL, jsonData):
		success = False
		print("Sending meteo info to:", URL)
		try: 
			response = requests.post(URL, json=jsonData)
			print("Server status code: ", response.status_code, flush=True)
			if (response.status_code!=200): 
				print("Data not uploaded.")
				return False
			responseJSON = json.loads(response.text)
			if responseJSON['status'] == 'OK': success = True
			response.close()
		except Exception as e: 
			success = False
			print(e, flush=True)
				
		return success
		
	def startMonitor(self):
		self.monitorThread = threading.Thread(name='non-block', target=self.monitor)
		self.monitorThread.start()
			
	def stopMonitor(self):
		print("Stopping %s monitor. Will take up to %d seconds."%(self.name, self.monitorCadence), flush=True)
		self.exit = True
		self.logFile.close()


class textLogger():
	def __init__(self, hostname, config={}):
		self.hostname = hostname
		self.exit = False
		debug(config)
		try: 
			self.monitorCadence = config['cadence']
		except KeyError: 
			self.monitorCadence = 180
		
		try: 
			self.logFilename = config['logFile']
		except KeyError:
			self.logFilename = "/var/log/%s-meteo.log"%self.hostname
		
		self.sensors = []

	def attachSensor(self, sensor):
		self.sensors.append(sensor)


	def monitor(self):
		while not self.exit:
			timeStamp = datetime.datetime.now()
			timeStampStr = timeStamp.strftime("%Y-%m-%d %H:%M:%S")
			logData = {"timestamp": timeStampStr, "hostname": self.hostname }
			
			for s in self.sensors:
				logData[s.name] = s.logData
			debug("logging to file: " + json.dumps(logData))

			if not os.path.exists(self.logFilename):
				self.logFile = open(self.logFilename, "wt")
			else:
				self.logFile = open(self.logFilename, "at")
			json.dump(logData, self.logFile)
			self.logFile.write("\n")
			self.logFile.close()
			time.sleep(self.monitorCadence)
		print("%s monitor stopped."%self.name)
	
		
	def startMonitor(self):
		self.monitorThread = threading.Thread(name='non-block', target=self.monitor)
		self.monitorThread.start()
			
	def stopMonitor(self):
		print("Stopping %s monitor. Will take up to %d seconds."%(self.name, self.monitorCadence), flush=True)
		self.exit = True
		self.logFile.close()
