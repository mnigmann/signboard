#TODO: animation frame editor

import keyboard
import lcddriver2 as drv
import time
import json
import re
import os
import subprocess
import threading

PASSWORD = "pwd"

with open("structure_ctest.json") as f: cont = json.load(f)

currobjnum = 0
obj = None
mode = "olist"

lcd = drv.lcd()

lcd.lcd_write(0x0F)

cmd = ""
header = ""
cursorpos = [0,0]

curredit = 0    # currently highlighted
currstart = 0   # current one at top of list (for scroll)

# for animations
pstart = 0
pcurr = 0

reload_callback = None
displayingIP = False

lastMode = ""

confcallback = None

#lcd.lcd_display_string(">", 2)
#write()


shifts = {
    "−": "_"
}
shifts.update([[a, b] for a, b in zip("`1234567890-=[]\;',./", "~!@#$%^&*()_+{}|:\"<>?")])
print(shifts)


fontdata1 = [      
        [ 0b00000, 
          0b00000, 
          0b00000, 
          0b00000, 
          0b00000, 
          0b00000, 
          0b00000, 
          0b10101 ],
]

lcd.lcd_load_custom_chars(fontdata1)


def close():
    global timer
    timer = None
    lcd.lcd_write(0x08)

timer = threading.Timer(30, close)
timer.start()

def setcursor(row, col):
    rows = [
        0,
        64,
        20,
        84
    ]
    lcd.lcd_write(0x80+rows[row]+col)

def disp(clear=False):
    global cmd, header
    print(">"+cmd+"<")
    if clear: lcd.lcd_clear()
    lcd.lcd_display_string(header, 1)
    lcd.lcd_display_string(">"+cmd[:19], 2)
    if len(cmd) > 19:
        lcd.lcd_display_string(cmd[19:39], 3)
        if len(cmd) > 39: lcd.lcd_display_string(cmd[39:59], 4)
        

def nextLine():
    global curredit, currstart, cursorpos, obj
    curredit = (curredit + 1) % len(obj["colors"])
    print("curredit is now", curredit)
    if curredit == currstart+3:
        print("increasing start to", currstart+1)
        currstart += 1
    if curredit < currstart: currstart = curredit
    cursorpos[0] = curredit - currstart + 1

def prevLine():
    global curredit, currstart, cursorpos, obj
    curredit = (curredit - 1) % len(obj["colors"])
    if curredit < currstart:
        currstart = curredit
    elif curredit >= currstart + 3:
        currstart = curredit - 2
    cursorpos[0] = curredit - currstart + 1

def confirm(*prompt, cb):
    global mode, confcallback
    confcallback = (cb, mode)
    mode = "conf"
    lcd.lcd_clear()
    for i, x in enumerate(prompt): lcd.lcd_display_string(x, 1+i)


def delobj(idx):
    global cont
    cont["objects"].remove(cont['objects'][idx])

def write(evt=None):
    global cmd, header, currobjnum, obj, mode, cursorpos, curredit, currstart, confcallback, pcurr, pstart, displayingIP, timer, PASSWORD, lastMode
    name = evt.name if evt is not None else "enter"
    key = None
    if evt is not None:
        key = list(keyboard.get_typed_strings([evt]))[0]
        if keyboard.is_pressed("shift"):
            #print("shift pressed")
            if key in shifts: key = shifts[key]
            key = key.upper()
    print(key, name, mode)
    
    if timer is None:
        lcd.lcd_write(0x0C)
        lcd.lcd_write(0x0F)
        print("No timer found")
        lastMode = mode
        mode = "pwd"
        #This prevents any action from being taken
        name = key = "  "
    else: timer.cancel()
    timer = threading.Timer(30, close)
    timer.start()
    
    
    if displayingIP == True and key != "a" and not keyboard.is_pressed("alt"):
        displayingIP = False
        name = key = "  "

    ### PASSWORD ENTRY MODE ###
    if mode == "pwd":
        if key is not None and len(key) == 1:
            cmd += key
        elif name == "backspace":
            cmd = cmd[:-1]
        elif name == "enter":
            if cmd == PASSWORD:
                mode = lastMode
                # This prevents any action from being taken
                name = key = "  "
            cmd = ""
        
        lcd.lcd_clear()
        lcd.lcd_display_string("Enter password:", 1)
        lcd.lcd_display_string("*"*len(cmd), 2)

    ### NORMAL MODE ###
    if mode == "":
        if name == "tab" and cmd.startswith("path "):
            img = os.listdir("images")
            s = cmd.split(" ")[1]
            img = list(filter(lambda x: x.startswith(s), img))
            print(img)
            if len(img)==1: 
                cmd = "path "+img[0]
                disp()
            elif len(img) > 1:
                cmd = "path "+os.path.commonprefix(img)
                disp()
        if name == "backspace":
            cmd = cmd[:-1]
            disp(True)
        elif name == "enter":
            print("Command is", cmd, currobjnum)
            if currobjnum is not None:
                print("current object is", obj)
                if cmd == "finish":
                    cmd = ""
                    header = ""
                    mode = "olist"
                    obj = None

                elif obj['type'] == 'phrase':
                    if cmd.startswith("set"):
                        obj['phrase'] = cmd.split(" ", 1)[1]
                        print("setting phrase", currobjnum, cmd.split(" ", 1)[1])
                        cmd = ""
                        disp(True)
                    if cmd.split(" ")[0] in ['step', 'speed', 'offset']:
                        obj[cmd.split(" ")[0]] = int(cmd.split(" ")[1])
                        cmd = ""
                        disp(True)
                    if cmd == "colors":
                        cmd = ""
                        mode = "p:c"
                        cursorpos = [1, 13]
                elif obj['type'] == 'image':
                    if cmd.startswith("offset"):
                        obj['startoffset'] = int(cmd.split(" ")[1])
                    elif cmd.startswith("path"): 
                        obj['path'] = cmd.split(" ")[1]
                    elif cmd.startswith("time"):
                        obj['time'] = int(cmd.split(" ")[1])
                    cmd = ""
                    disp(True)
                elif obj['type'] == 'animation':
                    m = re.match(r"(iterations|start|step) (-?\d+)", cmd)
                    print(m)
                    if m is not None:
                        obj[m.group(1)] = int(m.group(2))
                        cmd = ""
                        disp(True)
                    elif cmd.startswith("descr"):
                        obj['descr'] = cmd.split(" ", 1)[1]
                        cmd = ""
                        disp(True)
                    elif cmd == "frames":
                        cmd = ""
                        mode = "frm"
                        cursorpos = [1, 6]
        if len(key) == 1 and not keyboard.is_pressed("ctrl"):
            #print("adding key >"+key+"<, was >"+cmd+"<")
            cmd += key
            #print(">"+cmd+"<")
            disp()    
        elif name == "  ":
            disp(True) 
    """
    ### COMMAND MODE ###
    elif mode == "cmd":
        if name == "backspace": 
            cmd = cmd[:-1]
            disp(True)
        elif name == "enter":
            mode = "olist"
            if cmd == "reboot":
                cmd = ""
                obj = None
                confirm("Are you sure you", "want to reboot?", cb=lambda: print("Restarting"))
                return
            obj = None
            cmd = ""
        if len(key) == 1 and not keyboard.is_pressed("ctrl"):
            cmd += key
            disp()
    """


    ### FRAME EDITING MODE ###
    if mode == "frm":
        c_frm = obj['frames'][curredit]
        c_key = ["path", "time", "offset"][cursorpos[0]-1]
        c_val = c_frm[c_key]
        
        tabbed = False

        if name == "tab" and cursorpos[0] == 1:
            poss = os.listdir("images")
            poss = list(filter(lambda x: x.startswith(c_val), poss))
            if len(poss) == 1:
                if poss[0] == c_val: pass
                else:
                    c_frm[c_key] = poss[0]
                    tabbed = True
            elif len(poss) > 1:
                c_frm[c_key] = os.path.commonprefix(poss)
                tabbed = True
            

        if tabbed: 
            pcurr = len(c_frm[c_key])
            pstart = max(pcurr-13, 0)
            cursorpos[1] = pcurr - pstart + 6
        elif name == "tab":
            curredit = (curredit + (-1 if keyboard.is_pressed("shift") else 1)) % len(obj['frames'])
        elif name == "right" and not keyboard.is_pressed("alt"):
            if cursorpos[0] == 1:
                pcurr = (pcurr + 1) % (len(str(c_val))+1)
                if pcurr >= 14: pstart = pcurr-13
                if pcurr < pstart: pstart = pcurr
                cursorpos[1] = pcurr - pstart + 6
            elif cursorpos[1] < len(str(c_val))+6:
                cursorpos[1] += 1
        elif name == "left" and not keyboard.is_pressed("alt"):
            if cursorpos[0] == 1:
                pcurr = (pcurr - 1) % (len(str(c_val))+1)
                if pcurr < pstart: pstart = pcurr
                if pcurr >= 14: pstart = pcurr-13
                cursorpos[1] = pcurr - pstart + 6
            elif cursorpos[1] > 6: cursorpos[1] -= 1
        elif name == "down":
            if cursorpos[0] != 3:
                cursorpos[0] += 1
                cursorpos[1] = min(cursorpos[1], 6+len(str(c_frm[["path", "time", "offset"][cursorpos[0]-1]])))
                pstart = 0
        elif name == "up":
            if cursorpos[0] != 1:
                cursorpos[0] -= 1 
                cursorpos[1] = min(cursorpos[1], 6+len(str(c_frm[["path", "time", "offset"][cursorpos[0]-1]])))
                if cursorpos[0] == 1:
                    pcurr = cursorpos[1] - 6
        elif key and key in "1234567890" and cursorpos[0] in [2,3]:
            s = str(c_val)
            s = s[:cursorpos[1]-6]+key+s[cursorpos[1]-6:]
            c_frm[c_key] = int(s)
            cursorpos[1]+=1
        elif name == "backspace" and cursorpos[0] in [2, 3] and cursorpos[1] != 6:
            s = str(c_val)
            print(s, s[:cursorpos[1]-7], s[cursorpos[1]-6:])
            s = s[:cursorpos[1]-7]+s[cursorpos[1]-6:]
            c_frm[c_key] = "" if s=="" else int(s)
            cursorpos[1] -= 1
        elif key and cursorpos[0] == 1 and not keyboard.is_pressed("ctrl"):
            c_frm[c_key] = c_val[:pcurr]+key+c_val[pcurr:]
            pcurr = (pcurr + 1) % (len(c_frm[c_key])+1)
            if pcurr >= 14: pstart = pcurr-13
            cursorpos[1] = pcurr - pstart + 6
        elif cursorpos[0] == 1 and name == "backspace":
            c_frm[c_key] = c_val[:pcurr-1]+c_val[pcurr:]
            print("backspace", pstart, pcurr)
            if pstart > 0:
                pstart -= 1
                pcurr -= 1
            elif pcurr > 0:
                pcurr -= 1
            print(pstart, pcurr)
            cursorpos[1] = pcurr - pstart + 6
        #alt must be pressed, or else it would've worked above
        elif name == "right" or name == "end":
            if cursorpos[0] == 1:
                pcurr = len(c_val)
                pstart = max(pcurr - 13, 0)
                cursorpos[1] = pcurr - pstart+6
            else:
                cursorpos[1] = 6+len(str(c_val))
        elif name == "left" or name == "home":
            pcurr = 0
            pstart = 0
            cursorpos[1] = 6
        elif name == "esc":
            mode = ""
            cmd = ""
            disp(True)
            return
        elif name == "delete" and cursorpos[0] == 1:
            c_frm[c_key] = c_val[:pcurr]+c_val[pcurr+1:]
        elif key == "a" and keyboard.is_pressed("ctrl"):
            curredit = len(obj['frames'])
            obj['frames'].append({"path": "", "time": 10, "offset": 0})
        elif key == "i" and keyboard.is_pressed("ctrl"):
            obj['frames'].insert(curredit, {"path": "", "time": 10, "offset": 0})

        elif name == "enter" or name == "  ": pass
        else: return

        

        
        p = obj['frames'][curredit]['path']
        print("FRame editor")
        lcd.lcd_clear()
        lcd.lcd_display_string("Object {}, frame {}".format(currobjnum, curredit), 1)
        lcd.lcd_display_string("Path: "+p[pstart:14+pstart], 2)
        lcd.lcd_display_string("Time: "+str(obj['frames'][curredit]['time']), 3)
        lcd.lcd_display_string("Ofs.: "+str(obj['frames'][curredit]['offset']), 4)
        setcursor(*cursorpos)

    ### COLOR EDITING MODE ###
    """    if mode == "p:c":
        if key and key in "0123456789abcdef" and cursorpos[1] < 16:
            print("Input", key)
            c_or_b = cursorpos[1] >= 8
            cbkey = "background" if c_or_b else "color"
            cidx = ((cursorpos[1] % 8) - 1)//2
            # upper nibble
            if cursorpos[1]%2 == 1:
                obj["colors"][curredit][cbkey][cidx] = (obj["colors"][curredit][cbkey][cidx] | 0xF0) & (("0123456789abcdef".find(key) << 4) | 0x0F)
            else:
                obj["colors"][curredit][cbkey][cidx] = (obj["colors"][curredit][cbkey][cidx] | 0x0F) & ("0123456789abcdef".find(key) | 0xF0)
            cursorpos[1] += 1
        elif key and key in "0123456789" and cursorpos[1] >= 16:
            s = str(obj["colors"][curredit]["duration"])
            idx = cursorpos[1] - 16
            s = s[:idx]+key+s[idx:]
            obj["colors"][curredit]["duration"] = int(s)
        elif name == "tab" and keyboard.is_pressed("shift"):
            if cursorpos[1] == 1:
                prevLine()
                cursorpos[1] = 16
            elif cursorpos[1] <= 9:
                cursorpos[1] = 1
            elif cursorpos[1] <= 16:
                cursorpos[1] = 9
        elif name == "tab":
            if cursorpos[1] >= 16:
                nextLine()
                cursorpos[1] = 1
            elif cursorpos[1] >= 8:
                cursorpos[1] = 16
            else:
                cursorpos[1] = 9
        
        elif name == "right":
            if cursorpos[1] == 6: cursorpos[1] = 9
            elif cursorpos[1] == 14: cursorpos[1] = 16
            elif cursorpos[1] == len(str(obj["colors"][curredit]["duration"])) + 16: 
                nextLine()
                cursorpos[1] = 1
            else:
                cursorpos[1]+=1
        elif name == "left":
            if cursorpos[1] == 16: cursorpos[1] = 14
            elif cursorpos[1] == 9: cursorpos[1] = 6
            elif cursorpos[1] == 1:
                prevLine()
                cursorpos[1] = 16 + len(str(obj["colors"][curredit]["duration"]))
            else: cursorpos[1] -= 1
        elif name == "down":
            nextLine()
        elif name == "up":
            prevLine()
        elif name == "esc":
            print("Leaving color editor")
            cmd = ""
            mode = ""
            lcd.lcd_clear()
            lcd.lcd_display_string(header, 1)
            lcd.lcd_display_string(">", 2)
            return
        

        # When it is loaded
        elif name == "enter": pass
        # If none of the above conditions met, don't redraw
        else: return
        
        print("cursorpos is", cursorpos)
        lcd.lcd_clear()
        lcd.lcd_display_string(header, 1)
        for i, x in enumerate(obj['colors'][currstart:currstart+3]):
            lcd.lcd_display_string("#%02x%02x%02x #%02x%02x%02x %d" % tuple(x['color'] + x['background'] + [x['duration']]), i+2)
        setcursor(*cursorpos)"""
    if mode == "p:c":
        if name == "tab" and not keyboard.is_pressed("shift"):
            curredit = (curredit + 1) % len(obj['colors'])
        elif name == "tab": 
            curredit = (curredit - 1) % len(obj['colors'])
        elif name == "right":
            if cursorpos[0] == 3: 
                if cursorpos[1] != 13+len(str(obj['colors'][curredit]['duration'])): cursorpos[1] += 1
            elif cursorpos[1] != 19: cursorpos[1] += 1
        elif name == "left":
            if cursorpos[1] != 13: cursorpos[1] -= 1
        elif name == "down":
            if cursorpos[0] != 3: cursorpos[0]+=1
        elif name == "up":
            if cursorpos[0] != 1: cursorpos[0] -= 1
        elif key and key in "0123456789abcdef" and cursorpos[0] != 3 and not keyboard.is_pressed("ctrl"):
            cidx = (cursorpos[1]-13)//2
            cbidx = ("color", 'background')[cursorpos[0]-1]
            l = obj['colors'][curredit][cbidx]

            if cursorpos[1] % 2 == 1:
                l[cidx] = (l[cidx] | 0xF0) & (("0123456789abcdef".find(key) << 4) | 0x0F)
            else:
                l[cidx] = (l[cidx] | 0x0F) & (("0123456789abcdef".find(key)) | 0xF0)
            if cursorpos[1] != 19: cursorpos[1] += 1
        elif key and key in "0123456789" and cursorpos[0] == 3:
            s = str(obj['colors'][curredit]['duration'])
            s = s if s != "0" else ""
            s = s[:cursorpos[1]-13]+key+s[cursorpos[1]-13:]
            obj['colors'][curredit]['duration'] = int(s)
            if cursorpos[1] != 13: cursorpos[1] += 1
        elif name == "backspace" and cursorpos[0] == 3 and cursorpos[1] != 13:
            s = str(obj['colors'][curredit]['duration'])
            s = s[:cursorpos[1]-14]+s[cursorpos[1]-13:]
            obj['colors'][curredit]['duration'] = int(s) if s else 0
            if cursorpos[1] != 19: cursorpos[1] -= 1
        elif name == "esc":
            mode = ""
            cmd = ""
            disp(True)
            return
        elif key == "a" and keyboard.is_pressed("ctrl"):
            curredit = len(obj['colors'])
            obj['colors'].append({"color": [128, 128, 128], "background": [0, 0, 0], "duration": 1})
        elif key == "i" and keyboard.is_pressed("ctrl"):
            obj['colors'].insert(curredit, {"color": [128, 128, 128], "background": [0, 0, 0], "duration": 1})

        elif name == "enter" or name == "  ": pass
        else: return

        lcd.lcd_clear()
        lcd.lcd_display_string("Color {} of obj {}".format(curredit, currobjnum), 1)
        lcd.lcd_display_string("Color     : #%02x%02x%02x" % tuple(obj['colors'][curredit]['color']), 2)
        lcd.lcd_display_string("Background: #%02x%02x%02x" % tuple(obj['colors'][curredit]['background']), 3)
        lcd.lcd_display_string(("Duration  :  %d" % obj['colors'][curredit]['duration']) if obj['colors'][curredit]['duration'] else "Duration  :", 4)
        setcursor(*cursorpos)
    

    ### CONFIRM MODE ###
    elif mode == "conf":
        if name == "esc" or name == "enter":
            mode = confcallback[1]
            #lcd.lcd_clear()
            #lcd.lcd_display_string(header, 1)
            #lcd.lcd_display_string(">", 2)
            if name == "enter" and confcallback is not None: confcallback[0]()
            write()
    

    ### NEW OBJECT MODE ###
    elif mode == "newobj":
        print("Creating new object")
        
        if name == "backspace":
            cmd = cmd[:-1]
        elif key is not None and len(key) == 1 and not keyboard.is_pressed("ctrl"):
            cmd += key
        elif name == 'enter' and cmd in ['phrase', 'image', 'animation']:
            new = {"type": cmd}
            if cmd == "phrase":
                new.update({
                    "phrase": "",
                    "step": 1,
                    "speed": 10,
                    "offset": 0,
                    "colors": [
                        {"color": [128, 128, 128], "background": [0, 0, 0], "duration": 1}
                    ]
                })
            elif cmd == "image":
                new.update({
                    "path": "",
                    "startoffset": 0,
                    "time": 1000
                })
            elif cmd == "animation":
                new.update({
                    "step": 0,
                    "start": 0,
                    "iterations": 0,
                    "frames": []
                })
            cont['objects'].insert(currobjnum, new)
            mode = ""
            cmd = ""
            disp(True)
            obj = cont['objects'][currobjnum]
            write()
                    
            
        print("writing")        
        lcd.lcd_clear()
        lcd.lcd_display_string(header, 1)
        lcd.lcd_display_string("Enter type: ", 2)
        lcd.lcd_display_string(cmd, 3)
        
        
    ### OBJECT LIST MODE ###
    elif mode == "olist":
        if name == "right": 
            currobjnum = (currobjnum + 1) % len(cont['objects'])
            obj = cont['objects'][currobjnum]
        elif name == "left": 
            currobjnum = (currobjnum - 1) % len(cont['objects'])
            obj = cont['objects'][currobjnum]
        elif key in ["a", "i"] and keyboard.is_pressed("ctrl"):
            mode = "newobj"
            currobjnum = len(cont['objects']) if key == "a" else currobjnum
            header = "Editing object "+str(currobjnum)
            cursorpos = [2, 0]
            write()
            return
        elif name == "enter":
            print("enter pressed", obj)
            if obj is None:
                obj = cont['objects'][currobjnum]
            else:
                # enter the current object, currobjnum and obj are already set
                mode = ""
                header = "Editing object "+str(currobjnum)
                disp(True)
                return
        elif name == "  ": pass
        else: return

        print(currobjnum, obj)

        lcd.lcd_clear()
        lcd.lcd_display_string("Index : "+str(currobjnum), 1)
        lcd.lcd_display_string("Type  : "+obj['type'], 2)
        if obj['type'] == 'phrase':
            lcd.lcd_display_string(("Phrase: "+obj['phrase'])[:20], 3)
            lcd.lcd_display_string("Step  : "+str(obj['step']), 4)
        elif obj['type'] == 'image':
            lcd.lcd_display_string(("Path  : "+obj['path'])[:20], 3)
            lcd.lcd_display_string("Offset: "+str(obj['startoffset']), 4)
        elif obj['type'] == 'animation':
            lcd.lcd_display_string(("Descr.: "+obj.get('descr', '--'))[:20], 3)
            lcd.lcd_display_string("#iter.: "+str(obj["iterations"]), 4)

    
    elif mode == "prompt": pass #TODO

write()

def save():
    print("Saving")
    with open("structure_ctest.json", "w") as f: json.dump(cont, f, indent=2)

def showip():
    global mode, displayingIP
    print("showing ip")
    ip = subprocess.check_output(["hostname", "-I"]).decode()
    displayingIP = True
    lcd.lcd_clear()
    lcd.lcd_display_string("My IP address is", 1)
    lcd.lcd_display_string(ip, 2)

def _reload():
    global reload_callback
    save()
    if reload_callback is not None:
        reload_callback()

keyboard.on_press(write)
keyboard.add_hotkey("ctrl+s", save)
keyboard.add_hotkey("alt+i", showip)
keyboard.add_hotkey("ctrl+r", _reload)

if __name__ == "__main__":
    keyboard.wait()

