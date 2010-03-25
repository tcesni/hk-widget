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

from array import array
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.api import urlfetch
from google.appengine.api import memcache
from django.utils import simplejson

weather = None
warning = None
forecast = None

currentUrl = "http://www.weather.gov.hk/textonly/forecast/englishwx.htm"
warningUrl = "http://www.weather.gov.hk/textonly/warning/warn.htm"
forecastUrl = "http://www.weather.gov.hk/textonly/forecast/nday.htm"

# ##########################################################
# Default
class MainHandler(webapp.RequestHandler):
	def get(self):
		self.response.out.write('*** android-gateway ***')

		
def setMemcache(name, value):
	cdata = memcache.get(name)
	timeout = 3600
	if value is None:
		timeout = 0
		
	if cdata is not None:
		if not memcache.set(name, value, timeout):
			logging.error("Memcache::update "+ name +" failed.")
		
	else:
		if not memcache.add(name, value, timeout):
			logging.error("Memcache::create "+ name +" failed.")


def WeekdayEnum(weekday):
	wd = weekday.lower()
	if wd == 'monday':
		return 1
	if wd == 'tuesday':
		return 2
	if wd == 'wednesday':
		return 3
	if wd == 'thursday':
		return 4
	if wd == 'friday':
		return 5
	if wd == 'saturday':
		return 6
	return 0
	
# ##########################################################
# flush parsed Weather Info to user
class GetWeatherHandler(webapp.RequestHandler):
	def get(self):
		global weather
		global warning
		global forecast 
		
		self.response.headers['Content-Type'] = 'application/json'
		message = ''
		
		weather = memcache.get("weather")
		if weather is not None:
			message += 'M1'
		else:
			message += '+1'
			fetchCurrent()
		
		warning = memcache.get("warning")
		if warning is not None:
			message += 'M2'
		else:
			message += '+2'
			fetchWarning()
		
		forecast = memcache.get("forecast")
		if forecast is not None:
			message += 'M3'
		else:
			message += '+3'		
			fetchForecast()
		
		self.response.out.write( 
			simplejson.dumps({
			'current':weather,
			'warning':warning,
			'forecast':forecast,
			'msg':message,
			'notice':'Weather Information is provided by Hong Kong Observatory'
			}, ensure_ascii= False))

# ##########################################################
# Fetch Weather and Warning From HKO
class UpdateWeatherHandler(webapp.RequestHandler):
	def get(self):
		
		global weather
		global warning
		global forecast 
		
		logging.debug('UpdateWeatherHandler')
		self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
		
		fetchCurrent()
		self.response.out.write(datetime.datetime.now().isoformat() +"\tfetch current weather completed\n")
		self.response.out.write(weather)
		self.response.out.write("\n")
				
		fetchWarning()
		self.response.out.write(datetime.datetime.now().isoformat() +"\tfetch warning in force completed\n")
		self.response.out.write(warning)
		self.response.out.write("\n")
		
		fetchForecast()
		self.response.out.write(datetime.datetime.now().isoformat() +"\tfetch weather forecast completed\n")
		self.response.out.write(forecast)
		self.response.out.write("\n")


# ##########################################################
# Fetch Current Weather Info From HKO
class fetchCurrent():
	def __init__(self):
		global currentUrl
		
		result = urlfetch.fetch(currentUrl)
		if result.status_code == 200:
			fetchCurrentCompleted(result.content)
			logging.debug('weather updated')
		else:
			logging.error('failed to update weather : %d', result.status_code)
			
				
class fetchCurrentCompleted():
	def __init__(self, responseText):
	
		global weather

		# Get last update info
		m = re.search('<i>bulletin updated at ([\s\S.]*) HKT ([\s\S.]*)<\/i>', responseText, re.I + re.M)
		if m is None:
			logging.error('Cannot found content')
			setMemcache("weather", None)
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
		
		setMemcache("weather", weather)

# ##########################################################
# Fetch Warning in force From HKO
class fetchWarning():
	def __init__(self):
		global warningUrl

		result = urlfetch.fetch(warningUrl, headers = {'Cache-Control':'max-age=300'})
		if result.status_code == 200:
			fetchWarningCompleted(result.content)
			logging.debug('warning updated')
		else:
			logging.error('failed to update warning : %d', result.status_code)
				
class fetchWarningCompleted():
	def __init__(self, responseText):
	
		global warning
		
		m = re.search('<!--Warning Codes[\r|\n|\r\n]([\\s\\S.]*)[\r|\n|\r\n]-->', responseText, re.I + re.M)
		if m is None:
			logging.warning('no warning')
			warning = None
			setMemcache("warning", warning)			
			return
			
		# logging.info(m.group(0)) 
		
		entries = re.split("\n+", m.group(1))
		# for entry in entries:
		#	logging.info(entry)

		warning = entries
		logging.info('warning in force: %s', warning)
		setMemcache("warning", warning)

# ##########################################################
# Fetch Weather Forecast From HKO
class fetchForecast():
	def __init__(self):
		global forecastUrl
		
		result = urlfetch.fetch(forecastUrl)
		if result.status_code == 200:
			fetchForecastCompleted(result.content)
			logging.debug('forecast updated')
		else:
			logging.error('failed to update forecast : %d', result.status_code)

				
class fetchForecastCompleted():
	def __init__(self, responseText):
	
		global forecast
		
		fc = [0,1,2,3,4,5,6] # 7 days forecast
				
		# date
		m = re.findall('date\/month\\s(\\S+)\/(\\S+)\\s?\\((\\S+)\\)', responseText, re.I + re.M)
		if m is None:
			logging.warning( 'failed to fetch forecast date')
			return
		
		idx = 0
		for entry in m:
			wd = WeekdayEnum(entry[2])
			fcd =  { 'd':entry[0] +'/'+ entry[1], 'wd':wd, 'cartoon':0, 'tl':0, 'th':0, 'hl':0, 'hh':0 }
			fc[idx] = fcd
			idx = idx + 1
		
		# cartoon
		m = re.findall('cartoon no.\\s(\\d+)\\s', responseText, re.I + re.M)
		if m is None:
			logging.warning( 'failed to fetch forecast cartoon')
			return
		idx = 0
		for entry in m:
			fc[idx]['cartoon'] = entry	# cartoon
			idx = idx + 1
			
		# temperature range
		m = re.findall('temp range:\\s(\\S+)\\s-\\s(\\S+)\\sC', responseText, re.I + re.M)
		if m is None:
			logging.warning( 'failed to fetch forecast temp range')
			return
			
		idx = 0
		for entry in m:
			fc[idx]['tl'] = entry[0]		# temperature range lowest
			fc[idx]['th'] = entry[1]	# temperature range highest
			idx = idx + 1				

		# r.h. range
		m = re.findall('r.h. range:\\s(\\d+)\\s-\\s(\\d+)\\sper cent', responseText, re.I + re.M)
		if m is None:
			logging.warning( 'failed to fetch forecast relative humidity range')
			return
			
		idx = 0
		for entry in m:
			fc[idx]['hl'] = entry[0]	# relative humidity range lowest
			fc[idx]['hh'] = entry[1]	# relative humidity range highest
			idx = idx + 1		

		forecast = fc
		logging.info(forecast)		
		setMemcache("forecast", forecast)
            
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
