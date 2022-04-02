from enum import IntEnum
import json

################################
class BullyCode(IntEnum):
    ELECTION = 0
    OK = 1
    WON = 2

print(type(BullyCode.OK))
request_body = {'msg': BullyCode.OK}

data=json.dumps(request_body)

print(data)