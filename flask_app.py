from flask import Flask, render_template, session, request, redirect, flash, url_for, jsonify, Response, logging
from interfaces import databaseinterface, camerainterface, soundinterface
import robot #robot is class that extends the brickpi class
import global_vars as GLOBALS #load global variables
import logging, time
from datetime import *

#Creates the Flask Server Object
app = Flask(__name__); app.debug = True
SECRET_KEY = 'my random key can be anything' #this is used for encrypting sessions
app.config.from_object(__name__) #Set app configuration using above SETTINGS
logging.basicConfig(filename='logs/flask.log', level=logging.INFO)
GLOBALS.DATABASE = databaseinterface.DatabaseInterface('databases/RobotDatabase.db', app.logger)

#Log messages
def log(message):
    app.logger.info(message)
    return

#create a login page
@app.route('/', methods=['GET','POST'])
def login():
    if 'userid' in session:
        return redirect('/dashboard')
    message = ""
    if request.method == "POST":
        email = request.form.get("email")
        userdetails = GLOBALS.DATABASE.ViewQuery("SELECT * FROM users WHERE email = ?", (email,))
        log(userdetails)
        if userdetails:
            user = userdetails[0] #get first row in results
            if user['password'] == request.form.get("password"):
                session['userid'] = user['userid']
                session['permission'] = user['permission']
                session['name'] = user['name']
                return redirect('/dashboard')
            else:
                message = "Login Unsuccessful"
        else:
            message = "Login Unsuccessful"
    return render_template('login.html', data = message)    

# Load the ROBOT
@app.route('/robotload', methods=['GET','POST'])
def robotload():
    sensordict = None
    if not GLOBALS.CAMERA:
        log("LOADING CAMERA")
        try:
            GLOBALS.CAMERA = camerainterface.CameraInterface()
        except Exception as error:
            log("FLASK APP: CAMERA NOT WORKING")
            GLOBALS.CAMERA = None
        if GLOBALS.CAMERA:
            GLOBALS.CAMERA.start()
    if not GLOBALS.ROBOT: 
        log("FLASK APP: LOADING THE ROBOT")
        GLOBALS.ROBOT = robot.Robot(20, app.logger)
        GLOBALS.ROBOT.configure_sensors() #defaults have been provided but you can 
        GLOBALS.ROBOT.reconfig_IMU()
    if not GLOBALS.SOUND:
        log("FLASK APP: LOADING THE SOUND")
        GLOBALS.SOUND = soundinterface.SoundInterface()
        GLOBALS.SOUND.say("I am ready")
    sensordict = GLOBALS.ROBOT.get_all_sensors()
    return jsonify(sensordict)

# ---------------------------------------------------------------------------------------
# Dashboard
@app.route('/dashboard', methods=['GET','POST'])
def robotdashboard():
    if not 'userid' in session:
        return redirect('/')
    enabled = int(GLOBALS.ROBOT != None)
    return render_template('dashboard.html', robot_enabled = enabled )

#Used for reconfiguring IMU
@app.route('/reconfig_IMU', methods=['GET','POST'])
def reconfig_IMU():
    if GLOBALS.ROBOT:
        GLOBALS.ROBOT.reconfig_IMU()
        sensorconfig = GLOBALS.ROBOT.get_all_sensors()
        return jsonify(sensorconfig)
    return jsonify({'message':'ROBOT not loaded'})

#calibrates the compass but takes about 10 seconds, rotate in a small 360 degrees rotation
@app.route('/compass', methods=['GET','POST'])
def compass():
    data = {}
    if GLOBALS.ROBOT:
        data['message'] = GLOBALS.ROBOT.calibrate_imu(10)
    return jsonify(data)

@app.route('/sensors', methods=['GET','POST'])
def sensors():
    data = {}
    if GLOBALS.ROBOT:
        data = GLOBALS.ROBOT.get_all_sensors()
    return jsonify(data)

# YOUR FLASK CODE------------------------------------------------------------------------

@app.route('/shoot', methods=['GET','POST'])
def shoot():
    data = {}
    if GLOBALS.SOUND:
        GLOBALS.SOUND.say("Prepare to die")
    if GLOBALS.ROBOT:
        #for i in range(2): # Because this is playing up otherwise.
        GLOBALS.ROBOT.spin_medium_motor(720)
    return jsonify(data)

@app.route('/reloadpackage', methods=['GET','POST'])
def reloadpackage():
    data = {}
    if GLOBALS.SOUND:
        GLOBALS.SOUND.say("Loading new package")
    if GLOBALS.ROBOT:
        #for i in range(2): # Because this is playing up otherwise.
        GLOBALS.ROBOT.spin_medium_motor(-720)
    return jsonify(data)

@app.route('/moveforward', methods=['GET','POST'])
def moveforward():
    data = {}
    if GLOBALS.ROBOT:
        dat['elapsedtime'] = GLOBALS.ROBOT.move_power(30)
        data['heading'] = GLOBALS.ROBOT.get_compass_IMU()
    return jsonify(data)

@app.route('/movebackward', methods=['GET','POST'])
def movebackward():
    data = {}
    if GLOBALS.ROBOT:
        GLOBALS.ROBOT.move_power_time(-30, 3)
    return jsonify(data)

@app.route('/stop', methods=['GET','POST'])
def stop():
    data = {}
    if GLOBALS.ROBOT:
        GLOBALS.ROBOT.stop_all()
    return jsonify(data)

@app.route('/turnleft', methods=['GET','POST'])
def turnleft():
    data = {}
    if GLOBALS.ROBOT:
        GLOBALS.ROBOT.rotate_power_degrees_IMU(30, -90)
    return jsonify(data)

@app.route('/turnright', methods=['GET','POST'])
def turnright():
    data = {}
    if GLOBALS.ROBOT:
        GLOBALS.ROBOT.rotate_power_degrees_IMU(30, 90)
    return jsonify(data)

@app.route('/mission', methods=['GET','POST']) # Allows the current mission to be updated, and previous missions to be viewed
def misson():
    data = None
    if request.method == "POST": # If the POST method is being used
        userid = session['userid'] # Get the userid from the session
        notes = request.form.get('notes') # Get the notes from the form
        location = request.form.get('location') # Get the location from the form
        starttimePartOne = datetime.now() # Get the start time through a datetime function to get the current time
        log(starttimePartOne) # Logging to see what format this is in because mktime is causing issues.
        starttime = time.mktime(datetime.datetime.strptime(starttimePartOne, "%Y-%m-%d %H:%M:%S").timetuple()) # Please work for the love of goodness gracious.
        # This above bit makes the start time from part one into a Unix Timestamp
        #TODO: For some unholy and godforsaken reason, the terminal says that time.mktime
        log("FLASK_APP - mission: " + str(location) + " " + str(notes) + " " + str(starttime)) # Log these things
        GLOBALS.DATABASE.ModifyQuery("INSERT INTO missionsTable (userid, starttime, location, notes) VALUES (?,?,?,?)", (userid, starttime, location, notes))
        # I might have mucked up this query, too bad!
        # I haven't done one of these in a while. So it's a bit of a guessing game as to whether it works or not.
        # Note to self: Yes, I mucked up the query. I realise that there is no name field in MissionsTable, and that
        # subsequently, I'm a bit silly.


        # The next step: select the current mission entry id and save it into the session as session['missionid']
        CurrentMissionID = GLOBALS.DATABASE.ViewQuery("SELECT MissionID FROM MissionsTable WHERE EndDateTime IS NULL")
        # Like the modify query, I haven't done one of these for a while. It might be quite wrong, but let's hope not!
        session['missionid'] = CurrentMissionID # If the query doesn't work then this will cause problems. This is supposed to
        # set the missionid in session to the current MissionID that we obtained from the DB.
        log(session['missionid']) # Log the CurrentMissionID that is in session
        log(CurrentMissionID) # Log this just for comparison.


    # The next next step: Get the mission history and send it to the page
    data = GLOBALS.DATABASE.ViewQuery("SELECT MissionsTable.MissionID, UsersTable.Name, MissionsTable.StartDateTime, MissionsTable.Location, MissionsTable.EndDateTime, MissionsTable.MedicalNotes FROM MissionsTable INNER JOIN UsersTable ON MissionsTable.UserID = UsersTable.UserID")
    # Hoping and praying that this will work.
    log(data) # Stupid, but it should help in figuring out where the problem is.

    #TODO: Right, time to do some serious witchcraft. I'm going to remove the need to state the name of the manager on the 
    # mission.html form, as we can get that via the UserID in the session dictionary. As for the current mission selection, 
    # my best guess is to add some things to the DB manually and then run it again, because right now it returns 'False'.

    #TODO: Time to run these changes and report what happens

    return render_template('mission.html', data=data) # This renders the template and includes any data that will be sent.

@app.route('/sensorview', methods=['GET','POST']) # Allows the sensor outputs to be viewed
def sensorview():
    data = None
    if GLOBALS.ROBOT:
        data = GLOBALS.ROBOT.get_all_sensors()
    else:
        return redirect('/dashboard')

    return render_template('sensorsview.html', data=data)


































# -----------------------------------------------------------------------------------
# CAMERA CODE-----------------------------------------------------------------------
# Continually gets the frame from the pi camera
def videostream():
    """Video streaming generator function."""
    while True:
        if GLOBALS.CAMERA:
            frame = GLOBALS.CAMERA.get_frame()
            if frame:
                yield (b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n') 
            else:
                return '', 204
        else:
            return '', 204 

#embeds the videofeed by returning a continual stream as above
@app.route('/videofeed')
def videofeed():
    if GLOBALS.CAMERA:
        log("FLASK APP: READING CAMERA")
        """Video streaming route. Put this in the src attribute of an img tag."""
        return Response(videostream(), mimetype='multipart/x-mixed-replace; boundary=frame') 
    else:
        return '', 204
        
#----------------------------------------------------------------------------
#Shutdown the robot, camera and database
def shutdowneverything():
    log("FLASK APP: SHUTDOWN EVERYTHING")
    if GLOBALS.CAMERA:
        GLOBALS.CAMERA.stop()
    if GLOBALS.ROBOT:
        GLOBALS.ROBOT.safe_exit()
    GLOBALS.CAMERA = None; GLOBALS.ROBOT = None; GLOBALS.SOUND = None
    return

#Ajax handler for shutdown button
@app.route('/robotshutdown', methods=['GET','POST'])
def robotshutdown():
    shutdowneverything()
    return jsonify({'message':'robot shutdown'})

#Shut down the web server if necessary
@app.route('/shutdown', methods=['GET','POST'])
def shutdown():
    shutdowneverything()
    func = request.environ.get('werkzeug.server.shutdown')
    func()
    return jsonify({'message':'Shutting Down'})

@app.route('/logout')
def logout():
    shutdowneverything()
    session.clear()
    return redirect('/')

#---------------------------------------------------------------------------
#main method called web server application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True) #runs a local server on port 5000