import sys
import csv
import json
import psycopg2
import datetime
import time
from psycopg2.extras import RealDictCursor


db = psycopg2.connect(host="", database="netjets", user="tornado", password="spacetime")
c = db.cursor()

dept_aprt = "CMH"

# Retrieves the coordinates of the airport matching the IATA
query = "SELECT lat,lng from airports where iata = '%s';" % dept_aprt
c.execute(query)
aprt_lat, aprt_lng = c.fetchone()

# Retrieves up to 5 airport IATA's based on the lat/long
query = "SELECT iata FROM airports WHERE (lat BETWEEN %s-1 AND %s+1) and (lng BETWEEN %s-1 AND %s+1) and iata <> '%s' order by abs(lat - %s)*abs(lng - %s) limit 5;"	% (aprt_lat, aprt_lat, aprt_lng, aprt_lng, dept_aprt, aprt_lat, aprt_lng)
c.execute(query)

top5 = c.fetchall()

top5 = [x[0] for x in top5]

print top5
