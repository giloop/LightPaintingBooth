#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A pygame program to show a slideshow of all images buried in a given directory.
Originally Released: 2007.10.31 (Happy halloween!)
Modified by Giloop for Raspberry Pi Carnaval photobooth: 2015.03.06
"""
from __future__ import division
import argparse
import os
import subprocess
import stat
import sys
import time
import exifread
from threading import Thread
import testDiskUsage as du

import pygame
from pygame.locals import QUIT, KEYDOWN, K_ESCAPE

title = "Photobooth @Giloop !"
waittime = 0.5   # default time to wait between images (in seconds)

def get_exif(fn):
    # Open image file for reading (binary mode)
    f = open(fn, 'rb')
    # Return Exif tags
    tags = exifread.process_file(f, details=False)
    f.close()
    return tags

def listImageFiles(top, extensions=['.png', '.jpg', '.jpeg', '.gif', '.bmp']):
    fileList = []
    for f in os.listdir(top):
        name = os.path.join(top, f)
        mode = os.stat(name)[stat.ST_MODE]
        creation = os.stat(name)[stat.ST_CTIME]
        if stat.S_ISREG(mode):
            # Chech if it's a image file
            filename, ext = os.path.splitext(name)
            e = ext.lower()
            # Only add common image types to the list.
            if e in extensions:
                fileList.append((creation,name))

    # Sort list
    fileList = sorted(fileList)

    # Debug print
    #for (creation,name) in fileList:
    #    print 'Adding to list: ', name, 'date :', time.ctime(creation)

    # Return sorted list
    return fileList


def rot_center(image, angle):
    """rotate an image while keeping its center and size"""
    orig_rect = image.get_rect()
    rot_image = pygame.transform.rotate(image, angle)
    rot_rect = orig_rect.copy()
    rot_rect.center = rot_image.get_rect().center
    rot_image = rot_image.subsurface(rot_rect).copy()
    return rot_image

# Catch ESC key to quit slideshow
def input(events):
    """A function to handle keyboard/mouse/device input events. """
    for event in events:  # Hit the ESC key to quit the slideshow.
        if (event.type == QUIT or
            (event.type == KEYDOWN and event.key == K_ESCAPE)):
            pygame.quit()
            sys.exit(0)


# Main function
class Slideshow(Thread):
    """Thread chargé d'afficher les images du dossier PhotoBooth."""
    def __init__(self, startdir="/home/pi/PhotoBooth"):
        Thread.__init__(self)
        self.startdir = startdir
        self.title = 'Slideshow'
        self.waittime = 4

    def run(self):

        # Init pygame
        pygame.init()

        # Create thumb dir if it does not exists
        thumbDir = os.path.join(self.startdir, 'thumbs')
        if not(os.path.exists(thumbDir)):
            os.mkdir(thumbDir)
        

        # List images in startdir
        fileList = listImageFiles(self.startdir)  # this may take a while...
        
        modes = pygame.display.list_modes()
        # print modes : [(1280, 800)]

        pygame.display.set_mode(max(modes))
        maxMode = max(modes)

        screen = pygame.display.get_surface()
        pygame.display.set_caption(self.title)
        # Plein écran et cache la souris
        pygame.display.toggle_fullscreen()
        pygame.mouse.set_visible(False)

        current = 0
        num_files = len(fileList)
        while(True):
            try:
                bNew = False
                bNoCamera = False
                # Search for new images if not locked
                if (os.path.exists("/home/pi/NoCamera")):
                    bNoCamera = True
                elif (os.path.exists("/home/pi/lock")):
                    bNew = False
                else:
                    newList = listImageFiles(self.startdir)
                    if (num_files == len(newList)):
                        bNew = False

                    else:         
                        bNew = True
                        # Refresh list
                        del fileList
                        fileList = list(newList)
                        del newList
                        num_files = len(fileList)


                # Test usb tous les 10 tours
                bUSB, bDispoOK = du.testUSBKey(self.startdir)
                if (bUSB==True):
                    # TODO copier les photos sur la clef
                    # Arret du slideshow
                    return 


                # Choose file to load
                if (bNoCamera):
                    # Error image to show on No Camera
                    imgName = "/home/pi/dev/PhotoBooth_Giloop/images/AppareilNonDetecte.jpg"
                    
                elif (num_files==0):
                    imgName = "/home/pi/dev/PhotoBooth_Giloop/images/PasDimage.jpg"
                
                elif (bNew):
                    # If there's a new image, show it
                    imgName = fileList[num_files-1][1]
                    # create thumbnail for image
                    imgShortName = os.path.basename(imgName)
                    try:
                        strCommand = "convert -define jpeg:size=500x500 {} -auto-orient -thumbnail '250x250>' -unsharp 0x.5 {}".format(imgName, os.path.join(thumbDir, imgShortName))
                        print(strCommand)
                        gpout = subprocess.check_output(strCommand, stderr=subprocess.STDOUT, shell=True)
                        print(gpout)
                    except subprocess.CalledProcessError:
                        # Create empty file in directory
                        print ("!!! impossible de creer la vignette")
                        
                else:
                    
                    # No new image, get back to current
                    imgName = fileList[current][1]
                    # Increment counter
                    current = (current + 1) % num_files;

                # Load image
                img = pygame.image.load(imgName)
                    
                imgSize = img.get_rect().size
                img = img.convert()
                print "Size :", imgSize
                
                #Get exit rotation info
                tags = get_exif(imgName)
                rotation = 0.
                if 'Image Orientation' in tags.keys():
                    if str(tags['Image Orientation']).lower() == 'Rotated 90 CW'.lower():
                        rotation = -90.
                        imgSize = (imgSize[1],imgSize[0])
                    elif str(tags['Image Orientation']).lower() == 'Rotated 180'.lower():
                        rotation = 180.
                    elif str(tags['Image Orientation']).lower() in ('Rotated 90 CCW'.lower(), 'Rotated 90'.lower()):
                        rotation = 90.
                        imgSize = (imgSize[1],imgSize[0])                            

                # Show it
                scales = (maxMode[0]/imgSize[0], maxMode[1]/imgSize[1])
                
                # rotate & rescale the image to fit the current display
                #img = pygame.transform.scale(img, max(modes))
                print "Image ",imgName, ", rotation ", rotation, ", scale ", min(scales)
                img = pygame.transform.rotozoom(img, rotation, min(scales))

                screen.fill((0,0,0))
                screen.blit(img, ((maxMode[0]-imgSize[0]*min(scales))/2, 0))
                pygame.display.flip()

                input(pygame.event.get())

                # wait
                time.sleep(self.waittime)
                
            except pygame.error as err:
                print "Failed to display %s: %s" % (fileList[current], err)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Recursively loads images '
        'from a directory, then displays them in a Slidshow.'
    )

    parser.add_argument(
        'path',
        metavar='ImagePath',
        type=str,
        default='/home/pi/PhotoBooth',
        nargs="?",
        help='Path to a directory that contains images'
    )
    parser.add_argument(
        '--waittime',
        type=int,
        dest='waittime',
        action='store',
        default=2,
        help='Amount of time to wait before showing the next image.'
    )
    parser.add_argument(
        '--title',
        type=str,
        dest='title',
        action='store',
        default="Diaporama !",
        help='Set the title for the display window.'
    )
    args = parser.parse_args()
    #waittime = args.waittime
    #title = args.title
    mySlide = Slideshow(startdir=args.path)
    mySlide.start()
    
