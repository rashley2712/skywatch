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
	retakeNow = False
	print(args.balance)
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
			image.show(title = "First of flat frames")

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
		median_r = numpy.median(r_flats, axis = axis)
		median_g = numpy.median(g_flats, axis = axis)
		median_b = numpy.median(b_flats, axis = axis)

		median = [ median_r, median_g, median_b ]
		numpy.save("median.npy", median)

		print("number of flats processed:", numflats)

		balance_r =  median_r / numpy.mean(median_r) 
		balance_g =  median_g / numpy.mean(median_g) 
		balance_b =  median_b / numpy.mean(median_b) 

		flat_r = numpy.rint(balance_r*255)
		flat_r = numpy.array(flat_r, dtype="uint8")
		flat_r = numpy.reshape(flat_r, (size[1], size[0]))

		flat_g = numpy.rint(balance_g*255)
		flat_g = numpy.array(flat_g, dtype="uint8")
		flat_g = numpy.reshape(flat_g, (size[1], size[0]))

		flat_b = numpy.rint(balance_b*255)
		flat_b = numpy.array(flat_b, dtype="uint8")
		flat_b = numpy.reshape(flat_b, (size[1], size[0]))
		
		imageflat_r = PIL.Image.fromarray(flat_r, mode=None)
		imageflat_g = PIL.Image.fromarray(flat_g, mode=None)
		imageflat_b = PIL.Image.fromarray(flat_b, mode=None)

		median_r = numpy.reshape(median_r, (size[1], size[0]))
		median_r = numpy.array(median_r, dtype="uint8")
		median_r = PIL.Image.fromarray(median_r, mode=None)
		median_g = numpy.reshape(median_g, (size[1], size[0]))
		median_g = numpy.array(median_g, dtype="uint8")
		median_g = PIL.Image.fromarray(median_g, mode=None)
		median_b = numpy.reshape(median_b, (size[1], size[0]))
		median_b = numpy.array(median_b, dtype="uint8")
		median_b = PIL.Image.fromarray(median_b, mode=None)
		flat = PIL.Image.merge("RGB", (median_r, median_g, median_b))
		if args.display: flat.show(title = "test")
		
		# Save the balance frame to disk	
		balance_data = [balance_r, balance_g, balance_b]
		numpy.save("balance.npy", balance_data)
		
		hdu_r = fits.PrimaryHDU(data = numpy.reshape(balance_r, (size[1], size[0])))
		hdu_g = fits.PrimaryHDU(data = numpy.reshape(balance_g, (size[1], size[0])))
		hdu_b = fits.PrimaryHDU(data = numpy.reshape(balance_b, (size[1], size[0])))
		hdul = fits.HDUList([hdu_r])
		hdul.writeto("balance_r.fits", overwrite=True)
		hdul = fits.HDUList([hdu_g])
		hdul.writeto("balance_g.fits", overwrite=True)
		hdul = fits.HDUList([hdu_b])
		hdul.writeto("balance_b.fits", overwrite=True)

	from PIL import ImageOps	
	sampleFilename =  args.sample
	print("Opening:", sampleFilename)
	sample = PIL.Image.open(sampleFilename)
	size = sample.size
	histogram = getHistoRGB(sample)
	plotHistoRGB(histogram)
	#sample = ImageOps.autocontrast(sample, cutoff= (1, 99))
	sample_r = numpy.array(list(sample.getdata(band=0)), dtype="uint8") 
	sample_g = numpy.array(list(sample.getdata(band=1)), dtype="uint8") 
	sample_b = numpy.array(list(sample.getdata(band=2)), dtype="uint8") 

	print("Loaded image", sample_r)
	sample_r = sample_r / balance_r
	print("deflat image", sample_r)
	sample_g = sample_g / balance_g
	sample_b = sample_b / balance_b
	
	sample_r = sample_r.clip(0,255)
	sample_r = numpy.rint(sample_r)
	sample_r = numpy.array(sample_r, dtype="uint8")
	sample_r = numpy.reshape(sample_r, (size[1], size[0]))

	sample_g = sample_g.clip(0,255)
	sample_g = numpy.rint(sample_g)
	sample_g = numpy.array(sample_g, dtype="uint8")
	sample_g = numpy.reshape(sample_g, (size[1], size[0]))

	sample_b = sample_b.clip(0,255)
	sample_b = numpy.rint(sample_b)
	sample_b = numpy.array(sample_b, dtype="uint8")
	sample_b = numpy.reshape(sample_b, (size[1], size[0]))

	deflat_r = PIL.Image.fromarray(sample_r, mode=None)
	deflat_g = PIL.Image.fromarray(sample_g, mode=None)
	deflat_b = PIL.Image.fromarray(sample_b, mode=None)
	deflat = PIL.Image.merge("RGB", (deflat_r, deflat_g, deflat_b))
	
	if args.display: sample.show()
	if args.display: deflat.show()

	from PIL import ImageChops
	difference = ImageChops.difference(sample, flat)
	difference = ImageChops.constant(difference, 127)
	difference.show()
	
	histogram = getHistoRGB(deflat)
	plotHistoRGB(histogram)
	grayscale = ImageOps.grayscale(deflat)
	histogram = grayscale.histogram()
	print(histogram)
	plotHistoL(histogram)
	contrast = ImageOps.autocontrast(grayscale, cutoff = (0.01, 99.99), preserve_tone=True)
	# contrast = ImageOps.equalize(grayscale)
	histogram = contrast.histogram()
	print(histogram)
	plotHistoL(histogram)
	contrast.show()
	contrast.save("sample_deflat.png")

	
	sys.exit()
