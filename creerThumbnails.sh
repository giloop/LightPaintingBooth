#!/bin/bash

curDir=`pwd`
cd $1
for photo in *.jpg
   do
	base=${photo%.*}
	if [[ $photo == *"_thumb.jpg"* ]]
	then
		echo "$photo est déjà une vignette !"
	else
		echo "convert $photo to ${base}_thumb.jpg"
		convert -define jpeg:size=500x500 $photo -auto-orient -thumbnail '350x350>' -unsharp 0x.5 ${base}_thumb.jpg
		convert -define jpeg:size=2000x2000 $photo -auto-orient -resize '1556x1556>' -unsharp 0x.5 ${base}_screen.jpg
		# convert "$photo" "$base_thumb.jpg"
	fi
   done

cd $curDir

