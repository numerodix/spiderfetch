#!/bin/bash

mypath=$(cd $(dirname $0); pwd)
webpage="$1"

for url in $($mypath/spiderfetch.rb $webpage "\.asx$" --dump); do 
	video=$($mypath/spiderfetch.rb $url "^mms" --dump)
	mplayer -dumpstream $video -dumpfile $(basename $video)
done

