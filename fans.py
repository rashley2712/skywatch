import threading, time, subprocess, os
import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library


class fan():
	def __init__(self, config={}):
		print("FAN starting: ", config)
		self.GPIO = config['GPIO']
		self.name = config['name']
		self.triggerTemperature = config['tempstart']
		self.hysterisis = config['tempstart'] - config['tempstop']
		GPIO.setmode(GPIO.BCM) # Use BCM pin numbering
		GPIO.setup(self.GPIO, GPIO.OUT, initial=GPIO.LOW)
		self.fanOn = False
		self.logData =  { "status" : "off" }
		
	def checkFan(self, temp):
		if temp>self.triggerTemperature: 
			if not self.fanOn:
				print("Input temperature is above %d... Turning on %s."%(self.triggerTemperature, self.name), flush=True)
				self.on()
		if temp<self.triggerTemperature-self.hysterisis:
			if self.fanOn:
				print("Input temperature is below %d... Turning off %s."%(self.triggerTemperature-self.hysterisis, self.name), flush=True)
				self.off()
		
	def on(self):
		GPIO.setup(self.GPIO, GPIO.OUT, initial=GPIO.HIGH) 
		self.fanOn = True
		self.logData = { "status" : "on" }
	
	def off(self):
		GPIO.setup(self.GPIO, GPIO.OUT, initial=GPIO.LOW)
		self.fanOn = False
		self.logData = { "status" : "off" }
	 
		
	def flip(self):
		if self.fanOn: self.off()
		else: self.on()
	


