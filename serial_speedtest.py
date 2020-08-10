import signboard

import serial
#import RPi.GPIO as GPIO
import os
import sys
import math

baud = int(sys.argv[1])
v = sys.argv[2]


def color2bytes(x):
    b = bytearray("   ", "utf-8")
    b[0] = int((x>>16)&255)
    b[1] = int((x>>8) &255)
    b[2] = x & 255
    return b


def compile_frame(frame, col, dtime):
    return bytearray([int(dtime>>8), dtime&255]) + b"".join([ bytearray([(col.index(frame[x])<<4) + (0 if len(frame)==x+1 else col.index(frame[x+1]))]) for x in range(0, len(frame), 2) ])



p_in = list(filter(lambda x: x is not None, signboard.phrases_rendered))
#p_in = [[p_in[0][0]], [p_in[1][0]]]

slen = signboard.ROWS*signboard.COLS

print("size of the signboard", slen)

objs = list(filter(lambda x: x['type'] in ['phrase', 'image', 'animation'], signboard.objects))


p = []; headers = []; pcolors = []
for index, obj in enumerate(p_in):
    pcol = [-1] + list(map(list, set(map(tuple, (col for frm in obj for col in frm)))))
    pcolors.append(pcol)
    print("Colors are", pcol)
    
    nfrms = len(obj)
    phead = bytearray([int(nfrms>>8), nfrms&255, int(slen>>8), slen&255])
    for col in pcol[1:]:
        phead += bytearray(col)                 # put colors in the header
    headers.append(phead)
    
    pfrms = []
    print("First LED value", obj[0][0], pcol.index(obj[0][0]))
    print(compile_frame(obj[0][:10], pcol, 2))
    for num, frm in enumerate(obj):
        dtime = 0
        t = objs[index]['type']
        if t=='phrase': dtime = signboard.settings['speed']
        if t=='image': dtime = objs[index]['time']
        if t=='animation': dtime = objs[index]['frames'][num%len(objs[index]['frames'])]['time']
        pfrms.append(compile_frame(frm, pcol, dtime))  # Compile a frame with the current list of colors
    
    p.append(pfrms)
        




currCycle = 0

numObjects = len(p)
currObject = 0

numFrames = 1
currFrame = 0

print(len(signboard.phrases_rendered))
print("num objects: {}".format(numObjects))


"""
def send(c):
    global ser, v, cc, hcc
    if GPIO.input(22):
        # data
        ser.write(chr(comp[cc]).encode())
        cc+=1
    else:
        # header
        ser.write(chr(hlen+hcc).encode()+header[hcc*63:(hcc+1)*63])
        hcc+=1	#TODO: finish chunk generator
"""

ser = serial.Serial("/dev/"+list(filter(lambda x: x.startswith("ttyACM"), os.listdir("/dev/")))[0], baudrate=baud)

headerSent = False


try:
    while True:
        v = ser.read()
        if v == b"H": 
            ser.write(headers[currObject])
            print("LOADING", currObject)
            print(numFrames, "num frames recvd", ser.readline())
            print("frame size recvd", ser.readline())
            currObject+=1
            if currObject == numObjects: 
                currObject = 0
                currCycle += 1
            numFrames = len(p[currObject-1])    # set to the previous
            currFrame = 0                       # just to be safe
            headerSent = True
            
        if v == b"F": 
            if headerSent: ser.write(p[currObject-1][currFrame])
            else:
                print("Sending interrupt frame")
                ser.write(b"\xff\xff\xff")      # interrupt frame
                print("received", ser.readline())
            #print("curr frame", currFrame)
            #print("curr object", currObject)
            #print(p[currObject-1][currFrame])
            #print("current frame recvd", ser.readline())
            #print("status", ser.readline())
            currFrame = (currFrame + 1) % numFrames
        #print(v)
        #print("-----------------------------------")
finally:
    ser.close()
    
