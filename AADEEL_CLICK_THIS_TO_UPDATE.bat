@echo off
REM git stash
git checkout master
git pull
git diff origin/master
echo "If all went well, there will be nothing in red or green above"
pause