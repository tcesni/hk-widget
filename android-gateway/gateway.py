#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import logging
import re
import datetime
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.api import urlfetch
from django.utils import simplejson

refresh = None
weather = ''
warning = ''
forecast = ''
message = ''

currentUrl = "http://www.weather.gov.hk/textonly/forecast/englishwx.htm"
warningUrl = "http://www.weather.gov.hk/textonly/warning/warn.htm"
forecastUrl = "http://www.weather.gov.hk/textonly/forecast/nday.htm"

# ##########################################################
# Default
class MainHandler(webapp.RequestHandler):
	def get(self):
		self.response.out.write('*** android-gateway ***')
# ##########################################################
# flush parsed Weather Info to user
class GetWeatherHandler(webapp.RequestHandler):
	def get(self):
		global weather
		global warning
		global forecast 
		global refresh		
		global message
		
		self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
		
		if weather == '':
			message += '(no weather)'
			fetchCurrent()
		
		if warning == '':
			message += '(no warning)'
			fetchWarning()
				
		self.response.out.write( 
			simplejson.dumps({
				'current':weather,
				'warning':warning,
				'msg':message
			}, ensure_ascii= False))

# ##########################################################
# Fetch Weather and Warning From HKO
class UpdateWeatherHandler(webapp.RequestHandler):
	def get(self):
		logging.debug('UpdateWeatherHandler')
		self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
		fetchCurrent()
		self.response.out.write(datetime.datetime.now().isoformat() +"\n")
		self.response.out.write("fetch current weather completed\n")
		fetchWarning()
		self.response.out.write("fetch warning in force completed\n")
		self.response.out.write(datetime.datetime.now().isoformat() +"\n")

# ##########################################################
# Fetch Current Weather Info From HKO
class fetchCurrent():
	def __init__(self):
		global refresh
		global currentUrl
		
		refresh = datetime.datetime.now().isoformat()		
		result = urlfetch.fetch(currentUrl)
		if result.status_code == 200:
			fetchCurrentCompleted(result.content)
			logging.debug('updated')
		else:
			logging.error('failed to update weather : %d', result.status_code)
				
class fetchCurrentCompleted():
	def __init__(self, responseText):
	
		global weather

		# Get last update info
		m = re.search('<i>bulletin updated at ([\s\S.]*) HKT ([\s\S.]*)<\/i>', responseText, re.I + re.M)
		if m is None:
			logging.error('Cannot found content')
			weather = null
			return
		else:
			lastupdate = datetime.datetime.strptime(m.group(2) +' '+ m.group(1), "%d/%b/%Y %H:%M").isoformat()
		
		# Get air temperature
		m = re.search('air temperature : ([\d.]*) degrees celsius', responseText, re.I + re.M)
		if m is None:
			temperature = '--'
		else:
			temperature = m.group(1)
				
		# Get humidity
		m = re.search('relative humidity : ([\d.]*) per cent', responseText, re.I + re.M)
		if m is None:
			humidity = '--'
		else:
			humidity = m.group(1)

		# Get weather cartoon and description
		m = re.search('weather cartoon : No.(\s|)([\d.]*) - ([\w^n]*)', responseText, re.I + re.M)
		if m is None:
			cartoon = '0'
		else:
			cartoon = m.group(2)			

		# Get the mean uv index
		m = re.search('the mean uv index recorded at king\'s park : ([\d.]*)', responseText, re.I + re.M)
		if m is None:
			uvindex = '0'
		else:
			uvindex = m.group(1)	
		
		# Get intensity of uv radiation
		m = re.search('intensity of uv radiation : ([\w^n]*)', responseText, re.I + re.M)
		if m is None:
			uvradiation = '0'
		else:
			uvradiation = m.group(1)
			
		weather = {
			"modified":lastupdate, 
			"temperature":temperature,
			"humidity":humidity,
			"cartoon":cartoon,
			"uvindex":uvindex,
			"uvradiation":uvradiation
		}
		logging.debug('fetchWeather completed')

# ##########################################################
# Fetch Warning in force From HKO
class fetchWarning():
	def __init__(self):
		global refresh
		global warningUrl
		refresh = datetime.datetime.now().isoformat()
		result = urlfetch.fetch(warningUrl)
		if result.status_code == 200:
			fetchWarningCompleted(result.content)
			logging.debug('updated')
		else:
			logging.error('failed to update weather : %d', result.status_code)
				
class fetchWarningCompleted():
	def __init__(self, responseText):
	
		global warning

		m = re.search('<!--Warning Codes\n([\\s\\S.]*)\n-->', responseText, re.I + re.M)
		if m is None:
			logging.warning('no warning')
			warning = None
			return
		entries = re.split("\n+", m.group(1))
		#for entry in entries:
		#	logging.info(entry)

		warning = entries
		logging.info('warning in force: %s', entries)		
# ##########################################################
# Main Loop and routes
def main():
  application = webapp.WSGIApplication([
  ('/', MainHandler),
  ('/hkweather/update', UpdateWeatherHandler),
  ('/hkweather', GetWeatherHandler)
  ], debug=True)
  util.run_wsgi_app(application)


if __name__ == '__main__':
  main()
