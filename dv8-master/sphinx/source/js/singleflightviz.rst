multipointviz/
====

gen_points_geo.py
----

This file loads the cached points CSV and parses the flights into a list of
IDs and colors. It then prints a unique JS variable for each point that
contains the definition of the corresponding circle for use in the GUI.

gen_points_heat.py
----

This file loads the cached points CSV and prints a JSON array containing the
latitude, longitude, and altitude of each point.

sample.js
----

This file contains a sample list of coordinates.
