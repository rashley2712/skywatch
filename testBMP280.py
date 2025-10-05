#!/usr/bin/env python3

import datetime
import time
import board
import busio
import sys

address = "0x77"
if len(sys.argv)>1:
	print("Using %s as the address of the device."%sys.argv[1])
	address = sys.argv[1]

# Initialise the bmp280
import adafruit_bmp280
i2c = board.I2C()  # uses board.SCL and board.SDA
decAddress = int(address, 16)
try:
	bmp280 = adafruit_bmp280.Adafruit_BMP280_I2C(i2c, address = decAddress)
except ValueError as e:
	print("Sensor BME280 failed!", flush=True)
	print(e)
	sys.exit()	


while True:
	now = datetime.datetime.now()

	temperature = round(bmp280.temperature, 1)
	pressure = round(bmp280.pressure, 1)
	#humidity = round(bmp280.humidity, 1)
	print('%s - %.1f %sC\t %.1f hPa'%(now, temperature, '\u00b0', pressure), flush=True)
	time.sleep(2)
