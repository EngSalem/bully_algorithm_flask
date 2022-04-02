## author: Mohamed Salem
## Date: March 8 2022
########################
import argparse
import json
import logging
import time
from enum import IntEnum
from threading import Thread
import random
import flask
import requests
from flask import request, jsonify

logger = logging.getLogger()

parser = argparse.ArgumentParser()
parser.add_argument('--id', action='store', dest='id',
                    help='node id')
parser.add_argument('--host', action='store', dest='host',
                    help='local server host', default='localhost')
parser.add_argument('--port', action='store', dest='port',
                    help='local server port')
args = parser.parse_args()


################################
class BullyCode(IntEnum):
    ELECTION = 0
    OK = 1
    WON = 2


##################################
app = flask.Flask(__name__)
app.config["DEBUG"] = False


###################################


class server:
    def __init__(self, id, host, port):
        self.id = id
        self.host = host
        self.port = port
        self.data_store = {}
        ## replicas info is id2host_port
        self.replica_info = {}
        self.isCoordinator = False
        self.coordinator_id = None
        ## values that will be committed once commit signal is sent
        self.temp_key = None
        self.temp_value = None

    def read_replicas_info(self):
        with open('./replicas_info.json') as jreader:
            self.replica_info = json.load(jreader)

    def read_datastore(self):
        try:
            with open(f'Node_{self.id}_storage.json', 'r') as json_reader:
                self.data_store = json.load(json_reader)

        except:
            with open('./init/data_storage.json', 'r') as json_reader:
                self.data_store = json.load(json_reader)

    def update_value(self, key, value):
        self.data_store[key] = value
        print('updating local storage ...')
        with open(f'Node_{self.id}_storage.json', 'w') as f:
            json.dump(self.data_store, f)

    def get_coordinator_address(self):
        coordinator_ix = int(self.coordinator_id) - 1
        coordinator_host = self.replica_info['server_hosts'][coordinator_ix]
        coordinator_port = self.replica_info['server_ports'][coordinator_ix]
        return ':'.join([coordinator_host, coordinator_port])

    def read(self, key):
        return self.data_store[key]

    def get_higher_servers(self):
        addreses = []
        for ix, id in enumerate(self.replica_info['server_ids']):
            if id > self.id:
                addreses.append(':'.join([self.replica_info['server_hosts'][ix],
                                          self.replica_info['server_ports'][ix]]))
        return addreses

    def get_lower_servers(self):
        addresses = []
        for ix, id in enumerate(self.replica_info['server_ids']):
            if id < self.id:
                addresses.append(':'.join([self.replica_info['server_hosts'][ix],
                                           self.replica_info['server_ports'][ix]]))
        return addresses

    def get_all_adds_except_me(self):
        addresses = []
        for ix, id in enumerate(self.replica_info['server_ids']):
            if id != self.id:
                addresses.append(':'.join([self.replica_info['server_hosts'][ix],
                                           self.replica_info['server_ports'][ix]]))
        return addresses

    def start_election(self):
        ## the node iteratively send an election signal to the nodes with higher ids
        request_body = {'msg': BullyCode.ELECTION}
        isCoordinator = True
        for address in self.get_higher_servers():
            api_url = 'http://' + address + '/api/v1/election_msg/'
            try:
                response = json.loads(requests.post(api_url, data=json.dumps(request_body), timeout=2.5).text)
                if response['msg'] == BullyCode.OK:
                    print('received OK from higher server and dropping')
                    ## drop
                    isCoordinator = False
                    break
            except:
                print(f'server {address} is not responding')

        self.isCoordinator = isCoordinator
        self.coordinator_id = self.id
        if isCoordinator:
            ## send I won to all lower ids servers
            print(f'Server {self.id} is now the coordinator')
            request_body = {'id': self.id, 'msg': BullyCode.WON}
            print(request_body)
            for address in self.get_lower_servers():
                try:
                    api_url = 'http://' + address + '/api/v1/won_msg/'
                    response = json.loads(requests.post(api_url, data=json.dumps(request_body)).text)
                    print(response)

                except:
                    print('not responding ...')
                    continue



        else:
            print(f'Received Ok and initiated an election')

    def update_key(self, key, val):
        try:
            self.data_store[key] = val
            return 'success'
        except:
            return 'failure'


## initialize server
print(f'Starting node ... {args.id}')
node = server(id=args.id, host=args.host, port=args.port)
print(f'Read replica info ...')
node.read_replicas_info()
node.read_datastore()
## set start up time for 3 seconds to allow servers to start
print('Starting election on start ...')
node.start_election()


## bully algorithm
## Election signal in a bully algorithm
@app.route('/api/v1/election_msg/', methods=['POST'])
def election():
    req = request.get_json(force=True)

    def do_election():
        time.sleep(1)
        node.start_election()

    thread = Thread(target=do_election)
    thread.start()
    return jsonify({'msg': BullyCode.OK})


## Won signal in a bully algorithm
@app.route('/api/v1/won_msg/', methods=['POST'])
def won():
    req = request.get_json(force=True)
    print('request', req)
    node.coordinator_id = req['id']
    node.isCoordinator = False
    print(f"Server {req['id']} is now the coordinator")
    return jsonify({"dummy": "dummy"})


@app.route('/api/v1/get_coordinator', methods=['POST'])
def get_coordinator():
    req = request.get_json(force=True)
    return jsonify(
        {'node id': node.id, 'coordinator': node.coordinator_id, 'node_coordinator_signal': node.isCoordinator})

@app.route('/api/v1/get_datastore', methods=['POST'])
def get_datastore():
    req = request.get_json(force=True)
    return jsonify({"store" :node.data_store})

## define a function where the client can contact for updates
@app.route('/api/v1/commit_update', methods=['POST'])
def commit_update():
    req = request.get_json(force=True)
    if req["msg"] == "COMMIT":
        try:
            response = node.update_key(node.temp_key, node.temp_value)
            if response == "success":
               return jsonify({"response": "success"})
            else:
               return jsonify({"respinse": "failure"})
        except:
            return jsonify({"response": "failure"})


## define a ready signal before commit
@app.route('/api/v1/ready_to_commit', methods=['POST'])
def ready_commit():
    req = request.get_json(force=True)
    node.temp_key = req["key"]
    node.temp_value = req["value"]
    return jsonify({"msg": "ready"})


@app.route('/api/v1/update_key', methods=['POST'])
def add_update():
    req = request.get_json(force=True)
    print('received an update request from client')
    ## check if current node is the coordinator
    if node.isCoordinator:
        addresses = node.get_all_adds_except_me()
        correct_responses_counter = 0
        req_body = {"key": req["key"],
                    "value": req["value"]}

        for address in addresses:
            api_url = 'http://' + address + '/api/v1/ready_to_commit'
            try:
                response = json.loads(
                    requests.post(api_url, data=json.dumps(req_body)).text)
                if response["msg"] == "ready":
                    correct_responses_counter += 1
                else:
                    print(f"Node {address} is not ready")
            except:
                print(f"Mode {address} is not responding")

        ### check if quorum
        if correct_responses_counter >= (int(5 / 2) + 1):

            print("Leader achieved quorum sending COMMIT msgs to replicas")
            ## update own local store first
            node.update_key(req["key"], req["value"])
            for address in addresses:
                api_url = 'http://' + address + '/api/v1/commit_update'

                try:
                    response = json.loads(requests.post(api_url, data=json.dumps({"msg": "COMMIT"})).text)
                    if response["response"] == "success":
                        print(f"node {address} has succeeded in updating its local store")
                except:
                    continue

            return jsonify({"msg": "update_success"})
        else:
            return jsonify({"msg": "update_failure"})

    else:
        ## if not coordinator transfer to the coordinator
        coordinator_address = node.get_coordinator_address()
        coordinator_url = 'http://' + coordinator_address + '/api/v1/update_key'
        req_body = {"key": req["key"], "value": req["value"]}
        try:
            response = json.loads(requests.post(coordinator_url, data=json.dumps(req_body)).text)
            if response["msg"] == "update_success":
                ## update local storage
                return jsonify({"msg": "update_success"})
            else:
                return jsonify({"msg": "update_failure"})

        except:
            print("coordinator not responding starting an election")

            def do_election():
                time.sleep(1)
                node.start_election()

            thread = Thread(target=do_election)
            thread.start()
            ####################################
            return jsonify({"msg": "failure resend update"})

@app.route('/api/v1/get_val_key', methods=['POST'])
def get_val():
    req = request.get_json(force=True)
    return jsonify({"value": node.read(req["key"])})


@app.route('/api/v1/read_key', methods=['POST'])
def read():
    ## read key
    req = request.get_json(force=True)
    ## NR should be NR + Nw > N
    ## N =  5, Nw = 3
    ## therefore NR >= 3
    node_val = node.read(req["key"])
    quorum_counter = 0

    replica_ids = [_id for _id in node.replica_info['server_ids'] if _id != node.id]
    ## randomly select replica ids
    while True:
        Nr_ids = random.sample(replica_ids, 3)
        addresses = [':'.join([node.replica_info['server_hosts'][int(ix) - 1], node.replica_info['server_ports'][int(ix) - 1]])
                     for ix in Nr_ids]
        ## first read own value

        for address in addresses:
            try:
                api_url = 'http://' + address + '/api/v1/get_val_key'
                response = json.loads(requests.post(api_url, data=json.dumps({"key": req["key"]})).text)
                print(response)
                if response["value"] == node_val:
                    quorum_counter += 1

            except:
                break
                print(f"node {address} is not responding")

        if quorum_counter >= 3:
           print("We have quorum on read !!!")
           return jsonify({"value": node_val})





app.run(port=node.port, host=node.host)
