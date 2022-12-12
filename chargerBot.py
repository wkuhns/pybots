import warbot_lib.userRobot as userRobot
import time
import math

mybot = userRobot.mybot

DEBUG = False

def dprint(msg):
    if DEBUG:
        print(msg)

mybot.heading = 0
mybot.myspeed = 35
mybot.scanDirection = 0
mybot.runTimer = 0
mybot.hunting = False
mybot.shells = 4
mybot.resolution = 10
mybot.shotWaiting = False
mybot.shotTimer = time.time()
mybot.reloadWaiting = False
mybot.reloadTimer = time.time()
mybot.startTime = time.time()
mybot.closestDist = 2000
mybot.closestHeading = 0

mybot.scanmode = "full"
mybot.scancount = 0
hunted = -1

mybot.scanStart = 0
mybot.scanEnd = 359
mybot.huntStart = 0
mybot.huntEnd = 10

mybot.my_bheat = 0
mybot.startmode = True
mybot.last_tick = 0

class Sighting():
    x = -1
    y = -1
    dist = -1
    stime = -1
    bheat = -1
    res = -1
    dist_hi_max = -1    # Dist if barrel heat error is added (max res error added as well)
    dist_hi_min = -1    # Farthest if barrel heat error is added (max res error subtracted)
    dist_lo_max = -1    # same if barrel heat error is subtracted
    dist_lo_min = -1
    hi_max_x = -1
    hi_max_y = -1
    hi_min_x = -1
    hi_min_y = -1
    lo_max_x = -1
    lo_max_y = -1
    lo_min_x = -1
    lo_min_y = -1
    best_x = -1
    best_y = -1
    best_dist = -1

class Enemy():
    alive = False
    scancount = 0
    last_pingtime = time.time()
    last_index = 0
    sighting = []  # Rotating list of last 4 sightings

    # Keep a revolving list of sightings
    def __init__(self):
        for e in range(0, 10):
            self.sighting.append(Sighting())

    def record_sighting(self, distance, direction, resolution):
        self.alive = True
        self.scancount += 1
        self.last_index = (self.last_index + 1) % 10
        
        # Record reported distance and determine nominal coordinates.
        sighting = self.sighting[self.last_index]

        sighting.dist = distance
        sighting.x = mybot.x() + distance * math.cos(math.radians(direction))
        sighting.y = mybot.y() + distance * math.sin(math.radians(direction))
        sighting.stime = time.time()
        sighting.bheat = mybot.my_bheat
        sighting.res = resolution

        # What are the ranges of possible distance? Barrel heat could be positive or negative fixed error.
        # Resolution error could also be positive or negative
        sighting.dist_hi_max = distance + mybot.my_bheat + 5 * resolution
        sighting.dist_hi_min = distance + mybot.my_bheat - 5 * resolution
        sighting.dist_lo_max = distance - mybot.my_bheat + 5 * resolution
        sighting.dist_lo_min = distance - mybot.my_bheat - 5 * resolution
        #print("Recording", sighting.dist_hi_max, sighting.dist_hi_min, sighting.dist_lo_max, sighting.dist_lo_min)

        sighting.hi_max_x = mybot.x() + sighting.dist_hi_max * math.cos(math.radians(direction))
        sighting.hi_max_y = mybot.y() + sighting.dist_hi_max * math.sin(math.radians(direction))
        sighting.hi_min_x = mybot.x() + sighting.dist_hi_min * math.cos(math.radians(direction))
        sighting.hi_min_y = mybot.y() + sighting.dist_hi_min * math.sin(math.radians(direction))

        sighting.lo_max_x = mybot.x() + sighting.dist_lo_max * math.cos(math.radians(direction))
        sighting.lo_max_y = mybot.y() + sighting.dist_lo_max * math.sin(math.radians(direction))
        sighting.lo_min_x = mybot.x() + sighting.dist_lo_min * math.cos(math.radians(direction))
        sighting.lo_min_y = mybot.y() + sighting.dist_lo_min * math.sin(math.radians(direction))

        #mybot.mark(sighting.hi_max_x,sighting.hi_max_y,"white")
        #mybot.mark(sighting.hi_min_x,sighting.hi_min_y,"yellow")
        #mybot.mark(sighting.lo_max_x,sighting.lo_max_y,"cyan")
        #mybot.mark(sighting.lo_min_x,sighting.lo_min_y,"black")
        #mybot.pause()

    # Where do we think he is (or will be)? tfn is 'time from now'. -1 means calculate time of flight for shell
    def predict(self, tfn):
        if self.scancount == 0:
            return (0, 0)
        if self.scancount == 1:
            return (self.sighting[0].hi_max_x + self.sighting[0].lo_min_x) / 2, (self.sighting[0].hi_max_y + self.sighting[0].lo_min_y) / 2
        
        print("Debug",mybot.debug)

        sighting_a = self.sighting[self.last_index]             # Most recent
        sighting_b = self.sighting[(self.last_index + 9) % 10]  # Previous sighting

        # Investigate four possibilities: a low b low, a low b hi, a hi b hi, a hi b lo
        # Start with each at 0 resolution error
        a_lo = abs(sighting_a.dist_lo_min + sighting_a.dist_lo_max) / 2
        a_hi = abs(sighting_a.dist_hi_min + sighting_a.dist_hi_max) / 2
        b_lo = abs(sighting_b.dist_lo_min + sighting_b.dist_lo_max) / 2
        b_hi = abs(sighting_b.dist_hi_min + sighting_b.dist_hi_max) / 2
        dt = sighting_a.stime - sighting_b.stime
        
        mybot.clear()
        # White for both 'b' possibilities
        mybot.mark((sighting_b.lo_min_x + sighting_b.lo_max_x) / 2, (sighting_b.lo_min_y + sighting_b.lo_max_y) / 2,"white")
        mybot.mark((sighting_b.hi_min_x + sighting_b.hi_max_x) / 2, (sighting_b.hi_min_y + sighting_b.hi_max_y) / 2,"white")

        # Cyan for both 'a' 
        mybot.mark((sighting_a.lo_min_x + sighting_a.lo_max_x) / 2, (sighting_a.lo_min_y + sighting_a.lo_max_y) / 2,"cyan")
        mybot.mark((sighting_a.hi_min_x + sighting_a.hi_max_x) / 2, (sighting_a.hi_min_y + sighting_a.hi_max_y) / 2,"cyan")
        
        vbest = 99
        v_alo_blo = abs(a_lo - b_lo) / dt
        v_alo_bhi = abs(a_lo - b_hi) / dt
        v_ahi_bhi = abs(a_hi - b_hi) / dt
        v_ahi_blo = abs(a_hi - b_lo) / dt
        
        if 45 > v_alo_blo > 0:
            vbest = v_alo_blo
            best_ax = (sighting_a.lo_max_x +  sighting_a.lo_min_x) / 2
            best_ay = (sighting_a.lo_max_y +  sighting_a.lo_min_y) / 2
            best_bx = (sighting_b.lo_max_x +  sighting_b.lo_min_x) / 2
            best_by = (sighting_b.lo_max_y +  sighting_b.lo_min_y) / 2

        if (45 > v_alo_bhi > 0) and (abs(20-vbest)> abs(20-v_alo_bhi)):
            vbest = v_alo_bhi
            best_ax = (sighting_a.lo_max_x +  sighting_a.lo_min_x) / 2
            best_ay = (sighting_a.lo_max_y +  sighting_a.lo_min_y) / 2
            best_bx = (sighting_b.hi_max_x +  sighting_b.hi_min_x) / 2
            best_by = (sighting_b.hi_max_y +  sighting_b.hi_min_y) / 2

        if (45 > v_ahi_bhi > 0) and (abs(20-vbest)> abs(20-v_ahi_bhi)):
            vbest = v_ahi_bhi
            best_ax = (sighting_a.hi_max_x +  sighting_a.hi_min_x) / 2
            best_ay = (sighting_a.hi_max_y +  sighting_a.hi_min_y) / 2
            best_bx = (sighting_b.hi_max_x +  sighting_b.hi_min_x) / 2
            best_by = (sighting_b.hi_max_y +  sighting_b.hi_min_y) / 2

        if (45 > v_ahi_blo > 0) and (abs(20-vbest)> abs(20-v_ahi_blo)):
            vbest = v_alo_bhi
            best_ax = (sighting_a.hi_max_x +  sighting_a.hi_min_x) / 2
            best_ay = (sighting_a.hi_max_y +  sighting_a.hi_min_y) / 2
            best_bx = (sighting_b.lo_max_x +  sighting_b.lo_min_x) / 2
            best_by = (sighting_b.lo_max_y +  sighting_b.lo_min_y) / 2

        if vbest == 99:
            return (sighting_a.x, sighting_a.y)

        # Yellow for best b, blue for best a
        mybot.mark(best_bx, best_by, "yellow")
        mybot.mark(best_ax, best_ay, "blue")

        xspeed = (best_ax - best_bx) / dt
        yspeed = (best_ay - best_by) / dt
        dist_now = math.sqrt((mybot.x() - best_ax)**2 + (mybot.y() - best_ay)**2)
        sighting_a.best_dist = dist_now
        
        if tfn == -1:
            tfn = dist_now / 200
    
        xtarget = best_ax + xspeed * tfn
        ytarget = best_ay + yspeed * tfn

        # Black for prediction
        mybot.mark(xtarget, ytarget, "black")


        # Where do we think he'll be?
        return (xtarget, ytarget)

enemies = []

for e in range(0, 5):
    enemies.append(Enemy())

# convert x,y pair to theta and distance
def xy_to_td(x, y):
    dx = x - mybot.x()
    dy = y - mybot.y()
    if dx == 0:
        return (0, 0)
    if dx > 0:
        theta = (math.degrees(math.atan(dy / dx)) + 360) % 360
    else:
        theta = (math.degrees(math.atan(dy / dx) + math.pi) + 360) % 360
    dist = abs(dx / math.cos(math.radians(theta)))
    #print("Us: ", mybot.x(), mybot.y(), "Them:", x, y, "Fire:", int(theta), int(dist))
    print("xy-td: %d\t%d\t%d\t%d\t Theta: %d\t Dist: %d " % (mybot.x(), mybot.y(), x, y, int(theta), int(dist)))
    #mybot.pause()
    return (theta, dist)

def td_to_xy(theta, distance):
    rtheta = theta / 57.3
    xt = mybot.x() + distance * math.cos(rtheta)
    yt = mybot.y() + distance * math.sin(rtheta)
    return (xt, yt)

def enemy_count():
    i = 0
    for e in enemies:
        if e.alive:
            i += 1
    return i

# Scan modes: 'full' means search full 360 and find everyone. Do at 10 res, 18 degree steps. Should take 4 seconds.
# 'verify' means update location for a specific enemy. Start with 10 res at predicted location, then +/- 15 degree 
# scans until located or after +/- 45 degrees (enemy might be dead). could take 1.4 seconds if not found. 

# Where should we start looking next?
def new_scandir():
    closestdist = 2000
    closest_enemy = -1
    for e in range (0, 5):
        if enemies[e].alive:
            if enemies[e].sighting[enemies[e].last_index].best_dist < closestdist:
                closestdist = enemies[e].sighting[enemies[e].last_index].best_dist
                closest_enemy = e
    coords = enemies[closest_enemy].predict(0)
    if coords[0] == -1:
        return 0
    print ("In new scandir: closest is %d at %d, %d" % (closest_enemy, coords[0], coords[1]))
    aim = xy_to_td(coords[0], coords[1])
    print ("aim", aim)
    #mybot.pause()
    return aim[0]


# mybot.scandirection and resolution are already set, but we figure out next values.
def do_scan():

    dprint("In do_scan")
    result = myscan(mybot.scandirection, mybot.resolution)
    mybot.scancount += 1
    if result > 0:
        print("Mode", mybot.scanmode, "Count", mybot.scancount, "hdg", int(mybot.scandirection), "res", mybot.resolution, "distance", int(result) )
    # Are we doing a full scan?
    if mybot.scanmode == "full":
        # did we just finish it?
        if mybot.scancount >= 24:
            # completed full scan. Go after closest
            mybot.scandirection = new_scandir()
            mybot.scancount = 0
            mybot.scanmode = "verify"
            mybot.resolution = 10
            print("Verifying 1")
            return result
        # Not done - increment scan direction
        mybot.scandirection = (mybot.scandirection + 15) % 360    
        return result
    if mybot.scanmode == "verify":
        # did we find him?
        if result > 0:
            if 700 > result > 45:
                mybot.scanmode = "hunt"
                mybot.scancount = 0
                mybot.resolution = 4
                mybot.hunted = mybot.dsp()
                print ("Hunting 1")
            else:
                # too far
                mybot.scanmode = "full"
                mybot.scancount = 0
                mybot.resolution = 10
                print("full 1")
            return result
        # did we fail? Go back to hunt (prolly should try next closest instead)
        if mybot.scancount >= 7:
            mybot.scanmode = "full"
            mybot.scancount = 0
            mybot.resolution = 10
            print ("full 2")
            return result
        # Didn't find him - try next scan
        if mybot.scancount == 1:
            mybot.scandirection = (mybot.scandirection + 15) % 360
        if mybot.scancount == 2:
            mybot.scandirection = (mybot.scandirection + 330) % 360
        if mybot.scancount == 3:
            mybot.scandirection = (mybot.scandirection + 45) % 360
        if mybot.scancount == 4:
            mybot.scandirection = (mybot.scandirection + 300) % 360
        if mybot.scancount == 5:
            mybot.scandirection = (mybot.scandirection + 75) % 360
        if mybot.scancount == 6:
            mybot.scandirection = (mybot.scandirection + 270) % 360
        return result

    if mybot.scanmode == "hunt":
        # Scan resolution starts at 4
        # did we find him?
        if result > 0:
            # Still not tight enough?
            if mybot.resolution > 1:
                mybot.resolution = mybot.resolution / 2
                mybot.scancount = 0
                return result
            else:
                # We're tight enough. Can we fire yet?
                if mybot.shotWaiting == True or mybot.reloadWaiting == True:
                    # Just keep hunting this guy
                    mybot.scancount = 0
                    return result
                # If distance is OK we can shoot
                response = enemies[mybot.dsp()].predict(-1)
                if (response[0] > 0):
                    coords = xy_to_td(int(response[0]), int(response[1]))
                    print("msc", coords)
                    if 700 > coords[1] > 45:
                        print("Mark")
                        mybot.mark(int(response[0]), int(response[1]),"red")
                        print("Fire")
                        myfire(coords[0], coords[1])
                        print("fired:", int(coords[0]), int(coords[1]))
                    # Either fired or too far - hunt again   
                    mybot.scanmode = "full"
                    mybot.scancount = 0
                    mybot.resolution = 10
                    print("full 3")
                    return result
         # Didn't find him - try next scan
        if mybot.scancount >= 7:
            mybot.scanmode = "verify"
            mybot.scancount = 0
            mybot.resolution = 10
            print ("verify 2")
            return result

        if mybot.scancount == 1:
            mybot.scandirection = (mybot.scandirection + 1.5 * mybot.resolution) % 360
        if mybot.scancount == 2:
            mybot.scandirection = (mybot.scandirection + 360 - 3 *  mybot.resolution) % 360
        if mybot.scancount == 3:
            mybot.scandirection = (mybot.scandirection + 4.5 *  mybot.resolution) % 360
        if mybot.scancount == 4:
            mybot.scandirection = (mybot.scandirection + 360 - 6 *  mybot.resolution) % 360
        if mybot.scancount == 5:
            mybot.scandirection = (mybot.scandirection + 7.5 *  mybot.resolution) % 360
        if mybot.scancount == 6:
            mybot.scandirection = (mybot.scandirection + 9 *  mybot.resolution) % 360
        return result
               
# perform scan. Record enemy coordinates and last scan time.
def myscan(direction, resolution):

    dprint("In myscan()")

    result = int(mybot.scan(direction, resolution))
    #mybot.pause()
    if result > 0:
        enemies[mybot.dsp()].record_sighting(result, direction, resolution)
    return result


def myfire(direction, distance):
    mybot.fire(direction, distance)
    mybot.my_bheat += 20
    mybot.shotTimer = time.time() + 4.0
    mybot.shotWaiting = True
    mybot.shells += -1
    if mybot.shells == 0:
        mybot.reloadTimer = time.time() + 12.0
        mybot.reloadWaiting = True
        mybot.scanmode = "full"
        mybot.scancount = 0
        mybot.resolution = 10
        mybot.scanDirection = mybot.heading
    mybot.pause()

def setup():
    mybot.set_name("Charger")
    mybot.drive(mybot.heading, mybot.myspeed)

def ping(enemy):
    enemies[enemy].last_pingtime = mybot.gametime()
    enemies[enemy].alive = True
    if enemies[mybot.dsp()].sighting[enemies[mybot.dsp()].last_index].dist < 750:
        mybot.myspeed = 100
        mybot.drive(mybot.myspeed, mybot.heading)
        mybot.runTimer = time.time() + 3
    else:
        msg = f"Not running from {mybot.dsp()}"
        mybot.post(msg)
    ec = mybot.whereis(enemy)
    print ("Enemy", enemy, "at", ec)

def move():
    
    dprint("In Move()")

    # Calculate barrel heat
    if mybot.my_bheat > 0:
        mybot.my_bheat = mybot.my_bheat - (mybot.gametime() - mybot.last_tick) * 2
        mybot.my_bheat = max(mybot.my_bheat, 0)

    mybot.last_tick = mybot.gametime()

    # If the game just started, head for the closest wall
    if mybot.startmode == True and mybot.closestDist == 2000:
        if mybot.x() < mybot.closestDist:
            mybot.closestDist = mybot.x()
            mybot.closestHeading = 180
        if (1000 - mybot.x()) < mybot.closestDist:
            mybot.closestDist = 1000 - mybot.x()
            mybot.closestHeading = 0
        if mybot.y() < mybot.closestDist:
            mybot.closestDist = mybot.y()
            mybot.closestHeading = 270
        if (1000 - mybot.y()) < mybot.closestDist:
            mybot.closestDist = 1000 - mybot.y()
            mybot.closestHeading = 90
        mybot.post(f"Heading {mybot.closestHeading}")
        mybot.myspeed = 75
        mybot.heading = mybot.closestHeading
        mybot.drive(mybot.myspeed, mybot.heading)
        mybot.scanmode = "full"
        mybot.scancount = 0
        mybot.scandirection = (mybot.heading + 90) % 360

    # See if we need to turn
    olddir = mybot.heading
    if (mybot.x() > 900 and (mybot.heading > 270 or mybot.heading < 90)):
        mybot.heading = 90
        mybot.scanStart = 90
        mybot.scanEnd = 270

    if (mybot.x() < 100 and (mybot.heading < 270 and mybot.heading > 90)):
        mybot.heading = 270
        mybot.scanStart = 270
        mybot.scanEnd = 90

    if mybot.y() > 900 and (mybot.heading > 0 and mybot.heading < 180):
        mybot.heading = 180
        mybot.scanStart = 180
        mybot.scanEnd = 359

    if (mybot.y() < 100 and (mybot.heading > 180 and mybot.heading < 360)):
        mybot.heading = 0
        mybot.scanStart = 0
        mybot.scanEnd = 180

    # If we're turning, set new scandir and slow down
    if mybot.heading != olddir:
        mybot.startmode = False
        mybot.drive(20, mybot.heading)
        # If we're not hunting, reset search
        if not mybot.hunting:
            mybot.scanDirection = mybot.heading

    # If we're not turning, go normal speed
    else:
        if (time.time() > mybot.runTimer):
            mybot.myspeed = 35

    # All done with move calculations. Send drive command if we're not already doing the right thing

    if abs(mybot.heading - mybot.direction() + mybot.myspeed - mybot.speed()) > .1:
        print ("Sending drive command %0.1f %0.1f %0.1f %0.1f" % (mybot.heading, mybot.direction(), mybot.myspeed, mybot.speed()))
        mybot.drive(mybot.myspeed, mybot.heading)

    # Check timers
    if time.time() > mybot.shotTimer:
        mybot.shotWaiting = False
    if time.time() > mybot.reloadTimer and mybot.reloadWaiting == True:
        mybot.reloadWaiting = False
        mybot.shells = 4
    
    dprint("Move: doing scan")

    do_scan()
    
    dprint("Move: finished")


# Do not change these lines
mybot.move = move
mybot.ping = ping
mybot.setup = setup
mybot.main()
