# Open the flight id cache file
file = open("ll.csv","r")
print "var addressPoints = ["
counter = 1

for line in file:
	# Parse line (individual point)
	counter += 1
	line = line.strip()
	parts = line.split(",")
	lat = parts[7]
	lng = parts[8]
	alt = parts[9]

	# Skip header and sample
	if counter == 1 or counter % 30 != 0:
		continue

	# Print info (latitude, longitude, and altitude)
	print "["+lat+","+lng+",\""+alt+"\"],"

print "];"
