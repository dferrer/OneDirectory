while sleep 10;
do
	rsync -va dlf3x@labunix01.cs.virginia.edu:~/CS3240/dylan/onedir/ ~/onedir
	rsync -va --delete ~/onedir/ dlf3x@labunix01.cs.virginia.edu:~/CS3240/dylan/onedir
done

# while inotifywait -e modify -e create -e delete -e move -r ~/onedir/; do
# 	rsync -vra --delete ~/onedir/ dlf3x@labunix01.cs.virginia.edu:~/CS3240/dylan/onedir
# done