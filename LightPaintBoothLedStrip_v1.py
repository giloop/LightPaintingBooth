#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Photobooth, version utilisant la librairie pigpio
qui gère des pwm pour allumer un ruban de led en 12V
"""

import pigpio
import time
from datetime import datetime
import os
import shutil
import subprocess
import signal
import sys
# import SlideShow as sl
import testDiskUsage as du
from threading import Thread
from lxml import etree

# Globals
SWITCH = 22
SHUTDOWN = 17
HIGH3V = 27 # pin used as +3.3V
RED = 19
BLUE = 13
GREEN = 26
pi = pigpio.pi()

# Lecture du fichier de config
ficConfig = '/home/pi/configLightPainting.xml'
tree = etree.parse('/home/pi/configLightPainting.xml')
imgDir = tree.findall('SAVE/SAVEDIR')[0].text
bSCP = int(tree.findall('SAVE/SCP')[0].text)
strIP = tree.findall('SAVE/IP')[0].text
scpDir = tree.findall('SAVE/SCPDIR')[0].text

tExpo = int(tree.findall('CAMERA/SHUTTERSPEED')[0].text)
bFlash = int(tree.findall('CAMERA/FLASH')[0].text)
bBulb =  int(tree.findall('CAMERA/BULB')[0].text)
tW =  int(tree.findall('IMAGES/THUMBWIDTH')[0].text)
screenW =  int(tree.findall('IMAGES/SCREENWIDTH')[0].text)
imgDir = tree.findall('SAVE/SAVEDIR')[0].text

# Recopie du fichier de config sur l'hote distant si spécifié
if bSCP>0:
    print("Recopie du fichier de config sur l'hote distant")
    strCommand = "scp -o ConnectTimeout=10 {} pi@{}:/home/pi/".format(ficConfig, strIP)
    print(strCommand)
    gpout = subprocess.check_output(strCommand, stderr=subprocess.STDOUT, shell=True)

# Création du dossier d'image s'il n'existe pas
if not os.path.exists(imgDir):
    print("Création du dossier d'image {}".format(imgDir))
    os.makedirs(imgDir)
    
# imgDir = "/home/pi/public_html/PhotoBooth/images/LightPainting"

def setup_Camera():
    """
    Initialisation de l'appareil photo
    """

    print("""
    # NE pas Oublier :
     - Régler le focus en Manuel
     - Flash ferme
     - ...
    """)

    # Test la présence de l'appareil
    gpout = subprocess.check_output('gphoto2 --auto-detect', stderr=subprocess.STDOUT, shell=True)
    if 'EOS' not in gpout:
        print("Appareil EOS non connecte")
        return 1

    print("Synchronisation heure de l'appareil -> RPi")
    gpout = subprocess.check_output('sudo /home/pi/camdate.sh', stderr=subprocess.STDOUT, shell=True)
    print(gpout)
    
    # Test le mode "manuel"
    gpout = subprocess.check_output('gphoto2 --get-config=autoexposuremode', stderr=subprocess.STDOUT, shell=True)
    if 'Current: Manu' not in gpout:
        print("Placer l'appareil en mode Manuel [M]")
        return 2

    # Réglage des configurations en mode M
    strCommand = "gphoto2 --set-config aperture=22; gphoto2 --set-config iso=400"
    gpout = subprocess.check_output(strCommand, stderr=subprocess.STDOUT, shell=True)
    print(gpout)

    # Temps de pause suivant le mode
    if bBulb:
        print("Le mode bulb ne fonctionne pas encore")
        # strCommand = "gphoto2 --set-config-index shutterspeed=0"
        # else:
        # strCommand = "gphoto2 --set-config shutterspeed={}".format(tExpo)

    strCommand = "gphoto2 --set-config shutterspeed={}".format(tExpo)
    gpout = subprocess.check_output(strCommand, stderr=subprocess.STDOUT, shell=True)
    print(gpout)

    # Sortie normale    
    return 0

def GPIO_setup():
    """
    Initialisation des pins utilisées pour le GPIO
    """
    # GPIO setup
    pi.set_mode(SWITCH, pigpio.INPUT)
    pi.set_mode(GREEN,  pigpio.OUTPUT)
    pi.set_mode(RED,    pigpio.OUTPUT)
    pi.set_mode(BLUE,   pigpio.OUTPUT)
    pi.set_mode(HIGH3V, pigpio.OUTPUT)
    
    # Switch off LEDs
    pi.set_PWM_dutycycle(GREEN, 0) # PWM off
    pi.set_PWM_dutycycle(RED,   0) # PWM off
    pi.set_PWM_dutycycle(BLUE,  0) # PWM off
    pi.write(HIGH3V, 1)
    time.sleep(0.1)


def allumerAvantPhoto():
    """Clignotement des LED avant de prendre la photo"""

    # Clignote orange : temps de mise en place
    for i in range(3):
        pi.set_PWM_dutycycle(GREEN, 80-20*i)
        pi.set_PWM_dutycycle(RED,   255)
        pi.set_PWM_dutycycle(BLUE,  0)
        time.sleep(0.5)
        pi.set_PWM_dutycycle(GREEN, 0) # PWM off
        pi.set_PWM_dutycycle(RED,   0) # PWM off
        pi.set_PWM_dutycycle(BLUE,  0) # PWM offt
        time.sleep(0.5)

    # Rouge fixe : temps de pause
    pi.set_PWM_dutycycle(GREEN, 0) # PWM off
    pi.set_PWM_dutycycle(RED,   255) # PWM off
    pi.set_PWM_dutycycle(BLUE,  0) # PWM offt
    # Temps de pause suivant l'appareil (A40 ou EOS ...)
    time.sleep(1.5)

    # Extinction pour la photo
    pi.set_PWM_dutycycle(GREEN, 0) # PWM off
    pi.set_PWM_dutycycle(RED,   0) # PWM off
    pi.set_PWM_dutycycle(BLUE,  0) # PWM offt
    return

def postProcessPhoto(nomImg):

        if not os.path.exists(nomImg):
            print("L'image n'existe pas : {}".format(nomImg))

        # create backup, thumbnail and screen formats for image
        imgOrigName = os.path.basename(nomImg).replace('.jpg', '_orig.jpg')
        imgThumbName = os.path.basename(nomImg).replace('.jpg', '_thumb.jpg')
        imgScreenName = os.path.basename(nomImg).replace('.jpg', '_screen.jpg')
        try:
            pi.set_PWM_dutycycle(GREEN, 0) # PWM off
            pi.set_PWM_dutycycle(RED,   255) # PWM off
            pi.set_PWM_dutycycle(BLUE,  0) # PWM offt

            # Flip image horizontally
            strCommand = "mogrify -flop {}".format(nomImg)
            print(strCommand)
            gpout = subprocess.check_output(strCommand, stderr=subprocess.STDOUT, shell=True)
            print(gpout)

            # Save Orig
            shutil.copyfile(nomImg, os.path.join(imgDir, imgOrigName))

            # Add logo
            strCommand = "convert {} /home/pi/LogoGiloop.png -geometry +4800+3050 -composite /home/pi/LogoHallo.png -geometry +4350+3050 -composite {}".format(nomImg, nomImg)
            print(strCommand)
            gpout = subprocess.check_output(strCommand, stderr=subprocess.STDOUT, shell=True)
            print(gpout)
            

            pi.set_PWM_dutycycle(GREEN, 50) # PWM off
            pi.set_PWM_dutycycle(RED,   255) # PWM off
            pi.set_PWM_dutycycle(BLUE,  0) # PWM offt

            # Thumbnail
            strCommand = "convert -define jpeg:size=500x500 {} -auto-orient -thumbnail '{}x{}>' -unsharp 0x.5 {}".format(nomImg, tW, tW, os.path.join(imgDir, imgThumbName))
            print(strCommand)
            gpout = subprocess.check_output(strCommand, stderr=subprocess.STDOUT, shell=True)
            print(gpout)

            pi.set_PWM_dutycycle(GREEN, 100) # PWM off
            pi.set_PWM_dutycycle(RED,   255) # PWM off
            pi.set_PWM_dutycycle(BLUE,  0) # PWM offt

            # Screen size image
            strCommand = "convert -define jpeg:size=1600x1600 {} -auto-orient -resize '{}x{}>' -unsharp 0x.5 {}".format(nomImg, screenW, screenW, os.path.join(imgDir, imgScreenName))
            print(strCommand)
            gpout = subprocess.check_output(strCommand, stderr=subprocess.STDOUT, shell=True)
            print(gpout)

            pi.set_PWM_dutycycle(GREEN, 200) # PWM off
            pi.set_PWM_dutycycle(RED,   255) # PWM off
            pi.set_PWM_dutycycle(BLUE,  200) # PWM off

            # Transfer SCP si demandé
            if bSCP>0:
                strCommand = "scp -o ConnectTimeout=10 {} {} {} pi@{}:{}".format(nomImg, os.path.join(imgDir, imgScreenName), os.path.join(imgDir, imgThumbName), strIP, scpDir)
                print(strCommand)
                gpout = subprocess.check_output(strCommand, stderr=subprocess.STDOUT, shell=True)
                print(gpout)                 

        except subprocess.CalledProcessError:
            # Create empty file in directory
            print(u'!!! impossible de creer la vignette ou la taille ecran')

def prendrePhoto():
    """
    Prise d'une photo en pause
    """
    
    # Prise d'une photo
    # temp lock file in directory
    open("/home/pi/lock", "a").close()
    # Clignotement des LED avant de prendre la photo
    allumerAvantPhoto()
    
    # Take picture and download it
    try:

        # WakeUp flash
        if bFlash>0:
            gpout = subprocess.check_output("gphoto2 --set-config eosremoterelease=1 --wait-event=1s  --set-config eosremoterelease=1", stderr=subprocess.STDOUT, shell=True)
            print(gpout)
            
        nomImg = "{}/light{}.jpg".format(imgDir, datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d-%H-%M-%S'))
        gpout = subprocess.check_output("gphoto2 --trigger-capture --wait-event-and-download={}s --filename {}".format(tExpo+3, nomImg), stderr=subprocess.STDOUT, shell=True)
        print(gpout)
               
        
    except subprocess.CalledProcessError as e:
        # Create empty file in directory
        print('erreur:')
        print(e)
        if False:
            open("/home/pi/NoCamera", "a").close()
            cptR = 0
            r = 255
            g = 0
            b = 0
            timeOutSec = 10.0
            startTime = time.time()
            while (time.time()-startTime) < timeOutSec:
                if (pi.read(SWITCH)):
                    break
                time.sleep(0.15)
                cptR += 1
                if cptR>2:
                    cptR = 0
                    r = abs(255-r)
                    pi.set_PWM_dutycycle(GREEN, min(255,max(g,0)))
                    pi.set_PWM_dutycycle(RED,   min(255,max(r,0)))
                    pi.set_PWM_dutycycle(BLUE,  min(255,max(b,0)))

                if os.path.exists("//home/pi/NoCamera"):
                    os.remove("/home/pi/NoCamera")
                time.sleep(0.15)
    
    # Delete lock file
    if os.path.exists("/home/pi/lock"):
        os.remove("/home/pi/lock")

    if os.path.exists(nomImg):
        print('appel postProcessPhoto()')
        postProcessPhoto(nomImg)
        
    print("Photo downloaded ... ready for next round")

                
class gestionHardware():
    def __init__(self):
        print("Start main loop")
        if bBulb>0:
            # self.runBulb()
            print("Le Mode Bulb ne marche pas encore")
        #else:
        #    self.run()
        #
        
        # Le Mode Bulb ne marche pas encore
        self.run()

    def run(self):

        # LED colors value
        r = 0
        g = 0
        b = 0
        speed = 10 # Vitesse du Fade
        btnState = False

        #~ Boucle infinie (ctrl+C pour arreter)
        try:
            while True:
                btnState = pi.read(SWITCH)
                if (btnState):
                    print("appel prendrePhoto()")
                    prendrePhoto()
                    
                    # Setting LEDs back to ready mode
                    r = 255
                    g = 0
                    b = 0
                    
                    time.sleep(0.5)
                    
                else:
                    # Etat d'attente d'une action utilisateur quand tout va bien
                    # On fait un fade sur la led verte
                    b = 0
                    if r>0:
                        r = -abs(speed)

                    g += speed
                    if g>=255:
                        g = 255
                        speed = -abs(speed)
                    elif g<=0:
                        g = 0
                        speed = abs(speed)


                    # PWM
                    pi.set_PWM_dutycycle(GREEN, min(255,max(g,0)))
                    pi.set_PWM_dutycycle(RED,   min(255,max(r,0)))
                    pi.set_PWM_dutycycle(BLUE,  min(255,max(b,0)))

                    time.sleep(0.1)
        except KeyboardInterrupt:
            return

    def startBulb(self):
        # Clignotement des LED avant de prendre la photo
        allumerAvantPhoto()

        # Take picture and download it
        try:
            # WakeUp flash
            if bFlash>0:
                gpout = subprocess.check_output("gphoto2 --set-config eosremoterelease=1 --wait-event=1s  --set-config eosremoterelease=0", stderr=subprocess.STDOUT, shell=True)
                print(gpout)
            
            # Enclenche le bouton
            gpout = subprocess.check_output("gphoto2 --set-config eosremoterelease=2", stderr=subprocess.STDOUT, shell=True)
            print(gpout)

        except subprocess.CalledProcessError:
            # Create empty file in directory
            open("/home/pi/NoCamera", "a").close()
            cptR = 0
            r = 255
            g = 0
            b = 0
            timeOutSec = 10.0
            startTime = time.time()
            while (time.time()-startTime) < timeOutSec:
                if (pi.read(SWITCH)):
                    break
                
                time.sleep(0.15)
                cptR += 1

                if cptR>2:
                    cptR = 0
                    r = abs(255-r)
                    pi.set_PWM_dutycycle(GREEN, min(255,max(g,0)))
                    pi.set_PWM_dutycycle(RED,   min(255,max(r,0)))
                    pi.set_PWM_dutycycle(BLUE,  min(255,max(b,0)))

            os.remove("/home/pi/NoCamera")
            time.sleep(0.15)

        # Delete lock file
        if os.path.exists("/home/pi/lock"):
            os.remove("/home/pi/lock")
        print("Mode bulb enclenche ...")


    def stopBulb(self):
        """ Relache le bouton en mode Bulb"""
        nomImg = "{}/light{}.jpg".format(imgDir, datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d-%H-%M-%S'))
        print("... relachement")
        gpout = subprocess.check_output("gphoto2 --set-config-index eosremoterelease=4 --wait-event-and-download=3s --filename {}".format(nomImg), stderr=subprocess.STDOUT, shell=True)
        print(gpout)
        
        postProcessPhoto(nomImg)

        gpout = subprocess.check_output("gphoto2 --set-config eosremoterelease=0", stderr=subprocess.STDOUT, shell=True)
        print(gpout)


    def runBulb(self):

        # LED colors value
        r = 0
        g = 0
        b = 0
        speed = 10 # Vitesse du Fade
        btnState = False
        bBulbOn = False
        #~ Boucle infinie (ctrl+C pour arreter)
        try:
            while True:
                btnState = pi.read(SWITCH)
                if (btnState):
                    if (bBulbOn==False):
                        bBulbOn=True
                        self.startBulb()
                    else:
                        self.stopBulb()
                        bBulbOn==False
                        
                    # Setting LEDs back to ready mode
                    r = 255
                    g = 0
                    b = 0
                    
                    time.sleep(0.5)
                    
                elif (bBulbOn==True):
                    # Mode bulb en cours, on ne fait qu'attendre
                    time.sleep(0.1)
                    
                else:
                    # Etat d'attente d'une action utilisateur quand tout va bien
                    # On fait un fade sur la led verte
                    b = 0
                    if r>0:
                        r = -abs(speed)

                    g += speed
                    if g>=255:
                        g = 255
                        speed = -abs(speed)
                    elif g<=0:
                        g = 0
                        speed = abs(speed)


                    # PWM
                    pi.set_PWM_dutycycle(GREEN, min(255,max(g,0)))
                    pi.set_PWM_dutycycle(RED,   min(255,max(r,0)))
                    pi.set_PWM_dutycycle(BLUE,  min(255,max(b,0)))

                    time.sleep(0.1)
                    
                    
        except KeyboardInterrupt:
            # Arrêt du mopde bulb s'il est en cours
            if (bBulbOn==True):
                bBulbOn=False
                self.stopBulb()
            return

def exitLoop():
    print("Goodbye")
    # Switch off LEDs
    pi.set_PWM_dutycycle(GREEN, 0) # PWM off
    pi.set_PWM_dutycycle(RED,   0) # PWM off
    pi.set_PWM_dutycycle(BLUE,  0) # PWM off
    pi.write(HIGH3V, 0)
    
    # GPIO object stop
    pi.stop()
    
    #sys.exit(0)

if __name__ == '__main__':
    # Clean "lock" file on startup
    if os.path.exists("/home/pi/lock"):
        os.remove("/home/pi/lock")
    if os.path.exists("/home/pi/NoCamera"):
        os.remove("/home/pi/NoCamera")

    print("Vérification des réglages de l'appareil")
    res = setup_Camera()
    if res == 0:
        # Lancement du
        print("Appuyer sur Ctrl+C pour fermer l'application")
        GPIO_setup()

        # Boucle principale (mode temps de pause fixe ou bulb)
        hardLoop = gestionHardware()
        
        # Attend la fin des threads
        exitLoop()

