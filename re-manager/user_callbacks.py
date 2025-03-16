import time

# create other user callbacks here. import modules as needed.

# use happi code found at beginning of startup.py to find devices available to be 
# communicated with.   Devices will be found from dev = happi.from_container(device). Then
# use yaqc-bluesky methods for daemon communication.
# 
# I haven't fully checked this yet, but sensors may not be available.  This makes the callbacks
# limited in scope.  
#
# The WT5 information should be available from the WT5 path env.  See the callback_wp.py
# for current state of this attempt to use.  In summary, the folder name is certainly 
# constructed properly in the _wp.py, but it is inaccessible for some reason.

# Use happi not yaqc_bluesky for devices

pass

