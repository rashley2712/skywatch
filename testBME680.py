#!/usr/bin/env python3

import datetime
import time
import sys


import board
import adafruit_bme680
i2c = board.I2C()

# Initialise the bme680
address = "0x76"
i2c = board.I2C()  # uses board.SCL and board.SDA
decAddress = int(address, 16)
try:
    bme680 = adafruit_bme680.Adafruit_BME680_I2C(i2c, address=decAddress)
except ValueError as e:
	print("Sensor BME680 failed!", flush=True)
	print(e)
	sys.exit()	


while True:
	now = datetime.datetime.now()

	temperature = round(bme680.temperature, 1)
	pressure = round(bme680.pressure, 1)
	humidity = round(bme680.humidity, 1)
	print('%s - %.1f %sC\t %.1f hPa\t %.1f %%'%(now, temperature, '\u00b0', pressure, humidity), flush=True)
	time.sleep(2)
