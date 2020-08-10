import serial_speedtest_ctest as ser
import json
import serial
import time
import threading
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setup(22, GPIO.IN, pull_up_down = GPIO.PUD_UP)


with open("structure_ctest.json") as f:
    struct = json.load(f)
    
with open("rsd.json") as f:
    countdown = json.load(f)

ser.signboard.load("/home/pi/neopixel_new", "structure_ctest.json")
m_comp, m_headers = ser.compile_frames(struct['objects'], "main.compiled", "structure_ctest.json")

ser.signboard.load("/home/pi/neopixel_new", "rsd.json")
c_comp, c_headers = ser.compile_frames(countdown['objects'], "rsd.compiled", "rsd.json")


objs = struct["objects"]
p = m_comp
headers = m_headers
mode = "main"

def callback():
        global conn, objs, p, headers, c_comp, c_headers, mode, countdown, numObjects, headerSent, currObject, currFrame
        print("INTERRUPTING")
        mode = "countdown"
        objs = countdown['objects']
        p = c_comp
        headers = c_headers
        numObjects = len(c_comp)
        currObject = -1
        currFrame = 0
        headerSent = False
        

#t = threading.Thread(target = callback)
#t.start()
 
GPIO.add_event_detect(22, GPIO.FALLING, callback=lambda x: callback())
   
    




conn = serial.Serial("/dev/ttyACM0", 4000000)
conn.flushInput()
conn.flushOutput()

currCycle = 0
numObjects = len(m_comp)
currObject = -1
numFrames = 1
currFrame = 0

headerSent = False
lastHeaderSent = 0



try:
    while True:
        v = conn.read()
        if v == b"H": 
            currObject+=1
            if currObject == numObjects: 
                currObject = 0
                currCycle += 1
                if mode == "countdown":
                    print("RETURNING")
                    mode = "main"
                    p = m_comp
                    headers = m_headers
                    objs = struct['objects']
                    currObject = 0
                    numObjects = len(p)
                    currCycle = 0
            
            numFrames = len(p[currObject]) if objs[currObject]['type']!='phrase' else len(p[currObject][0])
            currFrame = 0                       # just to be safe
            headerSent = True
            conn.write(headers[currObject])
            print("LOADING", currObject)
            print(numFrames, "num frames recvd", conn.readline())
            print("frame size recvd", conn.readline())
            print('time since last header', time.time() - lastHeaderSent)
            lastHeaderSent = time.time()
            
            
            
            
        if v == b"F": 
            if headerSent: 
                if objs[currObject]['type']!='phrase': 
                    conn.write(p[currObject][currFrame])
                else:
                    v = p[currObject]
                    conn.write(v[currCycle%len(v)][currFrame])
                    #print("writing color", currCycle%len(v))
            else:
                print("Sending interrupt frame")
                conn.write(b"\xff\xff\xff")      # interrupt frame
                print("received", conn.readline())
            #print("curr frame", currFrame)
            #print("curr object", currObject)
            #print(p[currObject-1][currFrame])
            #print("current frame recvd", ser.readline())
            #print("status", ser.readline())
            currFrame = (currFrame + 1) % numFrames
        #print(v)
        #print("-----------------------------------")
finally:
    conn.close()
    
