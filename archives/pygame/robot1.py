import socket
import sys
import selectors
import types
import pygame
import time
import math
import random

HOST = 'localhost'    # The remote host
PORT = 50007          # The same port as used by the server
QUANTA = 10           # frames per second

sel = selectors.DefaultSelector()
messages = [b""]

class bot():
  rindex = -1
  x = -1
  y = -1
  health = -1
  mHeat = -1
  speedgoal = -1
  speed = -1
  dir = -1
  dsp = -1
  scandir = -1
  dirgoal = -1
  scanres = -1
  scanResponse = 0
  fireResponse = 0
  sock = ""
  sleepUntil = time.time()

  def __init__(self):
    self.dir = -1
    print("Initialized")

  def init(self):
    self.dirgoal = 0
    self.scandir = 0
    self.speedgoal = 100

  def check_sleep(self):
    while time.time() < self.sleepUntil:
      events = sel.select(timeout=-10)
      for key, mask in events:
        service_connection(key, mask)
      time.sleep(.01)

  def send_message(self,reply):
    #print("sending: ", reply)
    self.sock.send(reply.encode("utf-8"))

  def scan(self, dir, res):
    self.scandir = dir
    self.scanres = res
    self.scanResponse = -1
    reply = "%d;scan;%d;%d" % (self.rindex, dir, res)
    #print("Scanning: ", reply)
    self.send_message(reply)
    self.sleepUntil = time.time() + .2
    self.check_sleep()
    return self.scanResponse

  def register(self):
    print("Set place message")

  def drive(self, dir, speed):
    self.check_sleep()
    #print("Dir",dir, "speed",speed)
    if self.rindex != -1:
      reply = "%d;drive;%d;%d" % (self.rindex, dir, speed)
      self.send_message(reply)
      self.dirgoal = dir
      self.sleepUntil = time.time() + .1

  def process_move(self):
    self.check_sleep()
    # See if we need to turn
    print("1")
    print(int(self.x), int(self.y), int(self.dirgoal))
    change = False
    if (self.x > 900 and (self.dirgoal > 270 or self.dirgoal < 90)):
      self.dirgoal = random.randint(90, 270)
      print("east x", self.x, "y", self.y, self.dirgoal)
      change = True
    if (self.x < 100 and (self.dirgoal < 270 and self.dirgoal > 90)):
      self.dirgoal = (self.dirgoal + 180) % 360
      print("west x", self.x, "y", self.y, self.dirgoal)
      change = True
    if (self.y > 900 and (self.dirgoal > 0 and self.dirgoal < 180)):
      self.dirgoal = random.randint(90, 180)
      print("north x", self.x, "y", self.y, self.dirgoal)
      change = True
    if (self.y < 100 and (self.dirgoal > 180 and self.dirgoal < 360)):
      self.dirgoal = random.randint(0, 90)
      print("south x", self.x, "y", self.y, self.dirgoal)
      change = True
    print("2")

    # If we're turning, set new scandir and slow down
    if change == True:
      self.scandir = self.dirgoal
      self.speedgoal = 15
      #print("Turn")
      self.drive(self.dirgoal, self.speedgoal)
    # If we're not turning, go as fast as we can
    else:
      if (self.speed < 100):
        #print("Accel")
        self.drive(self.dirgoal, 100)
    print("3")

    # Scan and increment scan direction
    result = self.scan(self.scandir, 10)
    if result != 0:
      #print("Scan Response: ", result)
      if result > 0:
        self.fire(self.scandir, result)
    self.scandir = (self.scandir + 10) % 360

  def fire(self, dir, range):
    self.check_sleep()
    reply = "%d;fire;%d;%d" % (self.rindex, dir, range)
    print(reply)
    self.send_message(reply)
    self.sleepUntil = time.time() + .1
    self.check_sleep()
    
  def process_response(self, response):
    r = response.decode("utf-8")
    #print("Messages: ", r)
    msgs = r.split(':')
    for msg in msgs:
      if msg == "":
        return
      rs = msg.split(";")
      #print(f"Processing {msg}")
      # 'place' response: 0;place;index
      if rs[1] == "place":
        self.rindex = int(rs[2])
        self.x = int(rs[3])
        self.y = int(rs[4])
        self.dir = int(rs[5])
        self.init()
        print(f"We are # {self.rindex }")
        return
      if rs[1] == "scan":
        self.scanResponse = int(rs[2])
        #break
      if rs[1] == "fire":
        self.fireResponse = int(rs[2])
        #break
      if rs[1] == "status":
        self.x = int(rs[2])
        self.y = int(rs[3])
        self.health = int(rs[4])
        self.mHeat = int(rs[5])
        self.speed = int(rs[6])
        self.dir = int(rs[7])
        self.dsp = int(rs[8])
        #print(f"x={self.x} y={self.y} dir={self.dir} speed={self.speed}")
        #break
      #error if not ours
      if int(rs[0]) != self.rindex:
        print(f"Wrong client: {r}")
        #break
      if rs[1] == "ping":
        self.ping(rs[2])
        #break

  def ping(self, enemy):
    print (f"Pinged by {enemy}")

def start_connections(HOST, PORT, num_conns):
  global mybot
  server_addr = (HOST, PORT)
  #for i in range(0, num_conns):
  #connid = i + 1
  connid=0
  print(f"Starting connection {connid} to {server_addr}")
  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  sock.setblocking(False)
  sock.connect_ex(server_addr)
  events = selectors.EVENT_READ | selectors.EVENT_WRITE
  data = types.SimpleNamespace(
    connid=connid,
    msg_total=sum(len(m) for m in messages),
    recv_total=0,
    messages=messages.copy(),
    outb=b"",
  )
  sel.register(sock, events, data=data)
  mybot.sock = sock
  reply = "0;place"
  mybot.send_message(reply)
  print("Connected")

def service_connection(key, mask):
  global mybot
  sock = key.fileobj
  data = key.data
  if mask & selectors.EVENT_READ:
    recv_data = sock.recv(1024)  # Should be ready to read
    if recv_data:
      #print(f"Received {recv_data!r} from connection {data.connid}")
      data.recv_total += len(recv_data)
      mybot.process_response(recv_data)
    if not recv_data or data.recv_total == data.msg_total:
      print(f"Closing connection {data.connid}")
      sel.unregister(sock)
      sock.close()
    recv_data = ""

mybot = bot()

def main():
  start_connections(HOST, int(PORT), 1)

  #try:
  while True:
    # don't block
    events = sel.select(timeout=-10)
    for key, mask in events:
      service_connection(key, mask)
    if(mybot.rindex != -1):
      mybot.process_move()
  #except KeyboardInterrupt:
  #  print("Caught keyboard interrupt, exiting")
  #finally:
  #  sel.close()
  #  sys.exit()

main()