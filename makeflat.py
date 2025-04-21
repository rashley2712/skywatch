#!/usr/bin/env python
import requests
import argparse
import json
import numpy
import subprocess
import os
import config, imagedata
import sys
import PIL.Image
import PIL.ExifTags

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


def getHistoRGB(image):
	histogram = image.histogram()

	r_histo = histogram[0:255]
	g_histo = histogram[256:511]
	b_histo = histogram[512:767]

	return (r_histo, g_histo, b_histo)

def getHistoL(image):
	histogram = image.histogram()

	return (histogram)


def debugOut(message):
	if debug: print("DEBUG: %s"%message, flush=True)
   
def information(message):
	print(message, flush=True)
	return

	
if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Makes a flat image for the night time exposures.')
	parser.add_argument('-n', '--number', type=int, default=11, help='Number of images to load.' )
	parser.add_argument('-l', '--list', type=str, default="latest", help='Filename to process (or look for the latest).' )
	parser.add_argument('-c', '--config', type=str, default='/home/skywatch/code/skywatch/local.cfg', help='Config file.' )
	parser.add_argument('--debug', action="store_true", default=False, help='Add debug information to the output.' )
	parser.add_argument('--test', action="store_true", default=False, help='Test mode. Don''t upload any data.' )
	parser.add_argument('--display', action="store_true", default=False, help='Show preview and graphs.' )
	
	args = parser.parse_args()
	debug = args.debug
	config = config.config(filename=args.config)
	config.load()
	#debugOut(config.getProperties())
	retakeNow = False

	flatFiles = []
	if args.list == "latest":
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
	else:
		listFile = open(args.list, "rt")
		for line in listFile:
			filename = line.strip()
			if len(filename)<1: continue
			flatFiles.append(filename)
		listFile.close()

	debugOut("flatfiles: %s\nNumber of flats: %d"%(str(flatFiles), len(flatFiles)))
	
	
	image = PIL.Image.open(flatFiles[0])
	if args.display: 
		print("Rendering a preview to the X-session ... will take about 30s")
		image.show()

	r_flats, g_flats, b_flats = [], [], []

	numflats = len(flatFiles)
	numflats = 5
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

	median_r =  median_r / numpy.mean(median_r) 
	median_g =  median_g / numpy.mean(median_g) 
	median_b =  median_b / numpy.mean(median_b) 

	real_flat = [median_r, median_g, median_b]

	median_r = numpy.rint(median_r*255)
	median_r = numpy.array(median_r, dtype="uint8")
	median_r = numpy.reshape(median_r, (size[1], size[0]))

	median_g = numpy.rint(median_g*255)
	median_g = numpy.array(median_g, dtype="uint8")
	median_g = numpy.reshape(median_g, (size[1], size[0]))

	median_b = numpy.rint(median_b*255)
	median_b = numpy.array(median_b, dtype="uint8")
	median_b = numpy.reshape(median_b, (size[1], size[0]))

	print("number of flats processed:", numflats)

	flat_r = PIL.Image.fromarray(median_r, mode=None)
	flat_g = PIL.Image.fromarray(median_g, mode=None)
	flat_b = PIL.Image.fromarray(median_b, mode=None)

	from PIL import ImageOps
	from PIL import ImageChops

	flat = PIL.Image.merge("RGB", (flat_r, flat_g, flat_b))
	contrast = ImageOps.autocontrast(flat, cutoff=0.3, preserve_tone=True)
	contrast.show(title = "test")
	flat.save("flat_feelgood.png")

	flatFilename =  flatFiles[0]
	print("Opening:", flatFilename)
	sample = PIL.Image.open(flatFilename)
	sample_r = numpy.array(list(sample.getdata(band=0)), dtype="uint8") * real_flat[0]
	sample_g = numpy.array(list(sample.getdata(band=1)), dtype="uint8") * real_flat[1]
	sample_b = numpy.array(list(sample.getdata(band=2)), dtype="uint8") * real_flat[2]

	sample_r = numpy.rint(sample_r*255)
	sample_r = numpy.array(sample_r, dtype="uint8")
	sample_r = numpy.reshape(sample_r, (size[1], size[0]))

	sample_g = numpy.rint(sample_g*255)
	sample_g = numpy.array(sample_g, dtype="uint8")
	sample_g = numpy.reshape(sample_g, (size[1], size[0]))

	sample_b = numpy.rint(sample_b*255)
	sample_b = numpy.array(sample_b, dtype="uint8")
	sample_b = numpy.reshape(sample_b, (size[1], size[0]))

	deflat_r = PIL.Image.fromarray(sample_r, mode=None)
	deflat_g = PIL.Image.fromarray(sample_g, mode=None)
	deflat_b = PIL.Image.fromarray(sample_b, mode=None)
	deflat = PIL.Image.merge("RGB", (deflat_r, deflat_g, deflat_b))
	
	sample.show()
	deflat.show()

	#difference = ImageChops.difference(sample, flat)
	#difference.show()  
	#deflat = ImageChops.multiply(sample, flat)
	#deflat.show()
	from PIL import ImageStat
	#print(ImageStat.Stat(difference).extrema)

	from PIL import ImageOps
	contrast = ImageOps.autocontrast(deflat, cutoff=0.3, preserve_tone=True)
	contrast.show()
	contrast.save("sample_deflat.png")

	sys.exit()
