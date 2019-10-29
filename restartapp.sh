ps -ef |grep "python3 app.py"
ps -ef |grep "python3 app.py" |awk '{print $2}'|xargs kill -9
nohup python3 app.py &
ps -ef |grep "python3 app.py"
cat app.py | grep __version__