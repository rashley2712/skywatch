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
import time

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

def uploadMetadata(jsonData, URL):
		success = False
		information("Sending JSON payload to: %s"%URL)
		try: 
			response = requests.post(URL, json=jsonData)
			responseJSON = json.loads(response.text)
			print(json.dumps(responseJSON, indent=4))
			if responseJSON['status'] == 'success': success = True
			response.close()
		except Exception as e: 
			success = False
			print(e, flush=True)
				
		print(success, flush=True)
		return success


def uploadToServer(imageFilename, URL):
	destinationURL = URL
	files = {'camera': open(imageFilename, 'rb')}
	headers = { 'Content-type': 'image/jpeg'}
	try:
		response = requests.post(destinationURL, files=files)
		information("skyWATCH server's response code: " + str(response.status_code))
		response.close()
	except Exception as e: 
		information("error: " + repr(e))
		return 
	information("Uploaded image to %s\n"%destinationURL) 
	return
   
def information(message):
	print(message, flush=True)
	return

def renderText(image, imageData):
	try:
		from PIL import ImageFont
		from PIL import ImageDraw 

		text = "%s | sun: %.2f | moon: %.2f (%.2f%%)"%(imageData.timestamp, imageData.ephemeris['sunElevation'], imageData.ephemeris['moonElevation'], imageData.ephemeris['moonIllumination'])
		print("Adding annotation:", text)
		draw = ImageDraw.Draw(image)
		size = image.size
		if size[0]>3000: fontSize = 54
		else: fontSize = 26
		font = ImageFont.truetype("DejaVuSans.ttf", fontSize)
		w = draw.textlength(text, font=font)
		h = fontSize * 1
		W, H = image.size
		draw.text(((W-w)/2,0), text, (255,255,255), font=font)

	except Exception as e:
		print("Unable to render text")
		print(e)

	return image


	
if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Performs post processing of the skycam images.')
	parser.add_argument('-t', '--cadence', type=int, default=5, help='Cadence in seconds.' )
	parser.add_argument('-f', '--filename', type=str, default="latest", help='Filename to process (or look for the latest).' )
	parser.add_argument('-c', '--config', type=str, default='/home/skywatch/code/skywatch/local.cfg', help='Config file.' )
	parser.add_argument('--debug', action="store_true", default=False, help='Add debug information to the output.' )
	parser.add_argument('--test', action="store_true", default=False, help='Test mode. Don''t upload any data.' )
	parser.add_argument('--display', action="store_true", default=False, help='Show preview and graphs.' )
	
	
	args = parser.parse_args()
	debug = args.debug
	config = config.config(filename=args.config)
	config.load()
	debugOut(config.getProperties())
	retakeNow = False

	if args.filename == "latest":
		# Generate the list of files in the specified folder
		cameraPath = config.camera['outputpath']
		debugOut("Looking for the most recent file in %s"%cameraPath)
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
		imageFile = { "filename": args.filename } 

	imageData = imagedata.imagedata(debug = False)
	JSONFilename = os.path.join(config.camera["JSONpath"], os.path.splitext(imageFile["filename"].split('/')[-1])[0] + ".json")
	print("JSONFilename:", JSONFilename)
	imageData.setFilename(JSONFilename)
	imageData.load()
	imageData.show()
	
	image = PIL.Image.open(imageFile["filename"])
	if args.display: 
		print("Rendering a preview to the X-session ... will take about 30s")
		image.show()

	try: 
		encoding = imageData.encoding
	except AttributeError:
		if (os.path.splitext(imageData.filename)[1] == ".jpg") or (os.path.splitext(imageData.filename)[1] == ".jpeg"): 
			imageData.setProperty("encoding", "jpg")
			encoding="jpg"
		if (os.path.splitext(imageData.filename)[1] == ".png"): 
			imageData.setProperty("encoding", "png")
			encoding="png"

	try: 
		expTime = float(imageData.exposure)
	except AttributeError:
		expTime = -1
		print("JSON does not contain the exposure time.", flush=True)

	def showTags(tags):
		for key in tags.keys():
			print(PIL.ExifTags.TAGS[key], tags[key])

	def getExposure(exif):
		for key in exif.keys():
			if PIL.ExifTags.TAGS[key] == "ExposureTime": return float(exif[key])

	if expTime==-1 and encoding == "jpg":
		exif_data = image._getexif()
		if exif_data is not None:
			print(str(exif_data))
			showTags(exif_data)
			expTime = getExposure(exif_data)
			debugOut("EXIF: expTime: %.4f"%expTime)	
		
	imageData.setProperty("exposure", expTime)
	
	size = image.size
	imageData.setProperty("width", size[0])
	imageData.setProperty("height", size[1])
	debugOut("size: %s"%str(size))
	(width, height) = size
	
	debugOut("Exposure time is %.4f seconds"%(expTime))
	if imageData.mode=="night":
		imageData.setProperty("exposure", round(expTime, 2))
	debugOut("Bands: %s"%str(image.getbands()))

	imageData.save()		

	if imageData.mode == "night":
	#if True:
		# Choose the central 12% of the image
		left = int( width/2 - width/8)
		right = int( width/2 + width/8)
		upper = int( height/2 - height/8)
		lower = int( height/2 + height/8)
		
		histogram = getHistoRGB(image)
		if args.display: plotHistoRGB(histogram)
		croppedImage = image.crop((left, upper, right, lower))
		croppedImage = croppedImage.convert('L')
		data = croppedImage.getdata()
		
		histogram = getHistoL(croppedImage)
		if args.display: plotHistoL(histogram)
		peak = numpy.argmax(histogram)
		median = numpy.median(data)
		mean = numpy.mean(data)
		min = numpy.min(data)
		max = numpy.max(data)
		print("Peak: %d, Median: %d, Mean: %.1f, Min: %d, Max: %d"%(peak, median, mean, min, max), flush=True)

		newExpTime = expTime
		if median > 240: 
			newExpTime = expTime * 0.50
			information("image is quite saturated, suggesting exposure goes from %.4f to %.4f seconds."%(expTime, newExpTime))
			retakeNow = True
		elif median>200:
			newExpTime = expTime * 0.75
			information("image is little bit saturated, suggesting exposure goes from %.4f to %.4f seconds."%(expTime, newExpTime))
		elif median>120:
			newExpTime = expTime * 0.9
			information("image is little bit saturated, suggesting exposure goes from %.4f to %.4f seconds."%(expTime, newExpTime))

		if median <60: 
			newExpTime = expTime * 2.5
			information("image is a quite under-exposed, suggesting exposure goes from %.4f to %.4f seconds."%(expTime, newExpTime))
			retakeNow = True
		elif median <90: 
			newExpTime = expTime * 1.25
			information("image is a little under-exposed, suggesting exposure goes from %.4f to %.4f seconds."%(expTime, newExpTime))
		
		# Never go over 100 seconds
		if newExpTime > 100: 
			newExpTime = 100
			retakeNow = False
			print("Requested exposure out of bounds >100s.", flush=True)

		config.camera['suggestedTexp'] = round(newExpTime,4)
		config.save()
		
	if retakeNow:
		print("retake requested", flush=True)
		sys.exit(1)
	

	if imageData.mode=="nightdkjlfkldf":
		print("Performing a de-flat process.")
		# Process the balance frame

		# Split the image into RGB
		r_data = numpy.array(list(image.getdata(band=0)), dtype="uint8")
		g_data = numpy.array(list(image.getdata(band=1)), dtype="uint8")
		b_data = numpy.array(list(image.getdata(band=2)), dtype="uint8")
		print("Split the raw image into [R, G, B] bands.")
		
		# Load the numpy data
		balance = numpy.load(config.processor["balance"]["r"])
		print("Loaded the r-band balance data.")
		r_data = r_data / balance
		
		balance = numpy.load(config.processor["balance"]["g"])
		print("Loaded the g-band balance data.")
		g_data = g_data / balance
		
		balance = numpy.load(config.processor["balance"]["b"])
		b_data = b_data / balance
		print("Loaded the b-band balance data.")
		
		# Re-construct the image
		processed_r = r_data.clip(0,255)
		processed_r = numpy.rint(processed_r)
		processed_r = numpy.array(processed_r, dtype="uint8")
		processed_r = numpy.reshape(processed_r, (size[1], size[0]))

		processed_g = g_data.clip(0,255)
		processed_g = numpy.rint(processed_g)
		processed_g = numpy.array(processed_g, dtype="uint8")
		processed_g = numpy.reshape(processed_g, (size[1], size[0]))

		processed_b = b_data.clip(0,255)
		processed_b = numpy.rint(processed_b)
		processed_b = numpy.array(processed_b, dtype="uint8")
		processed_b = numpy.reshape(processed_b, (size[1], size[0]))

		processed_r = PIL.Image.fromarray(processed_r, mode=None)
		processed_g = PIL.Image.fromarray(processed_g, mode=None)
		processed_b = PIL.Image.fromarray(processed_b, mode=None)
		processed = PIL.Image.merge("RGB", (processed_r, processed_g, processed_b))
	else:
		print("Not performing a de-flat process.")
		processed = image.copy()		
	processedPath = config.processor['processedpath']
	filename = imageData.filename
	processedFilename = os.path.join(processedPath, filename)
	processed.save(processedFilename)
	print("Save processed image to %s"%processedFilename)
	

	print("Preparing the image for web upload.", flush = True)
	# Apply any transformations needed for the web version of the image
	try: 
		transforms = config.processor['web']
		for t in transforms.keys():
			if t=="rotate" : 
				image = image.rotate(transforms[t])
				print("Rotating the image by", transforms[t], "degrees.", flush=True)
			if t=="resize" :
				factor = transforms[t]
				(width, height) = (int(image.width * factor), int(image.height * factor))
				image = image.resize( (width, height) )
				print("Resizing the image by a factor of", transforms[t], flush=True)	
	except KeyError:
		print("Transform: No transformations to apply...", flush=True)
	
	uploadURL = config.processor["cameraUploadURL"]
	webPath = config.processor["webPath"]
		
	# Render the annotations onto the image
	image = renderText(image, imageData)
	# Write the annotated image
	webFilename = os.path.join(webPath, imageFile['filename'].split('/')[-1])
	imageFile['webFilename'] = webFilename
	print(imageFile)
	image.save(imageFile['webFilename'])

	lowBandwidth = False
	try:
		if config.bandwidthlimited==1: 
			print("Upload bandwidth is limited. We will re-scale the image.", flush=True)
			lowBandwidth = True
	except AttributeError:
		print("Assuming full upload bandwidth is available.", flush=True)

	
	if lowBandwidth:
		if imageFile['filename'].find('small')!=-1:
			print("Filename already contains the word 'small' ... not resizing.")
		else:
			newFilename = imageFile['filename'].split('.')[0] + "_small.jpg"
			imageData.setFilename(os.path.splitext(newFilename)[0] + ".json")
			imageData.setProperty("resized", True)
			imageData.setProperty("width", int(size[0]/4))
			imageData.setProperty("height", int(size[1]/4))
			scaleCommand = ["convert", imageFile['filename'], '-resize', '1014', newFilename]
			#scaleCommand.append()
			commandLine =""
			for s in scaleCommand:
				commandLine+= s + " "
			print("Running:", commandLine, flush=True)
			subprocess.call(scaleCommand)
			# Reload the re-scaled image
			image = Image.open(newFilename)
			imageFile['filename'] = newFilename
			imageData.setProperty("file", os.path.basename(newFilename))
			imageData.save()
		

	sizeinBytes = os.path.getsize(imageFile['filename'])
	information("Image size is: %s %.2f kb"%(str(image.size), sizeinBytes/1024))
	# If upload is set... upload to skyWATCH server
	# args.test = True
	if not args.test: 
		#uploadMetadata(imageData.getJSON(), config.imagedataURL)
		URL = config.processor['cameraUploadURL']
		try: 
			if config.camera['local'] == "true":
				URL = config.camera['localURL']
		except AttributeError:
			URL = "http://localhost:8080/pictureupload"
		uploadToServer(imageFile['webFilename'], URL)	
		time.sleep(3)
		# Upload the image meta data to the BigQuery table
		metaURL = URL[0:URL.rfind("/")] + "/imagedata"
		print("Uploading image meta data to %s"%metaURL)
		tmstp = imageData._json['timestamp']
		reformattedTimestamp = "%s-%s-%s %s:%s:%s"%(tmstp[0:4], tmstp[4:6], tmstp[6:8], tmstp[9:11], tmstp[11:13], tmstp[13:15])
		import socket
		hostname = socket.gethostname()
		postData = { "timestamp" : reformattedTimestamp, "hostname" : hostname, "filename" : imageData._json['filename']}
		postData['json'] = imageData._json
		success = False
		try: 
			response = requests.post(metaURL, json=postData)
			print("Server status code: ", response.status_code, flush=True)
			if (response.status_code!=200): 
				print("Data not uploaded.")
				success = False
			responseJSON = json.loads(response.text)
			print("Response from skywatch server:", responseJSON['status'], flush=True)
			if responseJSON['status'] == 'OK': success = True
			response.close()
		except Exception as e: 
			success = False
			print(e, flush=True)
		

	
	
