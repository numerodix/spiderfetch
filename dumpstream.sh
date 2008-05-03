#!/bin/bash

logfile=$(mktemp /tmp/.$(basename $0).XXXXXX)

while read url; do 
	#echo "mplayer -dumpstream -dumpfile '$(basename "$url")' '$url' 2>&1"
	mplayer -dumpstream -dumpfile "$(basename "$url")" "$url" 2>&1
	e=$?
	if [ $e != "0" ]; then 
		echo "EXIT NONZERO:  $e   $url" >>$logfile
	fi
done

echo "LOG:"
cat $logfile
rm $logfile
