#!/bin/bash
# Set system date using gphoto2 camera

#
# Make sure a root user is running this script 
# 
if [[ $EUID -ne 0 ]]; then
        echo "Must run as root/sudo"
        exit -1
fi

#
# Get unix epoch from camera.  Note, gphoto2 does not support timezones
# or daylight savings.  The local system's timezone will be used, assuming
# the camera and the system are in the same zone.
#
DATETIME=`gphoto2 --get-config datetime`
if [ $? -ne 0 ]; then
        exit 1
fi
EPOCH=`echo "$DATETIME" | grep Current | awk '{print $2}'`
if [[ ! $EPOCH =~ [0-9]{10} ]]; then
        echo "gphoto2 did not return a usable time."
        exit 1
fi

#
# Set current time
#
date -s @$(( EPOCH - 7200 )) --universal

