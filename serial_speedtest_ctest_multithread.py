# To predict time of a phrase:
# (n*0.00003+d+(5*r*c/b))*(c+s*(w+1)*l-1)
# where:
#  n = number of LEDs per string
#  d = speed
#  r = rows
#  c = cols
#  b = serial baud rate
#  s = scale
#  w = width of a character
#  l = length of the phrase

import signboard_ctest_multithread as signboard

import serial
#import RPi.GPIO as GPIO
import os
import sys
import math
import time
import hashlib
import base64
import web_manager
import threading
import multiprocessing
import re
import json
#import lcd_keyboard_manager as lcd_key

arg = " ".join(sys.argv)
ser = None
baud = 4000000
web_manager.root = signboard.root
running = True

# Regexes match the argument name followed by a string containing non-space characters, except when escaped with a backslash

filename = re.search(r"--file ((?:\\ |[^ \n])+)", arg)
if filename is None: 
    print("Please specify structure file using --file argument")
    exit()
else: filename = filename.group(1)

portname = re.search(r"--port ((?:\\ |[^ \n])+)", arg)
if portname is None: portname = ""
else: portname = portname.group(1)

current_file = filename
recompile = "--recompile" in sys.argv


def color2bytes(x):
    b = bytearray("   ", "utf-8")
    b[0] = int((x>>16)&255)
    b[1] = int((x>>8) &255)
    b[2] = x & 255
    return b


def compile_frame(frame, col, dtime):
    return bytearray([int(dtime>>8), dtime&255]) + b"".join([ bytearray([(col.index(frame[x])<<4) + (0 if len(frame)==x+1 else col.index(frame[x+1]))]) for x in range(0, len(frame), 2) ])


def compile_one(index, obj, pcol, t, begin, end):
    global p
#    start_time = time.time()
#    print("Starting compile for", index, begin, end)
    pfrms = []
    #print("First LED value", obj[0][0], pcol.index(obj[0][0]))
    #print(compile_frame(obj[0][:10], pcol, 2))
    if t=='phrase':
        for cnum, color in enumerate(obj):                                          # color is the rendered frame with that color
            comp = []                                                               # comp is the current compiled color
            cdata = objs[index]['colors'][cnum]
#            print('compiling with color', cdata, len(color))
            for num, frm in enumerate(color[begin:end]):
                dtime = 0
                comp.append(compile_frame(frm, pcol, objs[index]['speed']))         # Compile a frame with the current list of colors
            
            for x in range(cdata['duration']): pfrms.append(comp)
        for i, x in enumerate(pfrms): p[index][i][begin:end]=x                      # Append each of the compiled segments to their respective color arrays
    else:
        for num, frm in enumerate(obj[begin:end]):
            dtime = 0
            if t=='image': dtime = objs[index]['time']
            if t=='animation': dtime = objs[index]['frames'][num%len(objs[index]['frames'])]['time']
            pfrms.append(compile_frame(frm, pcol, dtime))                           # Compile a frame with the current list of colors
        p[index][begin:end] = (pfrms)
    
    return (index, pfrms, t, slice(begin,end))
#    p[index] = pfrms
#    print("Finishing compile for", index, begin, len(pfrms), len(pfrms[0]))


def apply_results(args):
    index, pfrms, t, s_range = args
    global p
    if t=="phrase":
        for i, x in enumerate(pfrms): p[index][i][s_range]=x
    else: p[index][s_range]=pfrms


def compile_frames(objs, comp_fname, fname):
    global p
    global headers

    #check if previous data is available
    v = os.listdir()
    p = [[] if x['type']!='phrase' else [[]]*sum(y['duration'] for y in x['colors']) for x in objs]; headers = [None]*len(objs)
    dont_render = []
    print(p)    


    if recompile: 
        print("Forced recompile")
    elif comp_fname in v:
        print("version found")
        with open(comp_fname) as f:
            j = json.load(f)
            if len(j) == len(objs):
                for obj_index, obj in enumerate(j):
                    h_n = hashlib.md5()
                    h_n.update(json.dumps(objs[obj_index], sort_keys=True).encode())
                    if h_n.hexdigest() == obj['hash'].strip():
                        print("version found with matching hash for object", obj_index)
                        headers[obj_index] = (eval(base64.b64decode(obj['header'].encode()).decode()))
                        p[obj_index] = (eval(base64.b64decode(obj['frames'].encode()).decode()))
                        print(obj['header'], base64.b64decode(obj['header'].encode()).decode())
                        dont_render.append(obj_index)
                    else:
                        print("hashes do not match for {}: old={} and new={}".format(obj_index, obj['hash'].strip(), h_n.hexdigest()))
                        headers[obj_index] = (None)
                        p[obj_index] = (None)
                    
             
    


    rendered = signboard.render(objs, dont_render)
    p_in = list(filter(lambda x: x is not None, rendered))

    slen = signboard.ROWS*signboard.COLS

    print("size of the signboard", slen, len(p_in))


    obj2colors = lambda obj: list(map(list, set(map(tuple, (col for frm in obj for col in frm)))))

#    pcolors = []
    print("Before compiling", [bool(x) for x in p])

    comp_start = time.time()
   
    for index, obj in enumerate(p_in):
        if bool(p[index]) and bool(p[index][0]): 
            print("Skipping compile for", index)
            continue
        t = objs[index]['type']
        
        if t!='phrase': pcol = [-1] + obj2colors(obj)
        else: pcol = [-1] + [y for x in obj for y in obj2colors(x)]
        
        nfrms = len(obj) if t!='phrase' else len(obj[0])
        phead = bytearray([int(nfrms>>8), nfrms&255, int(slen>>8), slen&255])
        for col in pcol[1:]:
            phead += bytearray(col)                 # put colors in the header
        headers[index] = phead
       
        # Put in blank frames
        if len(p[index]) > 0:
            for i,x in enumerate(p[index]): p[index][i] = [None]*nfrms
#            print(len(p[index][0]))
        else: p[index] = [None]*nfrms

#        if t=="phrase": print("before {}, empty len {} non-None {} nfrms {}".format(index, len(p[index][0]), len(list(filter(lambda x:x is not None, p[index][0]))), nfrms))
#        else: print("before {}, empty len {} nfrms {}".format(index, len(p[index]), nfrms))
        #print(index, "nfrms", nfrms, len(p[index]))


        new_threads = []

        pool = multiprocessing.Pool()

        if nfrms <= 50:
            #thr = threading.Thread(target=compile_one, args=(index, obj, pcol, t, 0, nfrms))
            #thr.start()
            #new_threads.append(thr)
            pool.apply_async(compile_one, args=(index, obj, pcol, t, 0, nfrms), callback=apply_results)
        elif nfrms <=200:
            n_proc = 0
            while n_proc < nfrms:
#                print("starting thread", nproc)
                #thr = threading.Thread(target=compile_one, args=(index, obj, pcol, t, n_proc, n_proc+50))
                #thr.start()
                #new_threads.append(thr)
                pool.apply_async(compile_one, args=(index, obj, pcol, t, n_proc, n_proc+50), callback=apply_results)
                n_proc += 50
        else:
            nper = nfrms // 4 + 1
            for x in range(4):
                #thr = threading.Thread(target=compile_one, args=(index, obj, pcol, t, nper*x, nper*x+nper))
                #thr.start()
                #new_threads.append(thr)
                pool.apply_async(compile_one, args=(index, obj, pcol, t, nper*x, nper*x+nper), callback=apply_results)
        #for x in new_threads: x.join()
        pool.close()
        pool.join()
#        if t=="phrase": print(index, len(p[index][0]), len(list(filter(lambda x:x is not None, p[index][0]))))
#        else: print(index, len(p[index]))
    print("All threads terminated in", time.time() - comp_start)

        
    with open(comp_fname, "w") as f:
        f.write("[\n")
        for i in range(len(objs)):
            object_hash = hashlib.md5()
            object_hash.update(json.dumps(objs[i], sort_keys=True).encode())
            print("Saving with hash {} for {}".format(object_hash.hexdigest(), i))

            if i != 0: f.write(",\n")
            f.write('    {\n        "hash": "%s",\n' % (object_hash.hexdigest()))
            f.write('        "header": "{}",\n'.format(base64.b64encode(str(headers[i]).encode()).decode()))
            f.write('        "frames": "{}"\n'.format(base64.b64encode(str(p[i]).encode()).decode()))
            f.write("    }")
        f.write("\n]\n")

    print("After compiling", [bool(x) for x in p], [(i, len(x)) for i, x in enumerate(p) if isinstance(x, list)]) 
    
    
        



def reload(f=current_file):
    global p, headers, objs, numObjects, currObject, numFrames, currFrame, ser, running
    running = False
    if ser is not None: ser.write(b"\xff\xff\xff\x00")
    signboard.load(f)
    objs = signboard.objects
    compile_frames(objs, "active.compiled", f)
    numObjects = len(p)
    currObject = -1
    numFrames = 1
    currFrame = 0
    current_file = f
    running = True

if __name__ == "__main__":
    reload()
    web_manager.reload = reload

    threading.Thread(target=web_manager.run).start()

    #lcd_key.reload_callback = reload    

    currCycle = 0

    numObjects = len(p)
    currObject = -1

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

    if portname == "": 
        print("Please specify port name with --port argument")
        exit()

    while ser is None:
        try:
            ser = serial.Serial(portname, baudrate=baud)
        except Exception as e:
            print("Error ocurred: "+str(e))
            time.sleep(1)
    ser.flushInput()
    ser.flushOutput()

    headerSent = False

    lastHeaderSent = 0 


    try:
        print("Sending interrupt frame")
        ser.write(b'\xff\xff\xff\x00')
        while True:
            if not running: continue
            v = ser.read()
#            print(v)
            if v == b"H": 
                currObject+=1
                if currObject == numObjects: 
                    currObject = 0
                    currCycle += 1
                
                numFrames = len(p[currObject]) \
                                if objs[currObject]['type']!='phrase' \
                                else len(p[currObject][0])
                currFrame = 0                       # just to be safe
                headerSent = True
                ser.write(headers[currObject])
                print("\n LOADING", currObject)
#                print(numFrames, "num frames recvd", ser.readline())
#                print("colors", ser.readline())
#                print('time since last header', time.time() - lastHeaderSent)
                lastHeaderSent = time.time()
                
                
                
                
            if v == b"F": 
                if headerSent: 
                    if objs[currObject]['type']!='phrase': ser.write(p[currObject][currFrame])
                    else:
                        v = p[currObject]
                        ser.write(v[currCycle%len(v)][currFrame])
                        #print("writing color", currCycle%len(v))
                    print("\rServing frame "+str(currFrame)+"/"+str(numFrames), end="")
                else:
                    print("Sending interrupt frame")
                    ser.write(b"\xff\xff\xff\x00")      # interrupt frame
#                    print("received", ser.readline())
                #print("curr frame", currFrame)
                #print("curr object", currObject)
                #print(p[currObject-1][currFrame])
                #print("current frame recvd", ser.readline())
                #print("status", ser.readline())
#                if currObject == 0 and currFrame == 50: 
#                    print(len(p[0]))
#                    print(p[currObject][currCycle%len(p[currObject])][currFrame])
                currFrame = (currFrame + 1) % numFrames
            #print(v)
            #print("-----------------------------------")
    finally:
        ser.close()
    
