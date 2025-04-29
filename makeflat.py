#!/usr/bin/env python
import argparse
import json
import numpy
import os
import config, imagedata
import sys
import PIL.Image
from PIL import ImageStat
import astropy
from astropy.io import fits

def plotHistoRGB(histogram):
	import matplotlib.pyplot
	matplotlib.pyplot.bar(numpy.arange(0,255), histogram[0], color='r', alpha=0.25)
	matplotlib.pyplot.bar(numpy.arange(0,255), histogram[1], color='g', alpha=0.25)
	matplotlib.pyplot.bar(numpy.arange(0,255), histogram[2], color='b', alpha=0.25)
	matplotlib.pyplot.draw()
	matplotlib.pyplot.show()

def plotHistoL(histogram):
	import matplotlib.pyplot
	matplotlib.pyplot.bar(numpy.arange(0,256), histogram, color='k', alpha=0.25)
	matplotlib.pyplot.draw()
	matplotlib.pyplot.show()

def getHistoGrey(image):
	histogram = image.histogram
	return histogram

def getHistoRGB(image):
	histogram = image.histogram()

	r_histo = histogram[0:255]
	g_histo = histogram[256:511]
	b_histo = histogram[512:767]

	return (r_histo, g_histo, b_histo)

def getHistoL(image):
	histogram = image.histogram()
	return histogram


def debugOut(message):
	if debug: print("DEBUG: %s"%message, flush=True)
   
def information(message):
	print(message, flush=True)
	return

	
if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Makes a flat image for the night time exposures.')
	parser.add_argument('-n', '--number', type=int, default=11, help='Number of images use for the flat.' )
	parser.add_argument('-l', '--list', type=str, default="latest", help='Filename to process (or look for the latest).' )
	parser.add_argument('-c', '--config', type=str, default='/home/skywatch/code/skywatch/local.cfg', help='Config file.' )
	parser.add_argument('--balance', type=str, help='Use existing balance frame (ie skip making the flat).' )
	parser.add_argument('--sample', type=str, help="Sample file to process.")
	parser.add_argument('--debug', action="store_true", default=False, help='Add debug information to the output.' )
	parser.add_argument('--test', action="store_true", default=False, help='Test mode. Don''t upload any data.' )
	parser.add_argument('--display', action="store_true", default=False, help='Show preview and graphs.' )
	
	args = parser.parse_args()
	debug = args.debug
	config = config.config(filename=args.config)
	config.load()
	#debugOut(config.getProperties())
	if args.balance == None:
		makeFlat = True
		print("We will make a flat....")
	else: makeFlat = False

	flatFiles = []
	if args.list == "latest" and makeFlat:
		# Generate the list of files in the specified folder
		cameraPath = config.camera['outputpath']
		debugOut("Looking for the most recent %d files in %s"%(args.number, cameraPath))
		import glob
		types = [ 'jpg', 'png' ]
		fileCollection = []
		for t in types:
			listing = glob.glob(cameraPath + "/*." + t)
			for f in listing:
				fdict = { "filename": os.path.join(cameraPath, f), "timestamp": os.path.getmtime(os.path.join(cameraPath, f))}
				fileCollection.append(fdict)

		fileCollection.sort(key=lambda item: item['timestamp'])
		imageFile = fileCollection[-1]
		debugOut("Most recent: %s"%imageFile)
	elif makeFlat:
		listFile = open(args.list, "rt")
		for line in listFile:
			filename = line.strip()
			if len(filename)<1: continue
			flatFiles.append(filename)
		listFile.close()
	else:
		balanceFilename = args.balance
		balance_data = numpy.load(balanceFilename)
		balance_r = balance_data[0]
		balance_g = balance_data[1]
		balance_b = balance_data[2]
		

	debugOut("flatfiles: %s\nNumber of flats: %d"%(str(flatFiles), len(flatFiles)))
	
	if makeFlat:
		image = PIL.Image.open(flatFiles[0])
		if args.display: 
			print("Rendering a preview to the X-session ... will take about 30s")
			image.show()

		r_flats, g_flats, b_flats = [], [], []

		numflats = len(flatFiles)
		if args.number != None: numflats = args.number
		for i in range(numflats):
			flatFilename =  flatFiles[i]
			print("Opening:", flatFilename)
			img = PIL.Image.open(flatFilename)
			size = img.size
			r_flats.append(numpy.array(list(img.getdata(band=0)), dtype="uint8"))
			g_flats.append(numpy.array(list(img.getdata(band=1)), dtype="uint8"))
			b_flats.append(numpy.array(list(img.getdata(band=2)), dtype="uint8"))

		axis = 0
		print("Computing median image for the r-band.")
		median = numpy.median(r_flats, axis = axis)
		balance =  median / numpy.mean(median) 
		hdu = fits.PrimaryHDU(data = numpy.reshape(balance, (size[1], size[0])))
		hdul = fits.HDUList([hdu])
		hdul.writeto("balance_r.fits", overwrite=True)
		print("Written the balance FITS file for the r-band.")
		numpy.save("balance_r.npy", balance)
		
		print("Computing median image for the g-band.")
		median = numpy.median(g_flats, axis = axis)
		balance =  median / numpy.mean(median) 
		hdu = fits.PrimaryHDU(data = numpy.reshape(balance, (size[1], size[0])))
		hdul = fits.HDUList([hdu])
		hdul.writeto("balance_g.fits", overwrite=True)
		print("Written the balance FITS file for the g-band.")
		numpy.save("balance_g.npy", balance)
		
		print("Computing median image for the b-band.")
		median = numpy.median(b_flats, axis = axis)
		balance =  median / numpy.mean(median) 
		hdu = fits.PrimaryHDU(data = numpy.reshape(balance, (size[1], size[0])))
		hdul = fits.HDUList([hdu])
		hdul.writeto("balance_b.fits", overwrite=True)
		print("Written the balance FITS file for the b-band.")
		numpy.save("balance_b.npy", balance)
		
		print("number of flats processed:", numflats)

		sys.exit()
