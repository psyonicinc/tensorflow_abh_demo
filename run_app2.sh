unclutter -idle 0 -display :0 -noevents &
python3 ./Lobby_demo2.py --CP210x_only --reverse > shell_log.txt 2>&1 && killall -9 unclutter && echo "process complete"

