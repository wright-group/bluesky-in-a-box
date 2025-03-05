#import os
#import pathlib

from bluesky.callbacks.zmq import RemoteDispatcher
from bluesky.callbacks.zmq import Publisher
from bluesky import RunEngine
from user_callbacks_suspenders import *

'''
#dispatcher = RemoteDispatcher("zmq-proxy:5568")
RE= RunEngine({})
publisher = Publisher("zmq-proxy:5567")
dispatcher1= RemoteDispatcher("zmq-proxy:5567")

dispatcher2= RemoteDispatcher("zmq-proxy:5569")
# Run through the callbacks and suspenders found in the second file and subscribe 
# those you currently want...
CB1=SimpleTestCallback()
RE.subscribe(publisher)
dispatcher2.subscribe(CB1)
# etc.
dispatcher1.subscribe(CB1)
dispatcher2.start()
'''

pass
