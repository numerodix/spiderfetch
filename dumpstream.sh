#!/bin/bash 

cat /dev/null > /tmp/getlog
while read url; do 
	echo "mplayer -dumpstream -dumpfile '$(basename "$url")' '$url' 2>&1; "
	mplayer -dumpstream -dumpfile "$(basename "$url")" "$url" 2>&1; 
	e=$?
	if [ $e != "0" ]; then 
		echo "EXIT NONZERO:  $e   $url" >>/tmp/getlog ; 
	fi; 
done

echo "LOG:"
cat /tmp/getlog
