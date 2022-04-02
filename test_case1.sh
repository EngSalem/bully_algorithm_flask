echo 'Starting server 1'
python server.py --id 1 --host 127.0.0.1 --port 5000 & > /dev/null 2>&1
echo 'Starting server 2'
python server.py --id 2 --host 127.0.0.1 --port 5001 & > /dev/null 2>&1
echo 'Starting server 3'
python server.py --id 3 --host 127.0.0.1 --port 5002  & > /dev/null 2>&1

sleep 10
python client1.py