import os
from os import listdir
from os.path import isfile, join
import shutil
import datetime
from datetime import date
from itertools import islice
import pquery

# Configuration settings
cache_folder = "static/cache/"
cache_capacity = 20

def normalize_param(param):
	"""
	Replaces unfilled attributes with "A" in the CSV name
	"""

	out = param.replace("%","")
	if out == "":
		return "A"
	else:
		return out


def correct_airports(param):
	"""
	In case of multiple airports, this function removes "," as it is
	unacceptable in file name
	"""
	out = param.replace(",","")
	return out


def get_dir_name(params):
	"""
	Builds the folder name based on query parameters
	"""
	dir_name = normalize_param(params["L"])+"-"+normalize_param(params["C"])+"-"+normalize_param(params["P1"])+"-"+normalize_param(params["P2"])+"-"+normalize_param(params["T1"])+"-"+normalize_param(params["T2"])
	return dir_name


def is_in_cache(params):
	"""
	Verifies if a folder corresponding to the query exists in cache
	"""
	dir_name = get_dir_name(params)
	full_address = cache_folder + dir_name
	return os.path.isdir(full_address)


def incremental_cache_check(params):
	"""
	Check if cache was hit by a query
	"""
	in_name = get_dir_name(params)
	in_name_params = in_name.split('-')
	flights_copied = False

	# For each folder in the cache
	folders = [f for f in listdir(cache_folder)]
	for folder in folders:
		fparams = folder.split('-')

		if in_name_params[0:4] == fparams[0:4]:
			#[year, month, day]
			fd_date = fparams[4]
			fa_date = fparams[5]

			if fd_date < params['T1'] or fa_date > params['T2']:
				if incremental_cache(folder, params):
					print('INCREMENTAL CACHE HIT')

					return True

	return False


def incremental_cache(folder, params):
	"""
	Copy flights and points to a new output folder
	"""

	flights_copied = False
	d_date = params['T1']
	a_date = params['T2']

	# create new cache dir
	out_dir = get_dir_name(params)
	create_dir(cache_folder + out_dir)

	# copy flight list first
	fl = open(cache_folder + folder + '/flight_list.csv', 'r')
	fl_out = open(cache_folder + out_dir + '/flight_list.csv', 'w')
	fl_out.write(fl.readline())
	for line in fl:
		date = line[0:8] # line[0:8] = fid of the line
		if date > d_date and date < a_date:
			fl_out.write(line)
			flights_copied = True
	fl.close()
	fl_out.close()
	# os.chmod(cache_folder + folder + '/flight_list.csv', 0o777)

	# No overlapping flights even though the queries overlap
	if not flights_copied:
		os.remove(cache_folder + out_dir + '/flight_list.csv')
		os.rmdir(cache_folder + out_dir)
		return False

	# Copy points list (data.txt) second
	data = open(cache_folder + folder + '/data.csv', 'r')
	data_out = open(cache_folder + out_dir + '/data.csv', 'w')
	data_out.write(data.readline())
	for line in data:
		date = line[0:8]
		if date > d_date and date < a_date:
			data_out.write(line)
	data.close()
	data_out.close()
	# os.chmod(cache_folder + folder + '/data.csv', 0o777)

	# create new json
	old_json = pquery.read_json(cache_folder + folder)
	new_json = {}
	old_params = folder.split('-')
	old_d_date = datetime.date(int(old_params[4][0:4]), int(old_params[4][4:6]), int(old_params[4][6:8]))
	old_a_date = datetime.date(int(old_params[5][0:4]), int(old_params[5][4:6]), int(old_params[5][6:8]))
	new_d_date = datetime.date(int(params['T1'][0:4]), int(params['T1'][4:6]), int(params['T1'][6:8]))
	new_a_date = datetime.date(int(params['T2'][0:4]), int(params['T2'][4:6]), int(params['T2'][6:8]))

	# estimate new total flights from fraction of old
	fraction_of_date = (new_a_date.toordinal() - new_d_date.toordinal())/(old_a_date.toordinal() - old_d_date.toordinal() + .1)
	new_json['fcount'] = old_json['fcount'] * fraction_of_date
	new_json['sampling_rate'] =  old_json['sampling_rate'] / fraction_of_date
	new_json['points_per_iteration'] = old_json['points_per_iteration']
	new_json['flights_per_iteration'] = old_json['flights_per_iteration']
	new_json['query'] = old_json['query']
	new_json['inner_query'] = old_json['inner_query'].replace(old_params[4], params['T1']).replace(old_params[5], params['T2'])
	new_json['points_file'] = cache_folder + out_dir + '/data.csv'
	new_json['is_iterated'] = 0

	pquery.dump_json(cache_folder + out_dir, new_json)

	# delete oldest in cache
	manage_cache_size()

	return True

def create_dir(name):
	"""
	Creates the specified directory
	"""
	os.makedirs(name)
	#os.chmod(name, 0o777)


def get_cache_current_load():
	"""
	Counts current stored CSV files in the cache
	"""
	#return len(os.walk(cache_folder).next()[2])
	return len(os.listdir(cache_folder))


def get_oldest_cached():
	"""
	Returns the oldest file in cache. This file is a candidate to be removed.
	"""
	files = [f for f in listdir(cache_folder)]
	min_t = 0
	oldest_file = ""
	for my_file in files:
		t = os.path.getmtime(cache_folder+my_file)
		if min_t == 0 or t < min_t:
			min_t = t
			oldest_file = my_file
	return oldest_file


def delete_from_cache(my_file):
	"""
	Removes an entry from the cache.
	"""
	#os.remove(cache_folder + my_file)
	path = cache_folder + my_file
	try:
		shutil.rmtree(path, ignore_errors = True)
	except:
		os.chmod(path, stat.S_IWUSR)
		shutil.rmtree(path) #final error will be propogated up


def insert_to_cache(params,content):
	"""
	Adds a CSV file to the cache based on query parameters and the
	content (in CSV format)
	"""
	dir_name = get_dir_name(params)
	f = open(cache_folder+dir_name+'/data.csv',"w")
	f.write(content)
	f.close()


def read_from_cache(params):
	"""
	Returns content of a CSV file in cache based on query parameters
	"""
	dir_name = get_dir_name(params)
	f = open(cache_folder+dir_name+'/data.csv',"r")
	content = f.read()
	return content


def execute_query(q):
	"""
	Unimplemented: Executes a query and returns the results as a CSV
	"""

	return ""


def cache_manage(params,q):
	"""
	Reads from cache if params exist and executes the query otherwise
	"""

	if is_in_cache(params) == True:
		return read_from_cache(params)
	else:
		content = execute_query(q)
		cache_load = get_cache_current_load()
		if cache_load == cache_capacity:
			delete_from_cache(get_oldest_cached())
		insert_to_cache(params,content)


def get_cached_file(params):
	"""
	Returns the matching cache file or an empty string
	"""

	if is_in_cache(params) == True:
		return read_from_cache(params)
	else:
		return ""


def cache_file(params, q):
	"""
	Inserts a file into the cache
	"""

	content = execute_query(q)
	manage_cache_size()
	insert_to_cache(params,content)


def manage_cache_size():
	"""
	Removes old items if the cache is too large
	"""

	cache_load = get_cache_current_load()
	if cache_load >= cache_capacity:
		delete_from_cache(get_oldest_cached())


# EXAMPLE
# The query q may contain values for following attributes:
# airline L, aircraft C, departure airport(s) P1, arrival airport(s) P2
# beginning of period T1, end of period T2.
params = {}
params["L"] = "EJA%"
params["C"] = ""
params["P1"] = correct_airports("CMH")
params["P2"] = correct_airports("AGS,TEB")
params["T1"] = "20140401"
params["T2"] = "20140430"
