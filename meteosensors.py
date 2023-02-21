import threading, time

class sensor_bme280():
	def __init__(self, config={}):
		# Initialise the bme280
		from adafruit_bme280 import basic as adafruit_bme280
		import board
		i2c = board.I2C()  # uses board.SCL and board.SDA
		self.active = False
		decAddress = int(config['address'], 16)
		try:
			self.bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address = decAddress)
		except ValueError:
			print("Sensor BME280 failed!", flush=True)
			self.active = False
		
		self.fan = False
		self.attachedFans = []
		self.temperature = -999
		self.humidity = -999
		self.pressure = -999
		self.name = config['name']
		print(config, flush=True)
		try: 
			self.monitorCadence = config['cadence']
		except KeyError:
			self.monitorCadence = 20
		self.exit = False
		self.logData = { } 

	def attachFan(self, fan):
		self.attachedFans.append(fan)
		self.fan = True
		
	def readTemp(self):
		try:
			self.temperature = round(self.bme280.temperature, 1)
		except:
			self.temperature = -999
		self.logData['temperature'] = self.temperature
		return self.temperature
			
	def readHumidity(self):
		try:
			self.humidity = round(self.bme280.humidity, 1)
		except:
			self.humidity = -999
		self.logData['humidity'] = self.humidity
		return self.humidity
			
			
	def readPressure(self):
		try:
			self.pressure = round(self.bme280.pressure, 1)
		except:
			self.pressure = -999
		self.logData['pressure'] = self.pressure
		return self.pressure
			
	def monitor(self):
		while not self.exit:
			self.readTemp()
			self.readHumidity()
			self.readPressure()
			print("%s monitor: %.1f\u00b0C %.1f%% %.1fhPa"%(self.name, self.temperature, self.humidity, self.pressure), flush=True)
			if self.fan: 
				for fan in self.attachedFans:
					fan.checkFan(self.temperature)
	
			time.sleep(self.monitorCadence)
		print("%s monitor stopped."%self.name)
	

		
	def startMonitor(self):
		self.monitorThread = threading.Thread(name='non-block', target=self.monitor)
		self.monitorThread.start()
			
	def stopMonitor(self):
		print("Stopping %s monitor. Will take up to %d seconds."%(self.name, self.monitorCadence), flush=True)
		self.exit = True
