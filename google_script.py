from __future__ import print_function
import httplib2
import os
import datetime
import time
import json
import urllib
import subprocess

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
SCOPES = 'https://www.googleapis.com/auth/calendar'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Google Calendar API Python Quickstart'

class GoogleCalendar:
    def __init__(self, cardId, calendar_id):
        self.calendar_id = calendar_id
        self.cardId = cardId
        self.path = "/var/www/html/data/UserData.json"
        self.syncpath = "/home/pi/Desktop/Google_Events.json"

    def initialise_connection(self):
        #Check if the google agenda user could be authorized
        credentials = self.get_credentials()
        http = credentials.authorize(httplib2.Http())
        #Try to connect to the Google server.
        try:
            service = discovery.build('calendar', 'v3', http=http)
            return service
        except httplib2.ServerNotFoundError:
            return 1

    #Gets credentials from Google Account.
    #These credentials are generated from  a JSON file.
    #https://developers.google.com/google-apps/calendar/quickstart/python
    def get_credentials(self):
        credential_dir = os.path.join("/home/pi/Desktop/MFRC522-python/.credentials")
        if not os.path.exists(credential_dir):
            os.makedirs(credential_dir)
        credential_path = os.path.join(credential_dir,
                                       'calendar-python-quickstart.json')
        store = Storage(credential_path)
        credentials = store.get()

        if not credentials or credentials.invalid:
            flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
            flow.user_agent = APPLICATION_NAME
            if flags:
                credentials = tools.run_flow(flow, store, flags)
            print('Storing credentials to ' + credential_path)
        return credentials

    def test_calendar(self):
	service = self.initialise_connection()
        dateTimeStart = datetime.datetime.today()
        event = {
          'summary': "Connected card to pi",
          'start': {
            'dateTime': dateTimeStart.strftime("%Y-%m-%dT%H:%M:%S"),
            'timeZone': 'Europe/Amsterdam',
          },
          'end': {
            'dateTime': dateTimeStart.strftime("%Y-%m-%dT%H:%M:%S"),
            'timeZone': 'Europe/Amsterdam',
          },
        }

        try:
            service.events().insert(calendarId=self.calendar_id, body=event).execute()
            return 0
        except:
            return "Failed" 
#Synchronise events that couldn't be written
    def synchronise_events(self, service):
        if os.path.isfile(self.syncpath):
            with open(self.syncpath) as eventFile:
                eventData = json.load(eventFile)
            for node in eventData:
                calendar_id = node['calendar_id']
                del node['calendar_id']
                service.events().insert(calendarId=calendar_id, body=node).execute()
            os.remove(self.syncpath)

    #Creates an event if user scans card.
    def set_event(self):
        service = self.initialise_connection()
        #Get the data from the JSON file and check if the current card matches a code
        try:
            with open(self.path) as JSONFile:
                JSONData = json.load(JSONFile);
                cardIdIndex = next(i for (i, d) in enumerate(JSONData) if d["cardData"] == self.cardId)
        except IOError:
            return -1
        except StopIteration:
            return -2

        #Get the name and surname of the found user.
        name = urllib.unquote(JSONData[cardIdIndex]['name']).decode('utf8') + " " + urllib.unquote(JSONData[cardIdIndex]['surname']).decode('utf8')

        #Get the current time and endtime, this creates a single timeless event
        dateTimeStart = datetime.datetime.today()
        dateTimeEnd = dateTimeStart + datetime.timedelta(seconds = 1)

        if JSONData[cardIdIndex]['clockTime'] != 0:
            dateTimeHalfHour = datetime.datetime.strptime(JSONData[cardIdIndex]['clockTime'],
                                                          "%Y-%m-%dT%H:%M:%S") + datetime.timedelta(minutes=30)
            dateTimeOneMinute = datetime.datetime.strptime(JSONData[cardIdIndex]['clockTime'],
                                                           "%Y-%m-%dT%H:%M:%S") + datetime.timedelta(minutes=1)
        else:
            dateTimeHalfHour = dateTimeStart - datetime.timedelta(minutes=1)
            dateTimeOneMinute = dateTimeStart - datetime.timedelta(minutes=1)

        #check if user is already checked in and if a minute has passed since check out or it's his first time.
        if JSONData[cardIdIndex]['check'] == 0 and (dateTimeStart > dateTimeOneMinute or JSONData[cardIdIndex]['clockTime'] == 0):
            JSONData[cardIdIndex]['check'] = 1
            summary = name + '- ingeklokt'
        elif JSONData[cardIdIndex]['check'] == 1 and dateTimeStart > dateTimeHalfHour:
            JSONData[cardIdIndex]['check'] = 0
            summary = name + '- uitgeklokt'
        else:
            return -4

        JSONData[cardIdIndex]['clockTime'] = dateTimeStart.strftime("%Y-%m-%dT%H:%M:%S")
        with open(self.path, "w") as JSONFile:
            json.dump(JSONData, JSONFile, indent=2)
        event = {
          'summary': summary,
          'start': {
            'dateTime': dateTimeStart.strftime("%Y-%m-%dT%H:%M:%S"),
            'timeZone': 'Europe/Amsterdam',
          },
          'end': {
            'dateTime': dateTimeEnd.strftime("%Y-%m-%dT%H:%M:%S"),
            'timeZone': 'Europe/Amsterdam',
          },
        }
        #If a connection is found write the data to the calendar, else save the data in a file.
        if service != 0:
            self.synchronise_events(service)
            event = service.events().insert(calendarId=JSONData[cardIdIndex]['calendar_id'], body=event).execute()
            return 0
        elif service == 1:
            try:
                with open(self.syncpath) as eventFile:
                    eventData = json.load(eventFile)
                    event['calendar_id'] = JSONData[cardIdIndex]['calendar_id']
                    eventData.append(event)
                with open(self.syncpath, 'w') as eventFile:
                    json.dump(eventData, eventFile, indent=2)
                return -3
            #File doesn't exist
            except:
                subprocess.call(['sudo', 'chmod', '777', '/home/pi/Desktop'])
                with open(self.syncpath, 'w') as eventFile:
                    event['calendar_id'] = JSONData[cardIdIndex]['calendar_id']
                    a = [event]
                    json.dump(a, eventFile, indent=2)
                subprocess.call(['sudo', 'chmod', '777', '/home/pi/Desktop/Google_Events.json'])
                return -3
