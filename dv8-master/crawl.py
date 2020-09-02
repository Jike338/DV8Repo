from bs4 import BeautifulSoup
import urllib.request
import sys
import datetime

# example flight: 20140413328085 | TEB       |      20140413 | 22:11:00      | BOS      |     20140413 | 23:05:00     | F2TH      | EJA253

def get_weather_report(aprt,my_date,my_time):
	"""
	Retrieves the appropriate weather data from Iowa Environment Mesonet

	:param aprt: The airport to query
	:param my_date: The date to query
	:param my_time: The time to query
	:returns: Weather data
	"""

	# Parse the date
	year = my_date[0:4]
	month = my_date[4:6]
	day = my_date[6:8]
	print (year,month,day)

	# Construct the URL
	url = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?station="
	url += aprt
	url += "&data=all&year1="+year+"&month1="+month+"&day1="+day+"&year2="+year+"&month2="+month+"&day2="+day+"&tz=Etc%2FUTC&format=tdf&latlon=no&direct=no&report_type=1&report_type=2"
	print (url)

	# Make a request to the URL
	f = urllib2.urlopen(url)
	myfile = f.read()

	# Parse response
	my_time_time = datetime.datetime.strptime(my_time, '%H:%M')
	lines = myfile.split("\n")
	line_cnt = 0
	min_time_diff = 1000
	min_line = ""
	for line in lines:
		line_cnt += 1
		if line_cnt < 7:
			continue
		parts = line.split("\t")
		if len(parts) < 2:
			continue
		this_time = parts[1].split(" ")[1]
		this_time_time = datetime.datetime.strptime(this_time, '%H:%M')
		time_diff = abs(this_time_time - my_time_time).total_seconds() / 60
		if time_diff < min_time_diff:
			min_time_diff = time_diff
			min_line = line
	return min_line.split("\t")[21]


def translate_metar(metar_str):
	"""
	Converts a metar string to a list of usable data
	"""

	terms = []
	parts = metar_str.split(" ")
	for part in parts:
		if part[-2:]=="KT":
			direction = part[0:3]
			speed = part[3:5]
			terms.append("wind direction "+str(direction)+" with speed " +str(speed))
		elif part[0:3]=="BKN" or part[0:3]=="SCT" or part[0:3]=="FEW" or part[0:3]=="OVC" or part[0:3]=="CLR":
			status = part[0:3]
			status_label = ""
			elevation = part[4:]
			if status == "BKN":
				status_label = "broken"
			elif status == "SCT":
				status_label = "scattered"
			elif status == "FEW":
				status_label = "few clouds"
			elif status == "OVC":
				status_label = "overcast"
			elif status == "CLR":
				status_label = "clear clouds"
			if elevation == "":
				terms.append(status_label)
			else:
				terms.append(status_label+" at elevation "+elevation)
		elif part[0] == "A" and len(part) == 5:
			terms.append("visibility: "+part[1:3]+"."+part[3:5])
	return terms


###MAIN EXAMPLE###

#dept_aprt = "TEB"
#dept_date = "20140413"
#dept_time = "22:11"

#arr_aprt = "JFK"
#arr_date = "20140413"
#arr_time = "23:05"

#metar_dept = get_weather_report(dept_aprt,dept_date,dept_time)
#metar_arr = get_weather_report(arr_aprt,arr_date,arr_time)

# metar_dept = "KTEB 132151Z 18013G18KT 10SM CLR 26/11 A2998 RMK AO2 SLP151 T02560111"
# metar_arr = "KBOS 132254Z 19007KT 10SM FEW050 SCT220 OVC250 16/09 A3002 RMK AO2 SLP167 T01560094"

# print "Departure:", metar_dept
# print "Arrival:", metar_arr

#print translate_metar(metar_dept)
#print translate_metar(metar_arr)
