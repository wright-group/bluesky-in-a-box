import time
# import other modules here as found by requirements.txt


def SimpleEventCallback(name="event", doc={}):
    print("received event...waiting")
    time.sleep(1.0)
    print("done")

