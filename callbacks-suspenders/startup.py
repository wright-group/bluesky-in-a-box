#import os
#import pathlib

from bluesky.callbacks.zmq import RemoteDispatcher
from user_callbacks_suspenders import *

dispatcher = RemoteDispatcher("zmq-proxy:5568")

# Run through the callbacks and suspenders found in the second file and subscribe 
# those you currently want...
CB1=SimpleTestCallback()
dispatcher.subscribe(CB1)

# etc.

dispatcher.start()

