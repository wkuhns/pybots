import time
import socket
import selectors
import types
import random
import sys
import os
import subprocess
#import warbot_lib.serverRobot as serverRobot
import serverRobot

import tkinter as tk
from tkinter import ttk
from tkinter import *

# For recording user marks in arena
marks = []

# process one or more incoming messages from client robots
def service_connection(key, mask):
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(1024)  # Should be ready to read
        if recv_data:
            recv_data = recv_data.decode("utf-8")
            # print(f"Command {data.outb!r} from {data.addr}")
            msgs = recv_data.split("|")
            for msg in msgs:
                if len(msg) < 3:
                    break
                cmds = msg.split(";")
                botindex = int(cmds[0]) - 1
                botcmd = cmds[1]
                if botcmd == "post":
                    botparm1 = cmds[2]
                    robots[botindex].post(botparm1)
                if botcmd == "scan":
                    botparm1 = cmds[2]
                    botparm2 = cmds[3]
                    robots[botindex].scan(float(botparm1), float(botparm2))
                if botcmd == "place":
                    botindex = place_bot(sock)
                    recv_data = ""
                    data.outb = ""
                    return
                if botcmd == "drive":
                    # print(f"Drive #{botindex}: {cmds[2]} {cmds[3]}")
                    botparm1 = cmds[2]
                    botparm2 = cmds[3]
                    robots[botindex].drive(int(botparm1), int(botparm2))
                    data.outb = ""
                    recv_data = ""
                    return
                if botcmd == "fire":
                    botparm1 = cmds[2]
                    botparm2 = cmds[3]
                    robots[botindex].fire(int(botparm1), int(botparm2))
                    data.outb = ""
                    recv_data = ""
                    return
                if botcmd == "set_name":
                    robots[botindex].name = cmds[2]
                    robots[botindex].panel.set_name(cmds[2])
                if botcmd == "setArmor":
                    if arena.status == 'S':
                        robots[botindex].set_armor(int(cmds[2]))
                if botcmd == "setScan":
                    if arena.status == 'S':
                        robots[botindex].scan_accuracy = int(cmds[2])
                if botcmd == "pause" and arena.debug == True:
                    arena.status = "P"
                    post_message("Paused")
                    for r in robots:
                        if r.status == "A":
                            r.pause()
                    post_message(f"Paused by {cmds[2]}")
                if botcmd == "run":
                    start_btn_click()
                    post_message(f"Started by {cmds[2]}")
                if botcmd == "mark" and arena.debug == True:
                    x = int(cmds[2])
                    y = int(cmds[3])    
                    marks.append( (botindex, arena.line(x-10, y, x+10, y, fill=cmds[4])))
                    marks.append( (botindex, arena.line(x, y-10, x, y+10, fill=cmds[4])))
                if botcmd == "clear":
                    #print("Marks is ", len(marks))
                    for i in range (len(marks)-1, -1, -1):
                        #print("Mark", i)
                        m = marks[i]
                        if m[0] == botindex:
                            arena.delete(m[1])
                            del marks[i]
                if botcmd == "whereis" and arena.debug == True:
                    reply = "%d;whereis;%d;%d" % (botindex+1, robots[int(cmds[2])-1].x, robots[int(cmds[2])-1].y)
                    robots[botindex].send_message(reply)
                if botcmd == "bheat" and arena.debug == True:
                    reply = "%d;bheat;%d" % (botindex, robots[botindex].bHeat)
                    robots[botindex].send_message(reply)
                if botcmd == "setDirection":
                    botparm1 = cmds[2]
                    robots[botindex].setSpeedGoal(int(botparm1))
                    # reply = "%d;%d" % (robots[botindex].x, 4)
                    data.outb = ""
                    recv_data = ""
                    return
                if botcmd == "set_autopilot":
                    robots[botindex].autopilot = True
                if botcmd == "set_autoscan":
                    robots[botindex].autoscan = True

        else:
            # Client has closed socket, close our end too
            #print(f"Closing connection to {data.addr}")
            for r in robots:
                if sock == r.sock:
                    print(r.name, r.index, "Has left")
                    remove_bot(r)
            sel.unregister(sock)
            sock.close()
        data.outb = ""

# Handle new incoming connection
def accept_wrapper(sock):
    conn, addr = sock.accept()  # Should be ready to read
    #print(f"Accepted connection from {addr}")
    conn.setblocking(False)
    data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"")
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sel.register(conn, events, data=data)


# Subclass of tkinter.Canvas with positive Y axis and arena scaling
class MyCanvas(tk.Canvas):

    def __init__(self, window, height, width):
        super().__init__(window, height=f'{height}', width=f'{width}')
        self.height = height
        self.width = width
        self.xscale = width / 1000
        self.yscale = height / 1000
        self.starttime = time.time()
        self.gametime = 0
        self.status = "I"  # Initialized, Paused, Running, Finished

    def time():
        return time.time() - self.starttime

    def makebot(self, x, y, color):
        x = x * self.xscale
        y = self.height - y * self.yscale
        return super(MyCanvas, self).create_polygon(x - BOT_SIZE, y - BOT_SIZE, x - BOT_SIZE, y + BOT_SIZE, x + BOT_SIZE,
                                                    y + BOT_SIZE, x + BOT_SIZE, y - BOT_SIZE, fill=color, outline="Black",
                                                    width=1)

    # Move thing by x and y increments
    def move(self, thing, x, y):
        x = x * self.xscale
        y = y * self.yscale
        super(MyCanvas, self).move(thing, x, y * -1)

    def line(self, x1, y1, x2, y2, fill="black", width=1):
        x1 = x1 * self.xscale
        y1 = (1000 - y1) * self.yscale
        x2 = x2 * self.xscale
        y2 = (1000 - y2) * self.yscale
        return super(MyCanvas, self).create_line(x1, y1, x2, y2, fill=f"{fill}", width=f"{width}")

    def circle(self, x, y, r, fill=""):  # center coordinates, radius
        x0 = (x - r) * self.xscale
        y0 = (1000 - y - r) * self.yscale
        x1 = (x + r) * self.xscale
        y1 = (1000 - y + r) * self.yscale
        return super(MyCanvas, self).create_oval(x0, y0, x1, y1, fill=f"{fill}")

    def center(self, cir):
        coords = super(MyCanvas, self).coords(cir)
        x = (coords[0] + coords[2]) / 2 / self.xscale
        y = 1000 - ((coords[1] + coords[3]) / 2 / self.yscale)
        return [x, y]

# Window that frames the arena canvas
def create_frame(width, height):
    window = tk.Tk()
    window.title("Arena")
    window.geometry(f'{width}x{height}')
    return window

# Arena canvas
def create_arena(window, height, width):
    canvas = MyCanvas(window, height, width)
    canvas.configure(bg="Green")
    canvas.pack(expand=False)
    return canvas

# Remove client that has lost communication (presumably crashed)
def remove_bot(r):
    # remove status panel
    del panels[r.index]
    # free up quadrant
    quads[r.q].used = False
    # create new empty status panel
    panels[r.index] = RobotPanel(frame, r.index)
    r.panel = panels[r.index]
    # Clear any artifacts from arena
    r.clear_bomb()
    r.clear_scans()
    arena.delete(r.botIcon)
    if r.shellIcon != 0:
        arena.delete(r.shellIcon)    
        arena.delete(r.tick1)
        arena.delete(r.tick2)
    # Initialiize robot structure for re-use
    r.my_init(r.index, arena, robots, r.index-1)

# Place a new robot in the arena
def place_bot(sock):
    # Make sure there's an empty quadrant
    x = 0
    for q in range(0, 4):
        #print("Quad", q, quads[q].used)
        if quads[q].used == False:
            x = 1

    if x == 0:
        print("Quadrant allocation error. Start over.")
        return 0

    # Pick a random quadrant
    q = random.randint(0, 3)
    while quads[q].used == True:
        q = random.randint(0, 3)
    #print(f"picked {q}")
    quads[q].used = True
    robots[q].used = True

    print(f"placing {q + 1}")
    x = random.randint(0, 300) + quads[q].x
    y = random.randint(0, 300) + quads[q].y

    # Run robot's place() method
    robots[q].place(sock, x, y)
    print("placed")
    # Populate this robot's status panel
    robots[q].panel.populate(robots[q].name)

    return robots[q].index

# Simple class just to get a data structure
class quad:
    def __init__(self):
        self.used = False
        self.x = 0
        self.y = 0

# These set up the four areas where robots will be placed
quads = [quad(), quad(), quad(), quad()]
quads[0].x = 100
quads[0].y = 100
quads[1].x = 100
quads[1].y = 600
quads[2].x = 600
quads[2].y = 100
quads[3].x = 600
quads[3].y = 600

# Create an empty status panel
def make_panel(frame, row):
    recspec = [(2, 2), (STATUS_WIDTH - 2, ARENA_SIZE / 5 - 2)]
    mypanel = tk.Canvas(frame, width=STATUS_WIDTH, height=ARENA_SIZE / 5 - 2, bg="white", bd=1)
    mypanel.grid(column=1, row=row)
    mypanel.create_rectangle(recspec)
    return mypanel

# Each robot gets a status panel. Methods handle update of status boxes etc.
class RobotPanel:
    def __init__(self, frame, index):
        self.botpanel = make_panel(frame, index)
        self.index = index

    def populate(self, name):
        # Label at top

        # Speed display
        Label(self.botpanel, text='Speed', bg='white', font=('arial', 10, 'normal')).place(x=5, y=10)
        self.speed = Entry(self.botpanel)
        self.speed.config(width=4, justify=RIGHT, font='arial 10')
        self.speed.place(x=75, y=10)

        # Direction display
        Label(self.botpanel, text='Direction', bg='white', font=('arial', 10, 'normal')).place(x=5, y=40)
        self.dir = Entry(self.botpanel)
        self.dir.config(width=4, justify=RIGHT, font='arial 10')
        self.dir.place(x=75, y=40)

        # Motor Heat display
        Label(self.botpanel, text='Mtr Heat', bg='white', font=('arial', 10, 'normal')).place(x=5, y=70)
        self.mheat = Entry(self.botpanel)
        self.mheat.config(width=4, justify=RIGHT, font='arial 10')
        self.mheat.place(x=75, y=70)

        # Barrel Heat display
        Label(self.botpanel, text='Barrel', bg='white', font=('arial', 10, 'normal')).place(x=5, y=100)
        self.bheat = Entry(self.botpanel)
        self.bheat.config(width=4, justify=RIGHT, font='arial 10')
        self.bheat.place(x=75, y=100)

        # Health status bar
        Label(self.botpanel, text='Health', bg='white', font=('arial', 10, 'normal')).place(x=5, y=130)
        progessBarOne_style = ttk.Style()
        progessBarOne_style.theme_use('clam')
        progessBarOne_style.configure('progessBarOne.Horizontal.TProgressbar',
                                      foreground='#FF4040', background='#FF4040')

        self.progessBarOne = ttk.Progressbar(self.botpanel, style='progessBarOne.Horizontal.TProgressbar',
                                             orient='horizontal', length=300, mode='determinate', maximum=100,
                                             value=100)
        self.progessBarOne.place(x=75, y=130)

        # Message box
        self.msgBox = Text(self.botpanel, height=5, width=38, font=('Arial', '10'))
        self.msgBox.place(x=115, y=35)

    def set_name(self, name):
        print("Setting name", name)
        self.nameLabel = Label(self.botpanel, text=name, bg=colors[self.index - 1], font=('arial', 12, 'normal')).place(
            x=151, y=3)

    def set_health(self, val):
        self.progessBarOne['value'] = val

    def set_mheat(self, val, cooling):
        self.mheat.delete(0, END)
        sval = "%.0f" % val
        self.mheat.insert(0, sval)
        if cooling:
            self.mheat.config(bg="red")
        else:
            self.mheat.config(bg="white")

    def set_speed(self, val):
        self.speed.delete(0, END)
        sval = "%.0f" % val
        self.speed.insert(0, sval)

    def set_dir(self, val):
        self.dir.delete(0, END)
        sval = "%.0f" % val
        self.dir.insert(0, sval)

    def set_bheat(self, val):
        self.bheat.delete(0, END)
        sval = "%.0f" % val
        self.bheat.insert(0, sval)
        if val > 35:
            self.bheat.config(bg="red")
        else:
            self.bheat.config(bg="white")

def start_btn_click():
    if arena.gametime == 0:
        arena.starttime = time.time()

    # Are we starting or pausing?
    if arena.status == "R":
        arena.status = "P"
        post_message("Paused")
        for r in robots:
            if r.status == "A":
                r.pause()
    else:
        arena.status = "R"
        post_message("Started")
        for r in robots:
            if r.status == "A":
                r.resume()

def debug_btn_click():
    global debug_btn
    arena.debug = True
    post_message("Debug Mode Enabled")
    for r in robots:
        if r.status == "A":
            reply = "%d;debug" % (r.index+1)
            r.send_message(reply)
    debug_btn.configure(bg = "red")

def post_message(msg):
    msg = msg[:50]
    arena.msgBox.insert(END, '\n' + msg)
    arena.msgBox.see(END)

# User has selected a robot from pulldown menu. Launch it.
def launchbot(p):
    fname = f"{clicked.get()}Bot.py"
    subprocess.Popen(["python3", fname])

# **************** Program starts here ***********************

QUANTA = 30
BOT_SIZE = 6
ARENA_SIZE = 800
STATUS_WIDTH = 400
colors = ["dodger blue", "lightgreen", "red", "yellow"]

# Create frame and arena - same size
frame = create_frame(ARENA_SIZE + STATUS_WIDTH + 2, ARENA_SIZE + 2)
arena = create_arena(frame, ARENA_SIZE, ARENA_SIZE)

arena.status = "S"      # Status "S" for Started
arena.debug = False

#Arena goes into left column. Right column will have five status panels
arena.grid(column=0, row=0, rowspan=5)

# Empty status panel list
panels = []

# Create status panel
panel_status = make_panel(frame, 0)
panels.append(panel_status)

# Status panel: Start button
arena.start_btn_text = tk.StringVar()
arena.start_btn = Button(panel_status, textvariable=arena.start_btn_text, bg='white', font=('arial', 10, 'normal'), command=start_btn_click)
arena.start_btn.place(x=10, y=10)
arena.start_btn_text.set("Startz")

debug_btn = Button(panel_status, text='Debug', bg='white', font=('arial', 10, 'normal'), command=debug_btn_click)
debug_btn.place(x=75, y=10)

# Status panel: pause button
#Button(panel_status, text='Pause', bg='white', font=('arial', 12, 'normal'), command=pause_btn_click).place(x=80, y=10)

# Status panel: robot select

# Get a list of available robots in current directory.
# The will have names in the form xxxBot.py
botlist = os.listdir()
diskbots = []
for fname in botlist:
    if fname[-6:] == "Bot.py":
        diskbots.append(fname[:len(fname)-6])

listvar = tk.Variable(value=diskbots)
clicked = StringVar()
clicked.set(diskbots[0])
listbox = tk.OptionMenu(
    panel_status,
    clicked,
    *diskbots,
    command=launchbot
)
listbox.place(x=225, y=10)

# Status panel: game time display
Label(panel_status, text='Game Time', bg='white', font=('arial', 8, 'normal')).place(x=325, y=3)
gTime = Entry(panel_status)
gTime.config(width=4, justify=RIGHT, font='arial 8')
gTime.place(x=350, y=20)

# Status panel: Message box
arena.msgBox = Text(panel_status, height=6, width=53, font=('Arial', '10'))
arena.msgBox.place(x=12, y=50)

# Empty panels for 4 robots
for i in range(1, 5):
    panels.append(RobotPanel(frame, i))

# For communication sockets
sel = selectors.DefaultSelector()

# List of robots
robots = []

# Create robots and link to status panels
for r in range(0,4):
    robots.append(serverRobot.ServerRobot(r + 1, arena, robots, r))
    robots[r].panel = panels[r+1]

def main():

    starttime = time.time()

    HOST = "127.0.0.1"
    PORT = 50007  # Arbitrary non-privileged port

    lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lsock.bind((HOST, PORT))
    lsock.listen()
    print(f"Listening on {(HOST, PORT)}")
    lsock.setblocking(False)
    sel.register(lsock, selectors.EVENT_READ, data=None)

    #try:
    while True:
        # don't block
        events = sel.select(timeout=-10)
        for key, mask in events:
            # listening socket
            if key.data is None:
                accept_wrapper(key.fileobj)
            else:
                service_connection(key, mask)

        # Check if tournament is over
        players = 0
        winner = "none"
        for r in robots:
            if r.status == "A":
                players += 1
                winner = r.name

        # If game is running and 1 or fewer live robots, we're finished.
        if players <= 1 and arena.status == "R":
            arena.status = "F"
            post_message(f"Finished! The winner is {winner}.")
            for r in robots:
                r.clear_bomb()
        else:
            for r in robots:
                r.update()

        if arena.status == "R":
            arena.gametime = time.time() - arena.starttime
        # If we're paused increment start time
        if arena.status == "P":
            arena.starttime = time.time() - arena.gametime

        gTime.delete(0, END)
        sval = "%.0f" % arena.gametime
        gTime.insert(0, sval)
        frame.update()
        time.sleep(.033)
        if arena.status != "R":
            arena.start_btn_text.set("Start")
        else:
            arena.start_btn_text.set("Pause")

    #except KeyboardInterrupt:
    print("Caught keyboard interrupt, exiting")
    #finally:
    sel.close()
    sys.exit()

main()
