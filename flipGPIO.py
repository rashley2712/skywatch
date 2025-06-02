#!/usr/bin/env python
import board
import argparse
import time
import datetime
import threading
import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library
import logging
from systemd import journal

def fanOn(pinID):
	GPIO.output(pinID, GPIO.HIGH) # Turn on

def fanOff(pinID):
	GPIO.output(pinID, GPIO.LOW) # Turn on



if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Monitors the CPU temp and turns the fan on if above a certain temperature..')
	parser.add_argument('-c', '--cadence', type=float, default=5, help='Cadence in seconds.' )
	parser.add_argument('-p', '--pin', type=int, default=21, help='Pin number to flip.' )
	parser.add_argument('-n', '--nolog', action="store_true", default=False, help='Don\'t output info.' )
	args = parser.parse_args()
	cadence = args.cadence
	debug = False
	GPIO.setwarnings(True) # Ignore warning for now
	GPIO.setmode(GPIO.BCM) # Use BCM pin numbering
	
	pinID = args.pin
	GPIO.setup(pinID, GPIO.OUT, initial=GPIO.HIGH) #
	
	stop = False
	while not stop:
		if not args.nolog: print("Setting pin #%d to high"%pinID)
		GPIO.output(pinID, GPIO.HIGH) #
		time.sleep(cadence)	
		if not args.nolog: print("Setting pin #%d to low"%pinID)
		GPIO.output(pinID, GPIO.LOW) #
		
		time.sleep(cadence)
	
	
