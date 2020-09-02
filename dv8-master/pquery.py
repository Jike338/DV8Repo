import sys
import csv
import json
import psycopg2
import datetime
import time
from psycopg2.extras import RealDictCursor
import math
from crawl import get_weather_report, translate_metar
import json
import os

# -- Configuration --
SAMPLING_LIMIT = 40000 # ( in number of records )
QUERY_TIMEOUT = 100000 # ( in milliseconds )
FID_MULTIPLIER = 1000
MAX_HASH = 200
POINTS_TABLE = 'all_points_hash' #'ram_points_hash'
FLIGHTS_TABLE = 'all_dflights'
COUNTS_TABLE = 'all_counts'

DEMO_POINTS = 'demo_points_hash'
DEMO_FLIGHTS = 'demo_dflights'
DEMO_COUNTS = 'demo_counts'

# -------------------
#- For Lazy Loading -
LLData = {
'fcount': 0,
'points_per_iteration': 0,
'flights_per_iteration': 0,
'sampling_rate': 1,
'query': 'default',
'inner_query': 'default',
'points_file': 'default',
'is_iterated': 0 #0 = false, 1 = true
}
#--------------------

### EVERY MILLISECOND COUNTS

def dump_json(cache_folder, json_map = None):
        global LLData
        if json_map:
                LLData = json_map
                
        with open(cache_folder + '/json_data.txt', 'w') as out:
                json.dump(LLData, out)
        #os.chmod(cache_folder + '/json_data.txt', 0o777)
                
def read_json(cache_folder):
        global LLData
        try:
                with open(cache_folder + '/json_data.txt', 'r') as fin:
                        LLData = json.load(fin)
        except IOError:
                print ("Cache not complete, refetching data")
                return None
        return LLData
        

def generate_csv(file_name, header, results_cursor):
        csvfile = open(file_name, "w")
        csvfile.write(header + "\n")
        for row in results_cursor:
                for column in row:
                        csvfile.write(str(column) + ",")
                csvfile.write("\n")
        csvfile.close()
        #os.chmod(file_name, 0o777)
        print ("Generated CSV file %s." % file_name)
        
        
def grab_from_fid_list(fid_list_str, using_demo = False):
                
        if using_demo:
                local_points = DEMO_POINTS
                local_flights = DEMO_FLIGHTS
                local_counts = DEMO_COUNTS
        else:
                local_points = POINTS_TABLE
                local_flights = FLIGHTS_TABLE
                local_counts = COUNTS_TABLE

        #db = psycopg2.connect(host="", database="spacetime", user="remote", password="remote")
        db = psycopg2.connect(host="spacetime-1.cluster-cuom8obdn6vl.us-east-2.rds.amazonaws.com", database="spacetime", user="root", password="WL7KZZG0JN")
        c = db.cursor()
        
        q = "SELECT flight_id, alt, ground, dept_aprt, dept_date_utc, dept_time_utc, arr_aprt, arr_date_utc, arr_time_utc, acft_type, icao, lat, lng FROM " + local_flights + " natural join " + local_points + " WHERE flight_id in (" + fid_list_str + ")"
        
        c.execute(q)
        return c
        
        
def given_where(where_cond, using_demo=True):

        if using_demo:
                local_points = DEMO_POINTS
        else:
                local_points = POINTS_TABLE

        #db = psycopg2.connect(host="", database="spacetime", user="remote", password="remote")
        db = psycopg2.connect(host="spacetime-1.cluster-cuom8obdn6vl.us-east-2.rds.amazonaws.com", database="spacetime", user="root", password="WL7KZZG0JN")
        c = db.cursor()
        
        q = 'SELECT D.flight_id, dept_aprt, dept_date_utc, dept_time_utc, arr_aprt, arr_date_utc, arr_time_utc, D.icao, D.acft_type, point_time, lat,lng,alt, ground, hash FROM ' + FLIGHTS_TABLE + ' D, ' + \
                local_points + where_cond + ' AND D.flight_id = ' + local_points +'.flight_id'
        print ('\n',q[0:500],'\n')
        
        c.execute(q)
        return c
        

def get_weather_data(fid, crawl_data):
        #db = psycopg2.connect(host="", database="netjets", user="tornado", password="spacetime")
        #db = psycopg2.connect(host="", database="spacetime", user="remote", password="remote")
        db = psycopg2.connect(host="spacetime-1.cluster-cuom8obdn6vl.us-east-2.rds.amazonaws.com", database="spacetime", user="root", password="WL7KZZG0JN")
        c = db.cursor()
        
        q = "SELECT arr, dept FROM weather WHERE flight_id=" + fid
        c.execute(q)
        results = c.fetchone()
        
        if not results:
                metar_dept = get_weather_report(crawl_data[0],crawl_data[1],crawl_data[2])
                metar_arr = get_weather_report(crawl_data[3],crawl_data[4],crawl_data[5])
                dept_message = ', '.join(translate_metar(metar_dept))
                arr_message = ', '.join(translate_metar(metar_arr))
                
                q = "INSERT INTO weather VALUES (%s, %s, %s)"
                args = (long(fid), dept_message, arr_message)
                c.execute(q, args)
                db.commit()
                
                print ("NEW DATA INSTERTED IN weather")
                results = (dept_message, arr_message)
                
        db.close()
        return results
                

def points(flight_id="", dept_aprts=[], arr_aprts=[], from_dates=[], to_dates=[], airline="", aircraft="", file_name="", single="", using_demo=True, dept_nearby=False, arr_nearby=False, geo=False):

        # Open database connection
        # For JSON: #, cursor_factory=RealDictCursor)
        
        if using_demo:
                local_points = DEMO_POINTS
                local_flights = DEMO_FLIGHTS
                local_counts = DEMO_COUNTS
        else:
                local_points = POINTS_TABLE
                local_flights = FLIGHTS_TABLE
                local_counts = COUNTS_TABLE
        
        global LLData
        global MAX_HASH
        
        print ("IN POINTS")
        #db = psycopg2.connect(host="", database="netjets", user="tornado", password="spacetime")
        #db = psycopg2.connect(host="", database="spacetime", user="remote", password="remote")
        db = psycopg2.connect(host="spacetime-1.cluster-cuom8obdn6vl.us-east-2.rds.amazonaws.com", database="spacetime", user="root", password="WL7KZZG0JN")
        c = db.cursor()
        
        timeout_query = "SET statement_timeout = %s" % QUERY_TIMEOUT
        c.execute(timeout_query)

        dflightsRef = local_flights
        inner_query = None
        inner_query_select = 'SELECT flight_id FROM ' + local_flights
        inner_query_where = ''
        multi_flight_query_select = ''
        multi_flight_query_where = ''
        
        query = 'MULT POINT VIZ QUERY       '
        
        if single: #Single flight viz
                query = "SELECT flight_id, point_time, lat,lng,alt,ground FROM " + local_points
        elif not geo: #Multi Point Viz
                multi_flight_query_select = "SELECT D.flight_id, dept_aprt, dept_date_utc, dept_time_utc, arr_aprt, arr_date_utc, arr_time_utc, D.icao, D.acft_type, point_time, lat,lng,alt, ground, D.hash FROM " + local_points 
                countQ = "SELECT COUNT(*), SUM(count) FROM " + local_counts + " "
        else: #Multi Flight Geo Viz
                dflightsRef = 't0'
                query = "SELECT flight_id,dept_aprt,dept_date_utc,dept_time_utc,arr_aprt,arr_date_utc,arr_time_utc,t0.icao,t1.lat as dept_lat,t1.lng as dept_lng,t2.lat as arr_lat,t2.lng as arr_lng FROM " + local_flights + " t0, airports t1, airports t2 where t0.dept_aprt = t1.iata and t0.arr_aprt = t2.iata"
                flights_query = "SELECT flight_id, dept_aprt, dept_date_utc, arr_aprt, arr_date_utc, icao FROM " + local_flights
                
        # Validate form input
        if not single:
                #Check for enough input
                if len(flight_id)==0 and len(airline)==0 and len(aircraft)==0:
                        if len(dept_aprts) == 0 and len(arr_aprts) == 0:        return "Neither airport specified."
                        if len(from_dates) == 0:        return "Begin date not completely specified."
                        if len(to_dates) == 0:  return "End date not completely specified."
                        

        # Filter on airport / direction, time of day, date range
        where_conditions = []
        data_map = {}

        #filter flight id
        if len(flight_id) > 0:
                # ifid = int(flight_id)
                # all_hashes = [str(ifid*FID_MULTIPLIER + x) for x in range(MAX_HASH)]
                # where_conditions.append(" " + local_points + ".hash IN (" + ','.join(all_hashes) + ')')
                where_conditions.append("flight_id="+flight_id)
                
        #filter date ranges
        if len(to_dates) > 0 and len(to_dates) == len(from_dates):
                from_dates.sort()
                to_dates.sort()
                date_conds = []
                for i, d in enumerate(from_dates):
                        #from_date_dt = datetime.datetime.strptime(from_dates[i], "%m/%d/%Y")
                        #to_date_dt = datetime.datetime.strptime(to_dates[i], "%m/%d/%Y")
                        #if from_date_dt and to_date_dt and to_date_dt < from_date_dt:
                        #       return "Arrival date is before departure date."
                        
                        if from_dates[i] > to_dates[i]:
                                return "Arrival date is before departure date"
                        
                        date_conds.append("( dept_date_utc >= %(from_date" + str(i) + ")s AND dept_date_utc <= %(to_date" + str(i) + ")s )")
                        data_map["from_date" + str(i)] = from_dates[i]
                        data_map["to_date" + str(i)] = to_dates[i]
                where_conditions.append('(' + ' OR '.join(date_conds) + ')')
                print(data_map)
                
        #filter departing airport
        if len(dept_aprts) > 0:
                dept_aprts_cond = " (dept_aprt = %(dept_aprts0)s"
                data_map["dept_aprts0"] = dept_aprts[0]
                for i, d_a in enumerate(dept_aprts[1:]):
                        dept_aprts_cond += " OR dept_aprt = %(dept_aprts" + str(i+1) + ")s"
                        data_map["dept_aprts" + str(i+1)] = d_a
                dept_aprts_cond += ")"
                where_conditions.append(dept_aprts_cond)

        #filter arriving airport
        if len(arr_aprts) > 0:
                arr_aprts_cond = " (arr_aprt = %(arr_aprts0)s"
                data_map["arr_aprts0"] = arr_aprts[0]
                for i, a_a in enumerate(arr_aprts[1:]):
                        arr_aprts_cond += " OR arr_aprt = %(arr_aprts" + str(i+1) +")s"
                        data_map["arr_aprts" + str(i+1)] = a_a
                arr_aprts_cond += ")"
                where_conditions.append(arr_aprts_cond)
                
                
        #filter airline
        
        if len(airline) > 0:
                if '%' in airline or '_' in airline:
                        where_conditions.append(dflightsRef + ".icao like %(icao)s ")
                else:
                        where_conditions.append(dflightsRef + ".icao = %(icao)s ")
                data_map["icao"] = airline
                        
        #Filter aircraft type

        if len(aircraft) > 0:
                if '%' in aircraft or '_' in aircraft:
                        where_conditions.append(" " + local_flights + ".acft_type like %(acft_type)s ")
                else:
                        where_conditions.append(" " + local_flights + ".acft_type = %(acft_type)s ")
                data_map["acft_type"] = aircraft
                        
                        
        #apply filters
        if len(where_conditions) > 0:
                if not geo: #USES INNER_QUERY
                        inner_query_where += " WHERE " + where_conditions[0]
                        for where_condition in where_conditions[1:]:
                                inner_query_where += " AND " + where_condition
                        #TEMP - This is added on because not all points are in the database
                        #inner_query_where += " AND ((flight_id>20120300000000 AND flight_id<20120600000000) OR (flight_id>20130300000000 AND flight_id<20130600000000) OR (flight_id>20140300000000 AND flight_id<20140600000000))"
                else: #DOESNT USE INNER_QUERY
                        query += " AND " + where_conditions[0]
                        flights_query += " WHERE " + where_conditions[0]
                        for where_condition in where_conditions[1:]:
                                query += " AND " + where_condition
                                flights_query += " AND " + where_condition
                        
        
        if single:              #singleflightviz
                # Order individual flight by point_time
                query += " WHERE " + where_conditions[0] #+ " ORDER BY point_time "
        elif not geo:   #multi point viz
                LLData['points_file'] = file_name
                
                try:

#------------------- Get dflight Count Info ----------------------------------#
                        count_inner_query = inner_query_select + inner_query_where
                        countQ += 'WHERE flight_id in (' + count_inner_query + ');'
                        print ("GETTING COUNT: ", countQ, '\n')
                        c.execute(countQ, data_map)
                        fcount_pcount = c.fetchone()
                        if fcount_pcount[0] == 0:
                                return "NO RESULTS"
                        fcount = float(fcount_pcount[0]);
                        pcount = float(fcount_pcount[1]);
                        print ("POINT COUNT: ", pcount, '\nFLIGHT COUNT: ', fcount, '\n')
                        
                        #--- Lots of math start ------------------------------------------#
                        points_per_flight = pcount/fcount
                        
                        #at least 8 points per flight
                        min_ppf = 4.0
                        hash_ranges_per_flight = points_per_flight / MAX_HASH
                        print (hash_ranges_per_flight)
                        max_hash_increment = MAX_HASH * hash_ranges_per_flight / min_ppf
                        flight_limit = SAMPLING_LIMIT*MAX_HASH / (min_ppf * points_per_flight)
                        
                        hash_increment = min(max_hash_increment, pcount/SAMPLING_LIMIT)
                        hash_increment = max(hash_increment, 1)
                        print ("HASH INCREMENT: ", max_hash_increment, pcount/SAMPLING_LIMIT, hash_increment)
                        
                        len_hashes = int(MAX_HASH / hash_increment)
                        hashes = []
                        for i in range(0, len_hashes):
                                hashes.append('(' + str(int(i*MAX_HASH/len_hashes)) + ')')
                        print ("HASHES: ", hashes, '\n')
                        
                        sampled_ppf = len(hashes) * hash_ranges_per_flight
                        
                        inner_query_select = 'SELECT flight_id, dept_aprt, dept_date_utc, dept_time_utc, arr_aprt, arr_date_utc, arr_time_utc, icao, acft_type, flight_id*' \
                                + str(FID_MULTIPLIER) + '+hash_value AS hash FROM ' + local_flights + ', (VALUES ' + ', '.join(hashes) + ') hashes(hash_value) '
                        #the 1.5 grabs probably too many points, but that's better than too few. This is a compromise between time and exact visualization
                        inner_query_where += ' limit ' + str(SAMPLING_LIMIT / hash_ranges_per_flight) 
                        inner_query = inner_query_select + inner_query_where
                        
                        
                        LLData['fcount'] = fcount
                        LLData['points_per_iteration'] = 500
                        LLData['flights_per_iteration'] = 40
                        LLData['sampling_rate'] = 1#deleted - samplingRate
                        #-- Lots of math end ----------------------------------------------#
                        
                except psycopg2.extensions.QueryCanceledError as e:
                        print ("myERROR: " + str(e))
#--------------------End Get Dflight Count Info ------------------------------#
                #inner_query += ' LIMIT ' + str(flight_limit)
                LLData['inner_query'] = inner_query
                
                multi_flight_query_select += ', \n(' + inner_query + ') D\n'
                #this limit corrects any extra from the over-estimate in the inner query 
                multi_flight_query_where += " WHERE " + local_points + ".hash = D.hash limit " + str(SAMPLING_LIMIT)
                multi_flight_query = multi_flight_query_select + multi_flight_query_where
                
                #old method: query += " AND random() <= " + str(samplingRate)   
                
                
        if geo:                 #multiflightgeoviz
                query += "ORDER BY flight_id"
                flights_query += "ORDER BY dept_date_utc;"

        
        LLData['query'] = query
        
        try:
                if not single and not geo: #MULTI POINTS VIZ
                        final_query = multi_flight_query + ';'
                else: #SINGLE FLIGHT VIZ or that other one
                        final_query = query + ';'
                print ("Executing '%s'" % final_query)
                c.execute(final_query, data_map)
                if c.rowcount == 0:             
                        print ("No Results" )
                        return "No Results."
                
                if not single: #creates the flight_list for the single flight viz
                        c2 = []
                        wanted_indices = [0,1,2,4,5,7,8]
                        for row in c:
                                wanted_data = [row[i] for i in wanted_indices]
                                if geo or not wanted_data in c2: #avoid duplicates when creating MPV
                                        c2.append(wanted_data)
                        if not geo:
                                c2.sort(); #sorts by flight id
                        c.scroll(0, 'absolute')
        except psycopg2.extensions.QueryCanceledError as e:
                # Handle QueryCanceledError
                print ("TIMEOUT")
                return "Search timed out."


        print ("Query complete: %d results." % c.rowcount)
                        
        if single:
                generate_csv(file_name=file_name, header="flight_id,point_time,lat,lng,alt,ground", results_cursor=c)
        elif not geo: #Create Cache Files               
                generate_csv(file_name=file_name, header="flight_id,dept_aprt,dept_date_utc,dept_time_utc,arr_aprt,arr_date_utc,arr_time_utc,icao,acft_type,point_time,lat,lng,alt,ground,hash,", 
                        results_cursor=c)
                generate_csv(file_name=file_name[0:-8] + 'flight_list.csv', header="flight_id,dept_aprt,dept_date_utc,arr_aprt,arr_date_utc,icao,acft_type,", 
                        results_cursor=c2)
                        
                LLData['is_iterated'] = 0
                dump_json(file_name[0:-8], LLData)
        else:    
                generate_csv(file_name=file_name, header="flight_id,dept_aprt,dept_date_utc,dept_time_utc,arr_aprt,arr_date_utc,arr_time_utc,icao,dept_lat,dept_lng,arr_lat,arr_lng,", 
                        results_cursor=c)
                generate_csv(file_name="static/singleflightviz/flight_list.csv", header="flight_id,dept_aprt,dept_date_utc,arr_aprt,arr_date_utc,icao,", 
                        results_cursor=c2)




        db.close()
        print ('\n\n\n\n\n\n')

def flights(flight_id="", dept_aprts=[], arr_aprts=[], from_date="", to_date="", airline="", aircraft="", file_name="", single="", dept_nearby=False, arr_nearby=False):
        # Open database connection
        # For JSON: #, cursor_factory=RealDictCursor)
        print ("IN FLIGHTS")
        #db = psycopg2.connect(host="", database="netjets", user="tornado", password="spacetime")
        #db = psycopg2.connect(host="", database="spacetime", user="remote", password="remote")
        db = psycopg2.connect(host="spacetime-1.cluster-cuom8obdn6vl.us-east-2.rds.amazonaws.com", database="spacetime", user="root", password="WL7KZZG0JN")
        c = db.cursor()
        
        timeout_query = "SET statement_timeout = %s" % QUERY_TIMEOUT
        c.execute(timeout_query)

        query = "SELECT flight_id,dept_aprt,dept_date_utc,dept_time_utc,arr_aprt,arr_date_utc,arr_time_utc,icao,acft_type FROM " + FLIGHTS_TABLE

        if not single and len(flight_id)==0:
                if len(dept_aprts) == 0 and len(arr_aprts) == 0:        return "Neither airport specified."
                if len(from_date) == 0: return "Begin date not completely specified."
                if len(to_date) == 0:   return "End date not completely specified."

                from_date_dt = datetime.datetime.strptime(from_date, "%m/%d/%Y")
                to_date_dt = datetime.datetime.strptime(to_date, "%m/%d/%Y")
                if to_date_dt < from_date_dt:
                        return "Arrival date is before departure date."

        # Filter on airport / direction, time of day, date range
        where_conditions = []
        if len(dept_aprts) > 0:
                if dept_nearby:
                        aprt_query = "SELECT lat,lng from airports where iata = '%s';" % dept_aprts[0]
                        c.execute(aprt_query)
                        aprt_lat, aprt_lng = c.fetchone()

                        top5_query = "SELECT iata FROM airports WHERE (lat BETWEEN %s-1 AND %s+1) and (lng BETWEEN %s-1 AND %s+1) and iata <> '%s' order by abs(lat - %s)*abs(lng - %s) limit 5;" % (aprt_lat, aprt_lat, aprt_lng, aprt_lng, dept_aprts[0], aprt_lat, aprt_lng)
                        c.execute(top5_query)

                        top5 = str([x[0] for x in c.fetchall()])[1:-1]

                        where_conditions.append(" dept_aprt in (%s) " % top5)
                        print (where_conditions)
                else:
                        dept_aprts_cond = " (dept_aprt = '" + dept_aprts[0] +"'"
                        for d_a in dept_aprts[1:]:
                                dept_aprts_cond += " OR dept_aprt = '" + d_a +"'"
                        dept_aprts_cond += ")"
                        where_conditions.append(dept_aprts_cond)

        if len(arr_aprts) > 0:
                if arr_nearby:
                        aprt_query = "SELECT lat,lng from airports where iata = '%s';" % arr_aprts[0]
                        c.execute(aprt_query)
                        aprt_lat, aprt_lng = c.fetchone()

                        top5_query = "SELECT iata FROM airports WHERE (lat BETWEEN %s-1 AND %s+1) and (lng BETWEEN %s-1 AND %s+1) and iata <> '%s' order by abs(lat - %s)*abs(lng - %s) limit 5;" % (aprt_lat, aprt_lat, aprt_lng, aprt_lng, arr_aprts[0], aprt_lat, aprt_lng)
                        c.execute(top5_query)

                        top5 = str([x[0] for x in c.fetchall()])[1:-1]

                        where_conditions.append(" arr_aprt in (%s) " % top5)
                        print (where_conditions)
                else:
                        arr_aprts_cond = " (arr_aprt = '" + arr_aprts[0] +"'"
                        for a_a in arr_aprts[1:]:
                                arr_aprts_cond += " OR arr_aprt = '" + a_a +"'"
                        arr_aprts_cond += ")"
                        where_conditions.append(arr_aprts_cond)

        if len(flight_id) > 0:          where_conditions.append(" flight_id = " + flight_id)
        if len(from_date) > 0:
                where_conditions.append(" dept_date_utc >= %s " % (from_date_dt.strftime("%Y%m%d")))
                print ("\n\n\n[%s]\n\n\n" % from_date_dt.strftime("%Y%m%d"))
        if len(to_date) > 0:            
                where_conditions.append(" dept_date_utc <= %s " % (to_date_dt.strftime("%Y%m%d")))
                print ("\n\n\n[%s]\n\n\n" % to_date_dt.strftime("%Y%m%d"))
        if len(airline) > 0:
                if '%' in airline or '_' in airline:
                        where_conditions.append(" " + FLIGHTS_TABLE + ".icao like '%s' " % airline)
                else:
                        where_conditions.append(" " + FLIGHTS_TABLE + ".icao = '%s' " % airline)
        if len(aircraft) > 0:
                if '%' in aircraft or '_' in aircraft:
                        where_conditions.append(" " + FLIGHTS_TABLE + ".acft_type like '%s' " % aircraft)
                else:
                        where_conditions.append(" " + FLIGHTS_TABLE + ".acft_type = '%s' " % aircraft)
                
        if len(where_conditions) > 0:
                query += " WHERE " + where_conditions[0]
                for where_condition in where_conditions[1:]:
                        query += " AND "
                        query += where_condition

        if single:
                # Order individual flight by point_time
                query += " ORDER BY point_time "
        else:
                # Randomly sample results
                #query += " ORDER BY random() LIMIT %s " % SAMPLING_LIMIT       
                query += " ORDER BY flight_id"

        print ("Executing '%s'..." % query)
        try:
                c.execute(query)
        except psycopg2.extensions.QueryCanceledError as e:
                # Handle QueryCanceledError
                return "Search timed out."


        print ("Query complete: %d results." % c.rowcount)
        if c.rowcount == 0:             return "No results."

        c2 = []
        wanted_indices = [0,1,2,4,5,7,8]
        for row in c:
                wanted_data = [row[i] for i in wanted_indices]
                c2.append(wanted_data)
        c.scroll(0, 'absolute')
        
        generate_csv(file_name=file_name, header="flight_id,dept_aprt,dept_date_utc,dept_time_utc,arr_aprt,arr_date_utc,arr_time_utc,icao,dept_aprt_lat,dept_aprt_lng,arr_aprt_lat,arr_aprt_lng,", 
                results_cursor=c)
                
        generate_csv(file_name="static/singleflightviz/flight_list.csv", header="flight_id,dept_aprt,dept_date_utc,arr_aprt,arr_date_utc,icao,acft_type,", 
                        results_cursor=c2)

        db.close()
        print ('\n\n\n\n\n\n')
