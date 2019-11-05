from imutils.video import VideoStream
import datetime
import math
import cv2
import numpy as np
import argparse
import imutils
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import sqlite3

#global variables
width = 0
height = 0
EnterCounter = 0
ExitCounter = 0
AreaBorderMinLimit = 2000  #Change these values according to your needs.
BinarizationThreshold = 70  #Change these values according to your needs.
LineOffset = 120  #Change these values according to your needs.
#timeout = time.time() + 60*1  # 1 minute from now, the program will shutdown, for testing purposes or else.
conn = sqlite3.connect('Count.db')
curr = conn.cursor()

#Verifying if the object is entering the monitored zone.
def CheckEntrance(y, EnterLineYCoordinate, ExitLineYCoordinate):
        AbsoluteDifference = abs(y - EnterLineYCoordinate)

        if ((AbsoluteDifference <= 2) and (y < ExitLineYCoordinate)):
                return 1
        else:
                return 0

#Verifying if the object is leaving the monitored zone.
def CheckExit(y, EnterLineYCoordinate, ExitLineYCoordinate):
        AbsoluteDifference = abs(y - ExitLineYCoordinate)

        if ((AbsoluteDifference <= 2) and (y > EnterLineYCoordinate)):
                return 1
        else:
                return 0

ap = argparse.ArgumentParser()
ap.add_argument("-p", "--picamera", type=int, default=-1,
        help="whether or not the Raspberry Pi camera should be used")
args = vars(ap.parse_args())

camera = VideoStream(usePiCamera=args["picamera"] > 0).start()
time.sleep(2.0)

FirstFrame = None

#Making some frame reading before considering analysis, the reason is, some cameras may take longer to
#get used to ambiente light conditions when they turn on, capturing consecutive frames with a lot of lighting
#variation, so to not process these effects, consecutive captures are maybe outside the image processing giving the
#camera some time to adapt to lighting conditions.

for i in range(0,20):
    (grabbed, Frame) = camera.read(), camera.read()

while True:
    #Reading first Frame and determining size.
    (grabbed, Frame) = camera.read(), camera.read()
    height = np.size(Frame,0)
    width = np.size(Frame,1)

    #Converting Frame to Grey Scale and applying Blur Effect to highlight shapes.
    FrameGray = cv2.cvtColor(Frame, cv2.COLOR_BGR2GRAY)
    FrameGray = cv2.GaussianBlur(FrameGray, (21, 21), 0)

    #A comparisson is made between two images, if the first frame is null, it's initialized.
    if FirstFrame is None:
        FirstFrame = FrameGray
        continue

    #Absolute difference between initial frame and actual frame (Background Subtraction)
    #Also makes the binarization of the frame and the subtracted background.
    FrameDelta = cv2.absdiff(FirstFrame, FrameGray)
    FrameThresh = cv2.threshold(FrameDelta, BinarizationThreshold, 255, cv2.THRESH_BINARY)[1]

    #Makes the dilatation of the binarized frame to eliminate holes, white zones inside the found shapes,
    #this way, detected objects will be considered a black mass, also finds the shapes after dilatation.
    FrameThresh = cv2.dilate(FrameThresh, None, iterations=2)
    _, cnts, _ = cv2.findContours(FrameThresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    NumContours = 0

    #Drawing reference lines
    EnterLineYCoordinate = (height / 2)-LineOffset
    ExitLineYCoordinate = (height / 2)+LineOffset
    cv2.line(Frame, (0,int(EnterLineYCoordinate)), (width,int(EnterLineYCoordinate)), (255, 0, 0), 2)
    cv2.line(Frame, (0,int(ExitLineYCoordinate)), (width,int(ExitLineYCoordinate)), (0, 0, 255), 2)


    #Wiping found shapes
    for c in cnts:
        #Small shapes are to be ignored.
        if cv2.contourArea(c) < AreaBorderMinLimit:
            continue
        #For debugging purposes, counts the number of found shapes
        NumContours = NumContours+1

        #Gets the shapes coordinates (A rectangle that involves the object), highlighting it's shape.
        (x, y, w, h) = cv2.boundingRect(c) #x e y: coordenadas do vertice superior esquerdo
                                           #w e h: respectivamente largura e altura do retangulo

        cv2.rectangle(Frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        #Determines the central point of the shape, and circles it.
        XCoordinateOfCenterOfContour = (x+x+w)/2
        YCoordinateOfCenterOfContour = (y+y+h)/2
        CenterOfContour = (math.floor(XCoordinateOfCenterOfContour),math.floor(YCoordinateOfCenterOfContour))
        cv2.circle(Frame, CenterOfContour, 1, (0, 0, 0), 5)

        #Tests the intersection of centers from the shapes and the reference lines. This way, it may count
        #which shapes crosses the reference lines.
        if (CheckEntrance(YCoordinateOfCenterOfContour,EnterLineYCoordinate,ExitLineYCoordinate)):
            EnterCounter += 1

        if (CheckExit(YCoordinateOfCenterOfContour,EnterLineYCoordinate,ExitLineYCoordinate)):
            ExitCounter += 1

        #If needed, uncomment these lines to show framerate.
        #cv2.imshow("Frame binarizado", FrameThresh)
        #cv2.waitKey(1);
        #cv2.imshow("Frame com subtracao de background", FrameDelta)
        #cv2.waitKey(1);


    print ("Contouts Entered: " + str(NumContours))

    #Writes on screen the number of people who enters or leaves the watched area.
    cv2.putText(Frame, "Enter: {}".format(str(EnterCounter)), (10, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (250, 0, 1), 2)
    cv2.putText(Frame, "Exit: {}".format(str(ExitCounter)), (10, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    cv2.imshow("Original", Frame)
    key = cv2.waitKey(1) & 0xFF

    #If you want to exit the program from a keystroke, uncomment these lines and comment the next ones,
    #which makes the program exit by itself after a certain ammount of time.
    # if the `q` key was pressed, break from the loop
    #if key == ord("q"):
        #break

    # test = 0
    # if test == 5 or time.time() > timeout:
    #     break
    # test = test - 1

# cleanup the camera and close any open windows

#Program writes the count to a file.
f = open( 'Count.txt', 'w' ) #File path and it's name with extension, to write to.
f.write( 'EnterCounter = ' + repr(EnterCounter) + '\n' ) #Variables to write
f.write( 'ExitCounter = ' + repr(ExitCounter) + '\n' ) #Variables to write
f.close()

#The following code allows you to send the file to an email address, if not needed just delete or comment it.
#Good thing there is a built in library for this already, so why not make use of it =D.

#fromaddr = "bhad1434@pacificu.edu" #Your Email Address
#toaddr = "sbhadra1@steelcase.com" #Address to receive email

#msg = MIMEMultipart()

#msg['From'] = fromaddr
#msg['To'] = toaddr
#msg['Subject'] = "Item Count" #Subject of the email goes here

#body = "How many items entered in the last session." #Message to be written on the email

#msg.attach(MIMEText(body, 'plain'))

#filename = "Count.txt" #File name with extension to send as an attatchment.
#attachment = open("/home/pi/Count.txt", "rb") #File path

#part = MIMEBase('application', 'octet-stream')
#part.set_payload((attachment).read())
#encoders.encode_base64(part)
#part.add_header('Content-Disposition', "attachment; filename= %s" % filename)

#msg.attach(part)

#server = smtplib.SMTP('smtp.gmail.com', 587)
#server.starttls()
#server.login(fromaddr, "Password") #Your password goes here, substitute xxxx for it.
#text = msg.as_string()
#server.sendmail(fromaddr, toaddr, text)
#server.quit()
cv2.destroyAllWindows()
camera.stop()
conn.commit()
conn.close()
