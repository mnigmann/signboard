import tkinter
import json
from PIL import Image, ImageTk

width, height = 318, 238

tk = tkinter.Tk()
tk.geometry("{}x{}".format(width, height))

canvas = tkinter.Canvas(tk, height=height, background="black", scrollregion=(0,0,width,500))

vbar = tkinter.Scrollbar(tk, orient=tkinter.VERTICAL)
vbar.pack(side=tkinter.RIGHT, fill=tkinter.Y)
vbar.config(command=canvas.yview)
print(vbar.cget("width"))
cwidth = width - int(vbar.cget("width"))-3

canvas.config(yscrollcommand=vbar.set)
canvas.config(width=cwidth)

with open("structure.json") as f:
    struc = json.load(f)
    obj = struc['objects']

canvas.config(scrollregion=(0,0,cwidth,len(obj)*100))
canvas.pack()



currDisp = []
currEntry = ""
currProp = None
pageInfo = {}

def save():
    with open("structure.json", "w") as f:
        json.dump(struc, f, indent=2)

def in_rect(coords, x, y):
    return coords[0] < x < coords[2] and coords[1] < y < coords[3]

def text_with_outline(x, y, anchor, text, fill, border, background="#000000", font=("Ubuntu Mono", 12)):
    t = canvas.create_text(x, y, anchor=anchor, text=text, fill=fill, font=font)
    b = canvas.create_rectangle(canvas.bbox(t), fill=background, outline=border)
    canvas.tag_lower(b, t)
    return t, b

def load_page(disp):
    if disp == []:
        canvas.config(scrollregion=(0, 0, cwidth, 100*len(obj)))
        for i, curr in enumerate(obj):
            canvas.create_line(0,(i+1)*100-1, cwidth, (i+1)*100-1, fill="white")
            canvas.create_text(10, 10+i*100, anchor=tkinter.NW, text="Type:", fill="white")
            canvas.create_text(80, 10+i*100, anchor=tkinter.NW, text=curr['type'], fill="white")
            if curr['type'] == 'phrase':
                canvas.create_text(10, 30+i*100, anchor=tkinter.NW, text='Contents: ', fill='white')
                #t = canvas.create_text(80, 30+i*100, anchor=tkinter.NW, text=curr['phrase'].upper(), fill=l2c(curr['color']))
                #b = canvas.create_rectangle(canvas.bbox(t), fill=l2c(curr['background']))
                #canvas.tag_lower(b, t)
                text_with_outline(80, 30+i*100, tkinter.NW, curr['phrase'].upper(), l2c(curr['color']), "black", l2c(curr['background']))
            elif curr['type'] == 'image':
                print(i, curr, "is an image")
                img = Image.open("images/"+curr['path'])
                img = img.resize((img.size[0]*5, img.size[1]*5))
                print(img)
                tk.p = p = ImageTk.PhotoImage(img)
                print(p)
                canvas.create_image(0, i*100+99, anchor=tkinter.SW, image=p)
    elif len(disp) == 1:
        idx = disp[0]
        type = canvas.create_text(10, 10, anchor=tkinter.NW, text="Type: ", fill="white")
        canvas.create_text(80, 10, anchor=tkinter.NW, text=obj[idx]['type'], fill="white")
        index = canvas.create_text(10, 30, anchor=tkinter.NW, text="Index: ", fill="white")
        canvas.create_text(80, 30, anchor=tkinter.NW, text=idx, fill="white")
        pageInfo['index'] = index               # todo: finish image path editor and index eitor (remove type editor)
        pageInfo['type'] = type
        if obj[idx]['type'] == 'phrase':
            l = canvas.create_text(10, 50, anchor=tkinter.NW, text='Contents: ', fill='white')
            cont = text_with_outline(80, 50, anchor=tkinter.NW, text=obj[idx]['phrase'].upper(), fill=l2c(obj[idx]['color']), border="black", background=l2c(obj[idx]['background']))
            col = text_with_outline(10, 70, anchor=tkinter.NW, text=l2c(obj[idx]['color']), fill=l2c(obj[idx]['color']), border="white")
            bg = text_with_outline(10, 90, anchor=tkinter.NW, text=l2c(obj[idx]['background']), fill=l2c(obj[idx]['background']), border="white")
            pageInfo['colorbbox'] = canvas.bbox(col[0])
            pageInfo['backgroundbbox'] = canvas.bbox(bg[0])
            pageInfo['color'] = col
            pageInfo['background'] = bg
            pageInfo['cont'] = cont
            pageInfo['contlabel'] = l
            pageInfo['contbbox'] = canvas.bbox(cont[0])
        elif obj[idx]['type'] == 'image':
            print(idx, obj[idx], "is an image")
            pathlabel = canvas.create_text(10, 50, anchor=tkinter.NW, text='Path: ', fill="white")
            path = canvas.create_text(80, 50, anchor=tkinter.NW, text=obj[idx]['path'], fill="white")
            
            img = Image.open("images/" + obj[idx]['path'])
            img = img.resize((img.size[0] * 5, img.size[1] * 5))
            tk.p = p = ImageTk.PhotoImage(img)
            canvas.create_image(0, idx * 100 + 99, anchor=tkinter.SW, image=p)
            
            pageInfo['path'] = path
    if len(disp) >= 1:
        pageInfo['backbutton'] = text_with_outline(0, height, tkinter.SW, "BACK", "white", "white", "black", ("Arial", 14))
        


def l2c(l): return "#"+"".join(map(lambda x: hex(x).replace("x", "")[-2:], l))
def c2l(c): return [int(c[1:3], 16), int(c[3:5], 16), int(c[5:], 16)]

load_page(currDisp)
        

def onclick(evt):
    global currProp, currProp, currEntry, pageInfo
    if currDisp == []:
        if evt.x > 200: return
        y = canvas.yview()
        idx = int((evt.y+y[0]*len(obj)*100)//100)
        print(obj[idx])
        currDisp.append(idx)
        
        canvas.config(scrollregion=(0,0,cwidth,height))
        canvas.delete('all')
        load_page(currDisp)
    if len(currDisp) == 1:
        idx = currDisp[0]
        curr = obj[idx]
        if curr['type'] == 'phrase':
            print(pageInfo)
            if in_rect(pageInfo['colorbbox'], evt.x, evt.y):
                currProp = 'color'
                currEntry = l2c(curr[currProp])
                canvas.itemconfig(pageInfo[currProp][1], outline="blue")
            elif in_rect(pageInfo['backgroundbbox'], evt.x, evt.y):
                currProp = 'background'
                currEntry = l2c(curr[currProp])
                canvas.itemconfig(pageInfo[currProp][1], outline="blue")
            elif in_rect(pageInfo['contbbox'], evt.x, evt.y):
                currProp = 'cont'
                currEntry = curr['phrase'].upper()
                canvas.itemconfig(pageInfo['contlabel'], fill='blue')
    if len(currDisp) >= 1:
        if in_rect(canvas.bbox(pageInfo['backbutton'][0]), evt.x, evt.y):
            currDisp.pop()
            pageInfo = {}
            canvas.delete('all')
            load_page(currDisp)
            

def onkey(evt):
    global currEntry, currProp, currDisp
    print(evt, evt.char)
    if len(currDisp) == 1:
        if currProp=="color" or currProp=="background":
            t = pageInfo[currProp][0]
            if evt.keysym == "BackSpace" and len(currEntry) > 1: currEntry = currEntry[:-1]
            elif evt.keysym == "Return":
                obj[currDisp[0]][currProp] = c2l(currEntry)
                canvas.itemconfig(pageInfo[currProp][1], outline="white")
                save()
                load_page(currDisp)
                currProp = None
            elif evt.char.lower() in "abcdef0123456789" and len(currEntry) <= 6:
                currEntry += evt.char.lower()
            canvas.itemconfig(t, text=currEntry)
            if len(currEntry) == 7:
                canvas.itemconfig(t, fill=currEntry)
        elif currProp == 'cont':
            if evt.keysym == "BackSpace" and len(currEntry) > 0: currEntry = currEntry[:-1]
            elif evt.keysym == "Return":
                obj[currDisp[0]]['phrase'] = currEntry.lower()
                canvas.itemconfig(pageInfo['contlabel'], fill="white")
                save()
                currProp = None
            elif evt.char.lower() in "abcdefghijklmnopqrstuvwxyz":
                currEntry += evt.char.upper()
            canvas.itemconfig(pageInfo['cont'][0], text=currEntry)
    
    
    #TODO finish click detector and actions
    
canvas.bind("<Button-1>", onclick)
canvas.bind_all("<Key>", onkey)

tk.mainloop()
