import random


# Open the points file
file = open("ll.csv","r")
counter = 0
flight_colors = {}
flight_ids = []

for line in file:
	# Parse the line (individual point)
	counter += 1
	line = line.strip()
	parts = line.split(",")
	fid = parts[0]

	if fid not in flight_ids:
		# Add the id to flight ids
		flight_ids.append(fid)

		# Generate a color for the flight
		r = random.randint(0,255)
		g = random.randint(0,255)
		b = random.randint(0,255)
		flight_colors[fid] = "rgb("+str(r)+","+str(g)+","+str(b)+")"

	# Parse data
	date = parts[1]
	from_aprt = parts[3]
	to_aprt = parts[6]
	lat = parts[7]
	lng = parts[8]
	alt = parts[9]
	point_time = parts[10]
	description = "Flight "+fid+" from "+from_aprt+" to "+to_aprt+" in "+date+" at "+point_time

	# Skip header
	if counter == 1 or counter % 5 != 0:
		continue

	# Print output
	print "var circle"+str(counter)+" = L.circle(["+lat+", "+lng+"], 15000, { fillColor: '"+flight_colors[fid]+"', fillOpacity: 0.8, stroke: false}).addTo(map);\n"
	print "circle"+str(counter)+".bindPopup(\""+description+"\")"
