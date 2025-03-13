import time
import WrightTools as wt
import pathlib, os


# from user_callbacks import *

# docs received have keys with "plan_name",  "run_start" (same name used for stops) and "descriptor"
#. Current descriptors on REManager include events.  This code parses out the docs to determine if
# a run has started, stopped, or an intermediate, true event has occurred.  The code requires at
# least 2 data points for a run job for the event finding portion to work.  It also cannot 
# detect the first event in that run job.    However, the code should be relatively robust to
# multiple nested decorators of plans, so suspenders can be called separately and nested within the
# decorated syntax of the startup.py
#  
# insert callback functions at bottom.  The timestamp methods from the wt5 event model might be
#  used to determine the data folder for data, but virtualization may make the path inaccessible...
#  The timestamps would be inserted at a plan_name or run_start(start).   

event=False
descriptor_id_1=""
descriptor_id_2=""
run_id=""
start=False
stop=False
_started=False
_stopped=False
_eventfound=False
_envstarted=False

_plan_name=""
_name=""

run_dir=""
bluesky_doc_dir=""


def globalreset():
    global event
    global descriptor_id_1
    global descriptor_id_2
    global run_id
    global start
    global stop
    global _started
    global _stopped
    global _eventfound
    global run_dir
    global bluesky_doc_dir

    event=False
    descriptor_id_1=""
    descriptor_id_2=""
    run_id=""
    start=False
    stop=False
    _started=False
    _stopped=False
    _eventfound=False
    run_dir=""
    bluesky_doc_dir=""
    pass



def Callback_wp(name="event", doc={}):
    global event
    global descriptor_id_1
    global descriptor_id_2
    global run_id
    global start
    global stop
    global _started
    global _stopped
    global _eventfound
    global _envstarted
 
    global _plan_name
    global _name

    global run_dir
    global bluesky_doc_dir

    # Name (not name) document try-except
    # coding finds proper path for wt5 file but currently cannot access it
    try:
        if doc["Name"]:
            if _started==False:
                if _envstarted==False:
                    _envstarted=True
                    print("********")
                    print("New Env Started="+str(_envstarted))
                    print("********")

                timestamp = wt.kit.TimeStamp(doc["time"])
                path_parts = []
                path_parts.append(timestamp.path)
               
                _name=doc["Name"]
                _plan_name=doc["plan_name"]
                
                path_parts.append(_plan_name)
                path_parts.append(_name)
                path_parts.append(doc["uid"][:8])
                dirname = " ".join(x for x in path_parts if x)
                run_dir = pathlib.Path("/data") / dirname
                bluesky_doc_dir = run_dir / "bluesky_docs"
                run_dir=str(run_dir)
                bluesky_doc_dir=str(bluesky_doc_dir)

                
    except:
        start=False
        event=False
        stop=False
        pass
    

    #run_start document try-except
    try:
        if doc["run_start"]:
            if _started==False:            
                start=True
                _started=True
            if _stopped==False:
                if _eventfound:
                    stop=True
                    _stopped=True
    except:
        start=False
        event=False
        stop=False
        pass

    #descriptor document try-except
    try:    
        if doc["descriptor"]:
            descriptor_id_1=descriptor_id_2
            descriptor_id_2=doc["descriptor"]
            if descriptor_id_1 == descriptor_id_2:
                event=True
                _eventfound=True
                run_id=descriptor_id_2
            else:
                event=False
    except:
        start=False        
        event=False
        stop=False
        pass


    if start:
        # insert start function here
        pass

    if event: 
        # insert event function here   
        # time.sleep(0.25)
        pass

    if stop:
        # insert stop function here
        pass

    if _started & _stopped:
        globalreset()
        pass