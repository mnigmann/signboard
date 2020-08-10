"""#!/usr/bin/python
import spidev
#Andybiker 23/09/2014
#test to write to 10 WS8212b Leds attached to MOSI pin
def buf(r,g,b):
#takes in R,G,B values, outputs SPI word
        word=[]
        for i in range (7,-1,-1):
                if (g & (1<<i)):
                        word+=[248]
                else:
                        word+=[224]
        for i in range (7,-1,-1):
                if (r & (1<<i)):
                        word+=[248]
                else:
                        word+=[224]
        for i in range (7,-1,-1):
                if (b & (1<<i)):
                        word+=[248]
                else:
                        word+=[224]
        return word
#end def

# MAIN

spi = spidev.SpiDev()
spi.open(0,0)
spi.max_speed_hz = 7812500
r=0
g=0
b=0
word=[]
buffer=[]
#this lights the 10 leds dimly Yellow,cyan.magenta,red,green,blue,
#yellow,cyan,magenta,white
#the values are (0-255 RED ,0-255 GREEN ,0-255 BLUE)
buffer+=buf(10,10,0)
buffer+=buf(0,10,10)
buffer+=buf(10,0,10)
buffer+=buf(10,0,0)
buffer+=buf(0,10,0)
buffer+=buf(0,0,10)
buffer+=buf(10,10,0)
buffer+=buf(0,10,10)
buffer+=buf(10,0,10)
buffer+=buf(10,1,10)
dummy=spi.xfer(buffer)"""


import sys
import board
import neopixel
import time


print(sys.argv)

strip = neopixel.NeoPixel(board.D18, 300, auto_write=False, pixel_order=neopixel.GRB)

strip.fill(list(map(int, sys.argv[1:])))
strip.show()
time.sleep(3)
strip.fill((0,0,0))
strip.show()