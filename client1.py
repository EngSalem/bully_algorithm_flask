import requests
import json
import time
print('client is up ...')
print('client is changing ID to 3456 from 1234')

time.sleep(10)
body_req = {"key": "ID", "value": "3456"}

print("contacting replica 1")


api_url = "http://127.0.0.1:5000/api/v1/update_key"
response = json.loads(requests.post(api_url, data=json.dumps(body_req)).text)
if response["msg"] == "update_success":
    print("ID is updated correctly to 3456")
else:
    print("Quorum wasn't achieved , update has failed")
