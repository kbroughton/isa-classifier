
from __future__ import print_function
import base64
import binascii
import datetime
import json
import logging
import numpy as np
import os
import random
import requests
import time
import uuid

SUPPORTED_ARCHITECTURES = ["avr", "alphaev56", "arm", "m68k", "mips", 
                           "mipsel", "powerpc", "s390", "sh4", "sparc", "x86_64", "xtensa"]

logging.basicConfig(level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class Server(object):
    url = 'https://mlb.praetorian.com'
    log = logging.getLogger(__name__)

    def __init__(self):
        self.session = requests.session()
        # in a sample of a few dozen, self.binary is either 32 or 36 bytes so pad X to 36 byte columns
        self.binary  = None
        self.hash    = None
        self.wins    = 0
        self.targets = []
        self.rate_limit_count = 0
        self.unknown_server_exception_count = 0
        self.retry_wait = 10
        self.count = 0
        self.failure_record = []
        self.start_time = datetime.datetime.now()
        self.response = None

    def _request(self, route, method='get', data=None):
        while True:
            if self.count > 597:
                print('Resetting session at count {}'.format(self.count))
                self.session = requests.session()
            try:
                if method == 'get':
                    r = self.session.get(self.url + route)
                else:
                    r = self.session.post(self.url + route, data=data)
                self.status_code = r.status_code
                if r.status_code == 429:
                    self.rate_limit_count += 1
                    self.failure_record.append({'type': 'rate_limit',
                                                'count': self.count,
                                                'time': (datetime.datetime.now() -
                                                         self.start_time).total_seconds()})
                    raise Exception('Rate Limit Exception')
                if r.status_code == 500:
                    self.unknown_server_exception_count += 1
                    self.failure_record.append({'type': 'unknown_server_exception',
                                                'count': self.count,
                                                'time': (datetime.datetime.now() -
                                                         self.start_time).total_seconds()})
                    raise Exception('Unknown Server Exception')
                self.response = r
                return r.json()
            except Exception as e:
                self.log.error(e)
                self.log.info('Waiting 60 seconds before next request')
                time.sleep(60)
                self.status_code = None

    def get(self):
        r = self._request("/challenge")
        self.targets = r.get('target', [])
        # removed base64.base64decode(r.get('binary', '')) to allow writes to disk without re-encoding
        self.binary  = r.get('binary', '')
        return r

    def post(self, target):
        r = self._request("/solve", method="post", data={"target": target})
        self.wins = r.get('correct', 0)
        self.hash = r.get('hash', self.hash)
        self.ans  = r.get('target', 'unknown')
        return r
    
    def get_data(self, number=10000):
        """
        Retrieves data in format
        @param number: nubmer of samples to return
        @returns {binary_data: values, targets: values, answers: values}
        where binary_data = [ "<base64 encoded string>", ... ]
        targets =  [ "avr", "x86_64", ... ]
        answers = [one item from targets,]
        """
        data = {}
        # If we grab a large data set make it a little more efficient by pre-allocating
        data['binary_data'] = [None]*number
        data['targets'] = [None]*number
        data['answers'] = [None]*number
        for i in range(number):
            count = 0
            self.get()
            while((self.status_code != 200) and (count < MAX_RETRIES) ):
                print('Status code != 200. Retrying')
                count = count + 1
                self.get()
            data['binary_data'][i] = self.binary
            data['targets'][i] = self.targets
            self.post(self.targets[0])
            while((self.status_code != 200) and (count < MAX_RETRIES) ):
                print('post status code {}'.format(self.status_code))
                count = count + 1
                self.post(self.targets[0])
            data['answers'][i] = self.ans
        return data
    
    def get_data_sets(self, num_train=1024, num_test=128, num_dev=128):
        """
        @returns {'train': {'binary_data': [num_train values],
                            'targets': [num_train [6 values]],
                            'answers': [num_train values],
                  'dev': format as with 'train',
                  'test': format as with 'train'
        }
        @param name_prefix: Write data to a file of this name. If None, do not write
        """
        data = {}
        data['train'] = self.get_data(num_train)
        data['dev'] = self.get_data(num_dev)
        data['test'] = self.get_data(num_test)
        return data
        
        
def submit(number):
    s = Server()

    for _ in range(number):
        # query the /challenge endpoint
        s.get()

        # choose a random target and /solve
        target = random.choice(s.targets)
        s.post(target)

        s.log.info("Guess:[{: >9}]   Answer:[{: >9}]   Wins:[{: >3}]".format(target, s.ans, s.wins))

        # 500 consecutive correct answers are required to win
        # very very unlikely with current code
        if s.hash:
            s.log.info("You win! {}".format(s.hash))    




        
def store(data, root_dir=None):
    """
    Store data to root_dir in a generated filename
    """
    # extract some info from data to generate friendly part of filename
    num_train = str(len(data['train']['answers']))
    num_dev = str(len(data['dev']['answers']))
    num_test = str(len(data['test']['answers']))
    
    if not root_dir:
        root_dir = os.getcwd()
    else:
        root_dir = os.path.realpath(root_dir)
    file_name = "_".join([num_train, num_dev, num_test, str(uuid.uuid1())[0:8]]) + ".json"
    file_path = os.path.join(root_dir, file_name)
    
    with open(file_path, 'w+') as f:
        json.dump(data, f)
            
def load(path):
    """
    load data from a single file.  Data must have format specified in get_data_sets        
    """
    path = os.path.realpath(path)
    with open(path, 'r') as f:
        data = json.load(f)
    return data

def load_dir(path):
    """
    load data from an entire directory.  Data must have format specified in get_data_sets
    """
    merged = {'train': { 'answers': [],
                         'targets': [],
                         'binary_data': [] },
              'dev': { 'answers': [],
                         'targets': [],
                         'binary_data': [] },
              'test': { 'answers': [],
                         'targets': [],
                         'binary_data': [] }
             }
    if os.path.isdir(path):
        for root, dirs, filenames in os.walk(path, topdown=True):
            for filename in filenames:
                if filename.endswith('.json'):
                    merged = merge_data(merged, load(os.path.join(root, filename)))
    return merged

def merge_data(dict1, dict2):
    """
    Perform list additions for two identically formatted dicts with lists at depth 2
    """
    #_dict1 = deepcopy(dict1)
    for key in dict2:
        assert(key in dict1)
        for key2 in dict2[key]:
            assert(key2 in dict2[key])
            dict1[key][key2] = dict1[key][key2] + dict2[key][key2]
    return dict1

def hex_data(base64_binary_data, stride=1, expected_len=None):
    """
    Take an list of base64 encoded data and convert to lists of hex characters
    @params base64_binary_data: a base64 encoded string of (presumeably) 32 or 36 hex numbers
                                shape = (m, 1)
    @params stride: number of bytes to consider a word
    @params expected_len: max length of hex array, used if we need to pad shorter arrays
    @returns: np.array([map(hexlify,base64string),])
              shape = (m, len(base64.b64decode(base64_binary_data))/stride)
    """
    # Should check that we aren't discarding https://docs.python.org/2/library/base64.html
    # Characters that are neither in the normal base-64 alphabet nor the
    # alternative alphabet are discarded prior to the padding check.
    misfits = []
    hex_X = []

    for data in base64_binary_data:
        byte_strings = []
        data = base64.b64decode(data)
        for i in range(0, len(data) , stride):
            byte_strings.append(data[i:i+stride])
        # probably not needed for most text_embeddings, but since most seem 32 or 36 it might help
        if expected_len:
            delta = len(byte_strings) - expected_len
            div = delta/stride
            remainder = delta % stride
            if remainder or (delta < 0):
                misfits.append(byte_strings)
            else:
                byte_strings.extend(['\x00'*stride]*div)
        hex_X.append([ binascii.hexlify(e) for e in byte_strings ])

    return np.array(hex_X), misfits

def class_to_ones_hot(answers, targets, supported_architectures):
    Y = []
    allowed_Y = []
    for answer, target in zip(answers, targets):
        y = [0]*len(supported_architectures)
        index = supported_architectures.index(answer)
        y[index] = 1
        Y.append(y)
        target_hot = [0]*len(supported_architectures)
        for j, arch in enumerate(target):
            index = supported_architectures.index(arch)
            target_hot[index] = 1
        allowed_Y.append(target_hot)
    return np.array(Y), np.array(allowed_Y) 

        