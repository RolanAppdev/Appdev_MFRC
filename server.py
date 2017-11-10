#!/usr/bin/env python
import socket
import sys
from threading import *
import time

HOST = '192.168.3.82'
PORT = 8888

web_clients = []

socket_alive = True

def kill_socket(socket):
    socket.close()
    print ("socket closed")

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print 'Socket created.'

s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
i = 0
while i < 10:
    try:
        s.bind((HOST, PORT))
    except:
        time.sleep(1)
        i = i + 1

class client(Thread):
	def __init__(self, socket, address):
		Thread.__init__(self)
		self.sock = socket
		self.addr = address
		self.start()

	def run(self):
		#print('Sending boiiii')
		#self.sock.send("boi")
		#print('boi sended')
		msg = self.sock.recv(1)
		print(msg)
		if msg == '0':
			print('web client connected')
			web_clients.append(self.sock)
		else:
			for web_client in web_clients:
				web_client.send('boii')
			del web_clients[:]

s.listen(5)
print 'Started listening'
while socket_alive:
    try:
        clientsocket, address = s.accept()
	print 'Connected with ' + address[0] + ':' + str(address[1])
	client(clientsocket, address)
    except KeyboardInterrupt:
        kill_socket(s)
        socket_alive = False
