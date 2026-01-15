cd /home/lobby_demo/Desktop/psyonic/test/tensorflow_abh_demo/
unclutter -idle 0 -display :0 -noevents &
python3 ./lobby_demo.py --CP210x_only --reverse >&1 && killall -9 unclutter && echo "process complete"

