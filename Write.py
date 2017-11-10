#!/usr/bin/env python
#-*- coding: utf8 -*-

import RPi.GPIO as GPIO
import MFRC522
import signal
import json
import sys
import errno
import subprocess
import time
import socket
import argparse
#from google_script import GoogleCalendar

#Lights must be passed as a list of pins.
#Input is inverted.
#Pin 3 is red, pin 5 yellow and pin 7 green.
GPIO.setmode(GPIO.BOARD)
GPIO.setup((3, 5, 7), GPIO.OUT)

def blink(seconds, times, lights):
    for _ in range(times):
        GPIO.output(lights, 0)
        time.sleep(seconds)
        GPIO.output(lights, 1)
        time.sleep(seconds)

def toggle_lights(toggle, lights):
    if toggle == 1:
        GPIO.output(lights, 0)
    elif toggle == 0:
        GPIO.output(lights, 1)

toggle_lights(0, (3, 5, 7))
#Initial checks to stop the script at initialisation.
#Check if there is already a read or write running.
procs = subprocess.check_output(['ps', 'uaxw']).splitlines()
pyt_procs = [proc for proc in procs if any(s in proc for s in ('Read', 'Write'))]
count = len(pyt_procs)
if count > 3:
    blink(0.5, 2, (3))
    GPIO.cleanup()
    sys.exit()

#Check if the minimum amount of arguments are given.
if len(sys.argv) != 4:
    blink(0.5, 2, (3))
    GPIO.cleanup()
    sys.exit()
 
#Capture SIGINT for cleanup when the script is aborted.
def end_read(signal,frame):
    global continue_reading
    print ("Ctrl+C captured, ending read.")
    continue_reading = False
    GPIO.cleanup()

#Function to clean GPIO pins and stop reading without keyboardinterrupt.
def stop_read(MIFAREReader):
    global continue_reading
    MIFAREReader.MFRC522_StopCrypto1()
    continue_reading = False
    GPIO.cleanup()

def send_to_socket():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('192.168.3.82', 8888))
    s.send('1')
    s.close()

continue_reading = True
path = "/var/www/html/data/UserData.json"

try:
    with open(path) as JSONFile:
        JSONData = json.load(JSONFile)
except(IOError, ValueError):
    subprocess.call(['sudo', 'chmod', '-R', '777', '/var/www/html'])
    with open(path, 'w') as JSONFile:
        JSONFile.write("[]")
        count = -1
        JSONData = []

if count != -1:
    count = len(JSONData) - 1
if count >= 0:
    if JSONData[count]['cardData'][0] >= 255:
        numberOne = 255
    	numberTwo = JSONData[count]['cardData'][8] + 1
    else:
    	numberOne = JSONData[count]['cardData'][0] + 1
    	numberTwo = 0
else:
    numberOne = 0
    numberTwo = 0

data = []

data.extend([numberOne] * 8)
data.extend([numberTwo] * 8)
#Hook the SIGINT.
signal.signal(signal.SIGINT, end_read)
#Create an object of the class MFRC522.
MIFAREReader = MFRC522.MFRC522()
if(GPIO.input(5) == 1):
    toggle_lights(1, (5))
while continue_reading:
    #Scan for cards.
    (status,TagType) = MIFAREReader.MFRC522_Request(MIFAREReader.PICC_REQIDL)
    #If a card is found.
    if status == MIFAREReader.MI_OK:
        print ("Card detected")
    #Get the UID of the card.
    (status,uid) = MIFAREReader.MFRC522_Anticoll()
    #If we have the UID, continue.
    if status == MIFAREReader.MI_OK:
        #This is the default key for authentication.
        key = [0xFF,0xFF,0xFF,0xFF,0xFF,0xFF]
        #Select the scanned tag.
        MIFAREReader.MFRC522_SelectTag(uid)
        #Authenticate.
        status = MIFAREReader.MFRC522_Auth(MIFAREReader.PICC_AUTHENT1A, 8, key, uid)
        #Check if authenticated.
        if status == MIFAREReader.MI_OK:
            #Test the calendar id
            #gCal = GoogleCalendar(0, "Test")
            #result = gCal.test_calendar()
            result = 0
            if result == 0:
                #MIFAREReader has it's own error handling if write failed.
                checkWrite = MIFAREReader.MFRC522_Write(8, data)
                if checkWrite == -1:
                    blink(0.5, 2, (3, 7))
                    stop_read(MIFAREReader)
                    sys.exit()
                #Socket is not needed to succesfully write data to the card, it only exists to update the website
                with open(path, "w") as JSONFile:
                    JSONDict = {'name' : sys.argv[1], 'surname' : sys.argv[2], 'cardData' : data, 'check' : 0, 'clockTime' : 0, 'calendar_id': sys.argv[3]}
                    JSONData.append(JSONDict)
                    json.dump(JSONData, JSONFile, indent=2)
                blink(0.25, 4, (3, 5, 7))
                i = 0
                while i != 1:
                    try:
                        send_to_socket()
                        i = 1
                    except:
                        subprocess.call(['sudo', 'python', '/home/pi/Desktop/MFRC522-python/server.py'])
                stop_read(MIFAREReader)
            else:
                #CalendarId not found, return result to php
                print ("Nope")
                blink(0.5, 4, (3))
                stop_read(MIFAREReader)
        else:
            blink(0.5, 2, (3, 7))
            print ("Authentication error")


