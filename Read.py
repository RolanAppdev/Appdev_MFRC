#!/usr/bin/env python -u
# -*- coding: utf8 -*-
import RPi.GPIO as GPIO
import MFRC522
import signal
import time
import subprocess
import sys
import socket
from neopixel import *
from google_script import GoogleCalendar

#Lights must be passed as a list of pins.
#Input is inverted.
#Pin 3 is lights red, pin 5 lights yellow and pin 7 light green.
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

# Capture SIGINT for cleanup when the script is aborted
def end_read(signal,frame):
    global continue_reading, Buzzer
    print "Ctrl+C captured, ending read."
    continue_reading = False
    GPIO.cleanup()
    Buzzer._cleanup()

def send_to_socket():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('192.168.3.82', 8888))
    s.send('1')
    s.close()

#Function to put on the buzzer for a couple of seconds.
def buzzer_on(Buzzer, seconds):
    t_end = time.time() + seconds
    while time.time() < t_end:
        Buzzer.show()

def error_handler(errorNumber):
    if(errorNumber == -1 or errorNumber == -2):
        blink(0.25, 4, (3, 5))
    if(errorNumber == -3):
        blink(0.25, 4, (5))
    if(errorNumber == -4 or errorNumber == -5):
        blink(0.2, 2, (3))
        buzzer_on(Buzzer, 0.5)
        blink(0.2, 2, (3))
    switch = {
        -1: "Please run write first",
        -2: "Code could not be found, please write data to the card",
        -3: "Canceled connection to Google server",
        -4: "You've already clocked in/out",
        -5: "Authentication error",
        -6: "Calendar event could not be set, made a mistake in id?"
        }
    return switch.get(errorNumber, "General error")

#Check the total amount of python processes running.
procs = subprocess.check_output(['ps', 'uaxw']).splitlines()
pyt_procs = [proc for proc in procs if any(s in proc for s in ('Read', 'Write'))]
count = len(pyt_procs)
if count > 3:
    blink(0.5, 2, (3))
    GPIO.cleanup()
    sys.exit()

continue_reading = True
path = "/var/www/html/data/UserData.json"
#Initialise the GPIO pins for the leds, put the leds off.
Buzzer = Adafruit_NeoPixel(1, 18, 4000, 5, False, 100)
Buzzer.begin()
toggle_lights(0, (3, 5, 7))
# Hook the SIGINT
signal.signal(signal.SIGINT, end_read)
# Create an object of the class MFRC522
MIFAREReader = MFRC522.MFRC522()
# This loop keeps checking for chips. If one is near it will get the UID and authenticate
while continue_reading:
    #Put on green light if scanning is on.
    if(GPIO.input(7) == 1):
        toggle_lights(1, (7))
    (status,TagType) = MIFAREReader.MFRC522_Request(MIFAREReader.PICC_REQIDL)
    # If a card is found
    if status == MIFAREReader.MI_OK:
        # Get the UID of the card
        (status,uid) = MIFAREReader.MFRC522_Anticoll()
    # If we have the UID, continue
    if status == MIFAREReader.MI_OK:
        # This is the default key for authentication
        key = [0xFF,0xFF,0xFF,0xFF,0xFF,0xFF]
        # Select the scanned tag
        MIFAREReader.MFRC522_SelectTag(uid)
        # Authenticate
        status = MIFAREReader.MFRC522_Auth(MIFAREReader.PICC_AUTHENT1A, 8, key, uid)
        # Check if authenticated
        if status == MIFAREReader.MI_OK:
            #Create a new google agenda object, send the UID
            gCal = GoogleCalendar(MIFAREReader.MFRC522_Read(8), 0)
            #Make a new event in the calendar
            checkSucces = gCal.set_event()
            #gCal has its own error handler, check if an error has occured
            if checkSucces == 0:
		try:
                    send_to_socket()
                except:
                    blink(0.2, 6, (5))
                    subprocess.call(['sudo', '-b', 'python', '/home/pi/Desktop/MFRC522-python/server.py'])
                #Stop reading for a few seconds
                print("Succesfully made calendar event.")
                MIFAREReader.MFRC522_StopCrypto1()
                buzzer_on(Buzzer, 0.1)
                blink(0.1, 1, (3, 5))
                buzzer_on(Buzzer, 0.1)
                blink(0.1, 1, (3, 5))
                time.sleep(1.15)
            else:
                print(checkSucces)
                error = error_handler(checkSucces)
                print(error)
                MIFAREReader.MFRC522_StopCrypto1()
                time.sleep(1)
        else:
            error = error_handler(-5)
            print (error)
