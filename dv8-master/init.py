import tornado.ioloop
import tornado.web
import tornado.websocket
import os.path
from pquery import *
import pquery
import sys
import math
import cache_management
from crawl import get_weather_report, translate_metar
import os
import shutil
import re
import csv
import pandas as pd
from datetime import datetime, timedelta
from scipy.cluster.hierarchy import fclusterdata
from scipy.spatial.distance import pdist
from scipy.cluster.hierarchy import linkage
from scipy.cluster.hierarchy import fcluster
from scipy.spatial.distance import squareform
from sklearn.metrics import silhouette_score
from collections import Counter
import numpy as np
from numpy import dot
from numpy.linalg import norm
import math
import time

#global var
port = -1
queryIteration = 1
cache_path = ''
cluster_path = os.path.join(os.path.dirname(__file__), "cluster/")

settings = dict(
        template_path = os.path.join(os.path.dirname(__file__), "templates/"),
        static_path = os.path.join(os.path.dirname(__file__), "static/"),
        cache_path = os.path.join(os.path.dirname(__file__), "cache/"),
        cluster_path = os.path.join(os.path.dirname(__file__), "cluster/"),
        debug = True
)
                

class MainHandler(tornado.web.RequestHandler) :
        def get(self):
                self.render('main/index.html', error="", port=port)

##MultiHandler VS SingleHandler
class SingleHandler(tornado.web.RequestHandler) :
        def get(self):
                flight_id = self.get_argument("flight_id")
                cache_path = self.get_argument("cache_path")
                
                points(flight_id=flight_id, file_name="static/singleflightviz/data.csv", single=True, using_demo=False)

                self.render("singleflightviz/index.html", cache_path=cache_path)

class MultiHandler(tornado.web.RequestHandler) :
        global cache_path

        def get(self):
                
                mode = self.get_argument("mode")
                from_date = self.get_argument("from_date")
                to_date = self.get_argument("to_date")
                airline=""
                aircraft = ""
                
                try: #Example queries aren't updated for this TODO - update examples
                        airline = self.get_argument("airline")
                        aircraft = self.get_argument("aircraft")
                except:
                        pass

                singleArrAprt = ""
                singleDeptAprt = ""
                
                        
                #Get Dept Airports
                i=1
                dept_aprts = []

                try:
                        dept_lat_min = self.get_argument("dept_lat_min")
                        dept_lat_max = self.get_argument("dept_lat_max")
                        dept_lng_min = self.get_argument("dept_lng_min")
                        dept_lng_max = self.get_argument("dept_lng_max")
                except:
                        dept_lat_min = ""
                        dept_lat_max = ""
                        dept_lng_min = ""
                        dept_lng_max = ""
                        
                if (dept_lat_min == ""):
                        dept_lat_min = 91
                if (dept_lat_max == ""):
                        dept_lat_max = -1
                if (dept_lng_min == ""):
                        dept_lng_min = 181
                if (dept_lng_max == ""):
                        dept_lng_max = -1       

                airports = csv.reader(open('airports.csv', 'r'), delimiter=",")
                for row in airports:
                        if(row[1]=='Latitude'):
                                print(dept_lat_min)
                                print(dept_lat_max)
                                print(dept_lng_min)
                                print(dept_lng_max)
                                continue
                        if(float(row[1])>=float(dept_lat_min) and float(row[1])<=float(dept_lat_max) and float(row[2])>=float(dept_lng_min) and float(row[2])<=float(dept_lng_max)):
                                dept_aprts.append(row[0])
                                
                next_dept = self.get_argument("from_aprt")
                if (len(next_dept) > 0): 
                        dept_aprts.append(next_dept)
                        singleDeptAprt = next_dept
                try: #It eventually try to find dept_aprtN+1 when theres only N dept aprts
                        while(i < 100): #for some reason while(true) doesnt work
                                argString = "from_aprt" + str(i)
                                next_dept = self.get_argument(argString)
                                if (len(next_dept) > 0): 
                                        dept_aprts.append(next_dept)
                                i += 1
                except:
                        pass

                #Get Arr Airports
                i=1
                arr_aprts = []

                try:
                        arr_lat_min = self.get_argument("arr_lat_min")
                        arr_lat_max = self.get_argument("arr_lat_max")
                        arr_lng_min = self.get_argument("arr_lng_min")
                        arr_lng_max = self.get_argument("arr_lng_max")
                except:
                        arr_lat_min = ""
                        arr_lat_max = ""
                        arr_lng_min = ""
                        arr_lng_max = ""
                        
                if (arr_lat_min == ""):
                        arr_lat_min = "91"
                if (arr_lat_max == ""):
                        arr_lat_max = "-1"
                if (arr_lng_min == ""):
                        arr_lng_min = "181"
                if (arr_lng_max == ""):
                        arr_lng_max = "-1"

                ## Why load the airport data twice?
                airports2 = csv.reader(open('airports.csv', 'r'), delimiter=",")        
                for row in airports2:
                        if(row[1]=='Latitude'):
                                print(arr_lat_min)
                                print(arr_lat_max)
                                print(arr_lng_min)
                                print(arr_lng_max)
                                continue
                        if(float(row[1])>=float(arr_lat_min) and float(row[1])<=float(arr_lat_max) and float(row[2])>=float(arr_lng_min) and float(row[2])<=float(arr_lng_max)):
                                arr_aprts.append(row[0])

                
                next_arr = self.get_argument("to_aprt")
                if (len(next_arr) > 0): 
                        arr_aprts.append(next_arr)
                        singleArrAprt = next_arr
                try:
                        while(i < 100): #for some reason while(true) doesnt work
                                argString = "to_aprt" + str(i)
                                next_arr = self.get_argument(argString)
                                if (len(next_arr) > 0): 
                                        arr_aprts.append(next_arr)
                                i += 1
                except:
                        pass

                #Get date ranges
                i=1
                from_dates = []
                next_from = self.get_argument("from_date")
                if (len(next_from) > 0): 
                        split_from_date = next_from.split('/')
                        formatted = split_from_date[2]  + split_from_date[0].rjust(2,'0') + split_from_date[1].rjust(2,'0')
                        from_dates.append(formatted)
                try:
                        while(i < 100): #for some reason while(true) doesnt work
                                argString = "from_date" + str(i)
                                next_from = self.get_argument(argString)
                                if (len(next_from) > 0): 
                                        split_from_date = next_from.split('/')
                                        formatted = split_from_date[2]  + split_from_date[0].rjust(2,'0') + split_from_date[1].rjust(2,'0')
                                        from_dates.append(formatted)
                                i += 1
                except:
                        pass
                i=1
                to_dates = []
                next_to = self.get_argument("to_date")
                if (len(next_to) > 0): 
                        split_to_date = next_to.split('/')
                        formatted = split_to_date[2]  + split_to_date[0].rjust(2,'0') + split_to_date[1].rjust(2,'0')
                        to_dates.append(formatted)
                try:
                        while(i < 100): #for some reason while(true) doesnt work
                                argString = "to_date" + str(i)
                                next_to = self.get_argument(argString)
                                if (len(next_to) > 0): 
                                        split_to_date = next_to.split('/')
                                        formatted = split_to_date[2]  + split_to_date[0].rjust(2,'0') + split_to_date[1].rjust(2,'0')
                                        to_dates.append(formatted)
                                i += 1
                except:
                        pass
                        
                print(to_dates)
                print(from_dates)
                        
                        
                #Check Boxes
                #dept_nearby = ("on" in self.get_argument("dept_nearby"))
                #arr_nearby = ("on" in self.get_argument("arr_nearby"))
                try:
                        #use full data if box is checked
                        use_demo = ("on" in self.get_argument("demo_data_check"))
                except:
                        use_demo = False
                dept_nearby = ""
                arr_nearby = ""
                
                
                
                
                if mode == 'points': #multi point view
                
                
                        #----------check cache------------
                        params = {}
                        params["P1"] = ""
                        params["P2"] = ""
                        params["T1"] = ""
                        params["T2"] = ""
                        params["L"] = airline
                        params["C"] = aircraft
                        for aprt in dept_aprts:
                                params["P1"] = params["P1"] + aprt
                        for aprt in arr_aprts:
                                params["P2"] = params["P2"] + aprt
                        for date in from_dates:
                                params["T1"] = params["T1"] + date
                        for date in to_dates:
                                params["T2"] = params["T2"] + date

                        cache_path = cache_management.cache_folder+airline+"-"+aircraft+"-"+''.join(from_dates)+"-"+''.join(to_dates)
                        if 0<=float(dept_lat_max) and 0<=float(dept_lng_max) and 0<=float(arr_lat_max) and 0<=float(arr_lng_max):
                                cache_path = cache_path+str(dept_lat_min)+str(dept_lat_max)+str(dept_lng_min)+str(dept_lng_max)+str(arr_lat_min)+str(arr_lat_max)+str(arr_lng_min)+str(arr_lng_max)
                        elif 0<=float(dept_lat_max) and 0<=float(dept_lng_max):
                                cache_path = cache_path+str(dept_lat_min)+str(dept_lat_max)+str(dept_lng_min)+str(dept_lng_max)+''.join(arr_aprts)
                        elif 0<=float(arr_lat_max) and 0<=float(arr_lng_max):
                                cache_path = cache_path+''.join(dept_aprts)+str(arr_lat_min)+str(arr_lat_max)+str(arr_lng_min)+str(arr_lng_max)
                        else:
                                cache_path = cache_management.cache_folder + cache_management.get_dir_name(params)
                        
                        csv_name = cache_path+'/data.csv'
                        if cache_management.is_in_cache(params):
                                print ('\nCACHE HIT\n')
                                cacheData = pquery.read_json(cache_folder = csv_name[0:-8])
                                if cacheData == None:
                                        #cache fetch errored
                                        cache_management.delete_from_cache(cache_management.get_dir_name(params))
                                else:
                                        LLData = cacheData
                                        self.render("../static/multipointviz/index.html", file_name=csv_name, error="", dept_aprt=singleDeptAprt, arr_aprt=singleArrAprt, 
                                                                airline=airline, aircraft=aircraft, from_date=from_date, to_date=to_date, is_iterated=LLData['is_iterated'], port=port)
                                        shutil.copy(csv_name,cluster_path+"data.csv")

                        #elif cache_management.incremental_cache_check(params):
                        #       pquery.read_json(cache_folder = csv_name[0:-8])
                        #       self.render("../static/multipointviz/index.html", file_name=csv_name, error="", dept_aprt=singleDeptAprt, arr_aprt=singleArrAprt, airline=airline, aircraft=aircraft, from_date=from_date, to_date=to_date)
                        else:                   
                                cache_management.create_dir(cache_path)
                
                                error = points(dept_aprts=dept_aprts, arr_aprts=arr_aprts, from_dates=from_dates, to_dates=to_dates, airline=airline, aircraft=aircraft, file_name=csv_name, using_demo=use_demo, dept_nearby=dept_nearby, arr_nearby=arr_nearby)

                                if error:
                                        ## delete the directory & sub-directory recursively.
                                        shutil.rmtree(cache_path)
                                else:
                                        cache_management.manage_cache_size()
                                self.render("../static/multipointviz/index.html", error=error, file_name=csv_name, dept_aprt=singleDeptAprt, 
                                        arr_aprt=singleArrAprt, airline=airline, aircraft=aircraft, from_date=from_date, to_date=to_date, is_iterated=0, port=port)
                                shutil.copy(csv_name,cluster_path+"data.csv")
                        #---------------End Cache Check -------------------------
                else: #NOT multi point view
                        if mode == "flights" and (len(dept_aprts) < 1 or len(arr_aprts) < 1):
                                        error = points(dept_aprts=dept_aprts, arr_aprts=arr_aprts, from_date=from_date, to_date=to_date, airline=airline, file_name="static/multiflightgeoviz/data.csv", using_demo=use_demo, dept_nearby=dept_nearby, arr_nearby=arr_nearby, geo=True)
                                        if not error:
                                                self.redirect("static/multiflightgeoviz/index.html")
                                        else:
                                                self.render('main/index.html', error=error, port=port)

                        elif mode == "flights":
                                        error = flights(dept_aprts=dept_aprts, arr_aprts=arr_aprts, from_date=from_date, to_date=to_date, airline=airline, file_name="static/multiflightviz/data.csv", dept_nearby=dept_nearby, arr_nearby=arr_nearby)
                                        if not error:
                                                title = "All Found Flights"
                                                if len(dept_aprts) > 0:
                                                        title += " from " + dept_aprts[0]
                                                        for ap in dept_aprts[1:-1]:
                                                                title += ", " + ap
                                                        if len(dept_aprts) > 1:
                                                                title += " or " + dept_aprts[-1]
                                                if len(arr_aprts) > 0:
                                                        title += " to " + arr_aprts[0]
                                                        for ap in arr_aprts[1:-1]:
                                                                title += ", " + ap
                                                        if len(arr_aprts) > 1:
                                                                title += " or " + arr_aprts[-1]
                                                self.render("multiflightviz/index.html",title=title, from_date=from_date, to_date=to_date)
                                        else:
                                                self.render('main/index.html', error=error, port=port)



class WebSocketHandler(tornado.websocket.WebSocketHandler):
        def open(self):
                print ("Web Socket Opened")
        
        def on_message(self, message):
                global queryIteration
                
                print ("\nMessage Recieved:", message[0:500])
                
                if message == 'iterate_first':
                        queryIteration = 1
                        iterateQuery(self)
                        
                elif message == 'iterate':
                        iterateQuery(self)
                        
                elif message[0:5] == 'local':
                        message = json.loads(message[5:])
                        where = ' WHERE hash IN ( '
                        
                        for k in message:
                                for h in range(message[k][0], message[k][1]):
                                        if h not in message[k][2]:
                                                where += str(h) + ','
                        where = where[:-1] + ')'
                        
                        #for k in message:
                        #       already_loaded = ','.join([str(x) for x in message[k][2]])
                        #       where += '(hash < ' + str(message[k][1]) + ' AND hash > ' + str(message[k][0]) + ' AND hash NOT IN (' + already_loaded + ')) OR'
                        #where = where[0:-3]
                        
                        if len(where) > 25:
                                c = pquery.given_where(where)
                        
                                file_name = 'static/local_data.csv'
                                c.scroll(0, 'absolute')
                                append_csv(file_name=pquery.LLData['points_file'], results_cursor=c);
                                c.scroll(0, 'absolute')
                                generate_csv(file_name, "flight_id,dept_aprt,dept_date_utc,dept_time_utc,arr_aprt,arr_date_utc,arr_time_utc,icao,acft_type,point_time,lat,lng,alt,ground,hash,", c)
                                self.write_message(file_name)
                        else:
                                print ('All local data already loaded')
                                self.close()
                        
                elif message[0:5] == 'weath':
                        data = message.split(',') #index 1: fid, 2-4: dept, 5-7: arr
                        
                        results = pquery.get_weather_data(data[1], data[2:])
                        
                        #the order sent is the only thing tracking whether data is dept/arr
                        self.write_message(results[0])
                        self.write_message(results[1])
                        self.close()

                elif message[0:8]== 'cluster1':
                        messages = message.split(",")
                        thred = float(messages[1])
                        num_points = int(messages[2])
                        metric = int(messages[3])
                        # start_time = time.time()
                        clustering(thred,self,1,num_points,metric)
                        # end_time = time.time()
                        # runningtime = end_time-start_time
                        # print("running time: " + str(runningtime))
                        self.close()

                elif message[0:8]== 'cluster2':
                        messages = message.split(",")
                        thred = float(messages[1])
                        num_points = int(messages[2])
                        metric = int(messages[3])
                        # start_time = time.time()
                        clustering(thred,self,2,num_points,metric)
                        # end_time = time.time()
                        # runningtime = end_time-start_time
                        # print("running time: " + str(runningtime))
                        self.close()


                else: #message = comma separated list of fids
                        c = pquery.grab_from_fid_list(message)
                        CreateAggCSV(c)
                        self.close()
                        
        def on_close(self):
                print ('Web Socket Closed')


## Distance calculation?
def distance(lat1, lng1, lat2, lng2):
      dept_lat_rad = math.radians(lat1)
      dept_lng_rad = math.radians(lng1)
      arr_lat_rad = math.radians(lat2)
      arr_lng_rad = math.radians(lng2)
      earth_radius = 3440
      d = math.acos(math.cos(dept_lat_rad)*math.cos(dept_lng_rad)*math.cos(arr_lat_rad)*math.cos(arr_lng_rad) + math.cos(dept_lat_rad)*math.sin(dept_lng_rad)*math.cos(arr_lat_rad)*math.sin(arr_lng_rad) + math.sin(dept_lat_rad)*math.sin(arr_lat_rad)) * earth_radius
      result = int(round(d))
      return result


        



def CreateAggCSV(c):
        print ("Create Agg CSV")
        file = open('static/aggregate_data.csv', 'w+')
        
        #header
        file.write("flight_id,airline,flight,acft,avg_alt,avg_speed,dept_aprt,dept_date,dept_time,arr_aprt,arr_date,arr_time,actual_distance,great_circle_distance\n");
        
        #do calculations
        alt_sum = 0
        speed_sum = 0
        count = 0
        dept = 0
        dept_date = 0
        dept_time = 0
        arr = 0
        arr_date = 0
        arr_time = 0
        acft = 0
        airline = 0
        prv_lat = 0;
        prv_lng = 0;
        lat = 0;
        lng = 0;
        act_dist = 0
        gc_dist = 0
        last_fid = -1
        for row in c: #row = [fid, alt, ground]
                if row[0] != last_fid:
                        if count > 0:
                                gc_dist = distance(first_lat, first_lng, last_lat, last_lng)
                                file.write(str(last_fid) + ',' + (str(airline))[:3]+ ',' + str(airline) + ','+ str(acft) + ','+str(alt_sum/count) + ',' + str(speed_sum/count) + ',' + str(dept)+ ',' + str(dept_date)+ ',' + str(dept_time)+ ',' + str(arr)+ ',' + str(arr_date) + ',' + str(arr_time) + ','+str(act_dist)+','+str(gc_dist)+',\n')
                        last_fid = row[0]
                        alt_sum = row[1]
                        speed_sum = row[2]
                        dept = row[3]
                        dept_date = row[4]
                        dept_time = row[5]
                        arr = row[6]
                        arr_date = row[7]
                        arr_time = row[8]
                        acft = row[9]
                        airline = row[10]
                        count = 1
                        first_lat = row[11]
                        first_lng = row[12]
                        lat = row[11]
                        lng = row[12]
                        act_dist = 0
                else:
                        count += 1
                        alt_sum += row[1]
                        speed_sum += row[2]
                        prv_lat = lat
                        prv_lng = lng
                        lat = row[11]
                        lng = row[12]
                        last_lat = row[11]
                        last_lng = row[12]
                        act_dist += distance(prv_lat, prv_lng, lat, lng)
        gc_dist = distance(first_lat, first_lng, last_lat, last_lng)
        file.write(str(last_fid) + ',' + (str(airline))[:3]+ ',' + str(airline) + ','+ str(acft) + ','+str(alt_sum/count) + ',' + str(speed_sum/count) + ',' + str(dept)+ ',' + str(dept_date)+ ',' + str(dept_time)+ ',' + str(arr)+ ',' + str(arr_date) + ',' + str(arr_time) + ','+ str(act_dist)+','+str(gc_dist)+',\n')
        
        file.close()
        
def append_csv(file_name, results_cursor):
        csvfile = open(file_name, "a")
        for row in results_cursor:
                for column in row:
                        csvfile.write(str(column) + ",")
                csvfile.write("\n")
        csvfile.close()
        print ("Append to CSV file %s" % file_name)
        
        
def iterateQuery(ws):
        global queryIteration
        
        LLData = pquery.read_json(pquery.LLData['points_file'][:-8])
        LLData['is_iterated'] = 1
        pquery.dump_json(LLData['points_file'][:-8], LLData)
        
        file_name = pquery.LLData['points_file'][:-4:]+ str(queryIteration) + '.csv'
        
        
        totalIterations = pquery.SAMPLING_LIMIT / pquery.LLData['points_per_iteration']
        #db = psycopg2.connect(host="", database="netjets", user="tornado", password="spacetime")
        #db = psycopg2.connect(host="", database="spacetime", user="remote", password="remote")
        db = psycopg2.connect(host="spacetime-1.cluster-cuom8obdn6vl.us-east-2.rds.amazonaws.com", database="spacetime", user="root", password="WL7KZZG0JN")
        c = db.cursor()

        print ('iterative query', queryIteration, 'out of',  totalIterations)
        if queryIteration < totalIterations:
                offset = queryIteration * pquery.LLData['fcount'] / totalIterations
                itQuery = pquery.LLData['query'] + pquery.LLData['inner_query'] + " OFFSET " + str(offset) + ');'
                
                print (itQuery)
                c.execute(itQuery)
                c2 = []
                wanted_indices = [0,1,2,4,5,7,8]
                for row in c:
                        wanted_data = [row[i] for i in wanted_indices]
                        if not wanted_data in c2: #avoid duplicates when creating MPV
                                c2.append(wanted_data)
                c2.sort(); #sorts by flight id
                ## What is scroll function?
                c.scroll(0, 'absolute')
                
                append_csv(file_name=pquery.LLData['points_file'], results_cursor=c)
                c.scroll(0, 'absolute')
                generate_csv(file_name, "flight_id,dept_aprt,dept_date_utc,dept_time_utc,arr_aprt,arr_date_utc,arr_time_utc,icao,acft_type,point_time,lat,lng,alt,ground,hash,", c)
                append_csv(file_name=pquery.LLData['points_file'][0:-8] + '/flight_list.csv', results_cursor=c2)
                
                queryIteration += 1
                ws.write_message(file_name);
        else:
                queryIteration = 1
                ws.close()
        db.close()

def distance_revise(lat1, lng1, lat2, lng2):
    dept_lat_rad = math.radians(lat1)
    dept_lng_rad = math.radians(lng1)
    arr_lat_rad = math.radians(lat2)
    arr_lng_rad = math.radians(lng2)
    earth_radius = 3440
    temp = math.cos(dept_lat_rad)*math.cos(dept_lng_rad)*math.cos(arr_lat_rad)*math.cos(arr_lng_rad) + math.cos(dept_lat_rad)*math.sin(dept_lng_rad)*math.cos(arr_lat_rad)*math.sin(arr_lng_rad) + math.sin(dept_lat_rad)*math.sin(arr_lat_rad)
    if(temp >=-1 and temp <= 1):
        d = math.acos(temp) * earth_radius
    else:
        d = 0
    result = int(round(d))
    return result

def flight_distance(flight_array1,flight_array2):
    totalDistance = 0
    length = len(flight_array1)
    i = 0
    while i < length:
        pointDistance = distance_revise(flight_array1[i],flight_array1[i+1],flight_array2[i],flight_array2[i+1])
        totalDistance = totalDistance + pointDistance
        i = i+2
    length = length/2
    return totalDistance/length

def cos_sim(a, b):
        cos_sim = dot(a, b) / (norm(a) * norm(b))
        return cos_sim

def flight_distance2(flight_array1,flight_array2):
    totalDistance = 0
    length = len(flight_array1)
    i = 0
    count = 0
    while i < length-3:
        vector1 = [(flight_array1[i+2] - flight_array1[i]), (flight_array1[i+3] - flight_array1[i+1])]
        vector2 = [(flight_array2[i+2] - flight_array2[i]), (flight_array2[i+3] - flight_array2[i+1])]
        pointDistance = cos_sim(vector1, vector2)
        if pointDistance<1 and pointDistance >-1:
                pointDistance = 1 - pointDistance
                totalDistance = totalDistance + pointDistance
                count = count + 1
        i = i+2
    return totalDistance/count

def get_standard_distance_matrix():
        df = pd.read_csv('cluster/data.csv')
        df = df[df.columns[0:-4]]
        df['point_time'] = pd.to_datetime(df['point_time'],format= '%H:%M:%S' )
        flightCountList = df.groupby(['flight_id']).size()#.reset_index(name='size')
        flightPointSelect = dict()
        #print(flightCountList.min())
        num_points = int(flightCountList.min())
        print(num_points)
        for fid, count in flightCountList.items():
                interval = count / num_points
                latLngList = list()
                flightExtract = df[df['flight_id']==fid]
                if(flightExtract['dept_date_utc'].values[0]!=flightExtract['arr_date_utc'].values[0]):
                        flightExtract['point_time']=flightExtract['point_time'].apply(lambda x: x+timedelta(hours=24) if x.time().hour<12 else x)
                flightExtract=flightExtract.sort_values(by=['point_time'])
                index = interval/2
                for i in range(num_points):
                        info = (flightExtract.iloc[int(index)]['lat'],flightExtract.iloc[int(index)]['lng'])
                        latLngList.append(info)
                        index = index + interval
                flightPointSelect[fid] = latLngList
        keys = np.array(list(flightPointSelect.keys()))
        values = np.array(list(flightPointSelect.values()))
        values=values.reshape(values.shape[0],values.shape[1]*values.shape[2])
        return values

def clustering(manual_threshold,ws,option,num_points,metric):
        origin_values = get_standard_distance_matrix()
        start_time = time.time()
        df = pd.read_csv('cluster/data.csv')
        df = df[df.columns[0:-4]]
        df['point_time'] = pd.to_datetime(df['point_time'],format= '%H:%M:%S' )
        flightCountList = df.groupby(['flight_id']).size()#.reset_index(name='size')
        flightPointSelect = dict()
        #print(flightCountList.min())
        num_points = int(flightCountList.min())/num_points
        num_points = int(num_points)
        if(num_points<4):
                num_points = 4
        for fid, count in flightCountList.items():
                interval = count / num_points
                latLngList = list()
                flightExtract = df[df['flight_id']==fid]
                if(flightExtract['dept_date_utc'].values[0]!=flightExtract['arr_date_utc'].values[0]):
                        flightExtract['point_time']=flightExtract['point_time'].apply(lambda x: x+timedelta(hours=24) if x.time().hour<12 else x)
                flightExtract=flightExtract.sort_values(by=['point_time'])
                index = interval/2
                for i in range(num_points):
                        info = (flightExtract.iloc[int(index)]['lat'],flightExtract.iloc[int(index)]['lng'])
                        latLngList.append(info)
                        index = index + interval
                flightPointSelect[fid] = latLngList     
        keys = np.array(list(flightPointSelect.keys()))
        values = np.array(list(flightPointSelect.values()))
        values=values.reshape(values.shape[0],values.shape[1]*values.shape[2])
        if(option==1):
                if(metric == 1):
                        original_dist_mat = pdist(origin_values, metric=flight_distance)
                        sqr_dist_mat = squareform(original_dist_mat)
                        start_time = time.time()
                        dist_mat = pdist(values, metric=flight_distance)
                        sqr_dist_mat = squareform(dist_mat)
                        linkages = linkage(dist_mat, method="average")
                # thresholds = [25, 50, 75, 100, 125, 150]
                        thresholds = [2, 3, 4, 5, 6, 7]
                        best_threshold = 0
                        best_score = -1
                        for threshold in thresholds:
                                result = fcluster(linkages, t=threshold, criterion = "maxclust")
                                if len(Counter(result).keys()) == 1:
                                        continue
                                performance = silhouette_score(sqr_dist_mat, result, metric="precomputed")
                                if performance > best_score:
                                        best_score = performance
                                        best_threshold = threshold
                                print("\nthreshold: " + str(threshold))
                                print("\nscore: " + str(performance))
                        result = fcluster(linkages, t=best_threshold, criterion="maxclust")
                        print("\nbest threshold: " + str(best_threshold))
                        print("\nbest score: " + str(best_score))
                        end_time = time.time()
                        runningtime = end_time - start_time
                        print("running time: " + str(runningtime))
                else:
                        best_threshold = manual_threshold
        else:
                # result = fclusterdata(values, t=threshold,metric =flight_distance2, criterion = "distance",method="average")
                # origin_values = get_standard_distance_matrix()
                        if(metric == 1):
                                original_dist_mat = pdist(origin_values, metric=flight_distance2)
                                sqr_dist_mat = squareform(original_dist_mat)
                                start_time = time.time()
                                dist_mat = pdist(values, metric=flight_distance2)
                                sqr_dist_mat = squareform(dist_mat)
                                linkages = linkage(dist_mat, method="average")
                # thresholds = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4]
                                thresholds = [2, 3, 4, 5, 6, 7]
                                best_threshold = 0
                                best_score = -1
                                for threshold in thresholds:
                                        result = fcluster(linkages, t=threshold, criterion = "maxclust")
                                        if len(Counter(result).keys()) == 1:
                                                continue
                                        performance = silhouette_score(sqr_dist_mat, result, metric="precomputed")
                                        if performance > best_score:
                                                best_score = performance
                                                best_threshold = threshold
                                        print("\nthreshold: " + str(threshold))
                                        print("\nscore: " + str(performance))
                                result = fcluster(linkages, t=best_threshold, criterion="maxclust")
                                print("\nbest threshold: " + str(best_threshold))
                                print("\nbest score: " + str(best_score))
                                end_time = time.time()
                                runningtime = end_time - start_time
                                print("running time: " + str(runningtime))
                        else:
                                best_threshold = manual_threshold
        result = fclusterdata(values, t=best_threshold,metric =flight_distance2, criterion = "distance",method="average")
        origin_values = get_standard_distance_matrix()
        flight_id_cluster = pd.DataFrame({'flight_id':keys, 'cluster':result})
        flight_id_cluster.to_csv('static/multipointviz/result.csv', sep=',')
        ws.write_message("Clustering Complete")
        


                
application = tornado.web.Application([
        (r"(?i)/", MainHandler),
        (r"(?i)", MainHandler),
        (r"(?i)/single", SingleHandler),
        (r"(?i)/multi", MultiHandler),
        (r'(?i)/websocket', WebSocketHandler),
        (r'(?i)/static/(.*)', tornado.web.StaticFileHandler, {'path': settings["static_path"]}),
], **settings)

if __name__ == "__main__":
        if os.name == 'nt':
                import asyncio
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        port = 8888
        if len(sys.argv) > 1:
                print ("Alternate port specifed: %s" % sys.argv[1])
                port = sys.argv[1]

        application.listen(port)
        print ("Server running on port %s ..." % port)
        tornado.ioloop.IOLoop.instance().start()

        

