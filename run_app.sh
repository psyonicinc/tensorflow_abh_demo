unclutter -idle 0 -display :0 -noevents &
python3 ./lobby_demo.py --CP210x_only && killall -9 unclutter
