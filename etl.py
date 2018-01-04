
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
import sys
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
        self.hashes    = []
        self.wins    = 0
        self.targets = []
        self.rate_limit_count = 0
        self.unknown_server_exception_count = 0
        self.retry_wait = 10
        self.count = 0
        self.failure_record = []
        self.start_time = datetime.datetime.now()
        self.response = None
        self.email = None

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
        # removed base64.base64decode(r.get('binary', '')) to keep raw data raw
        self.binary  = r.get('binary', '')
        return r

    def post(self, target):
        r = self._request("/solve", method="post", data={"target": target})
        self.wins = r.get('correct', 0)
        hash = r.get('hash', None)
        if hash:
            self.log.info("You win! {}".format(hash))
            self.collect_hash()
        self.ans  = r.get('target', 'unknown')
        return r
    
    def collect_hash(self):
        r = self._request("/hash", method="post", data={"email": self.email})
        #hash = r.get('hash', None)
        print('hash_response is {}'.format(r))
        self.hashes.append(r)
        # reset the session to earn more hashes
        self.session.close()
        self.session = requests.session()
        
    def get_data(self, number=10000, model=None, email=None):
        """
        Retrieves data in format
        @param number: nubmer of samples to return
        @returns {binary_data: values, targets: values, answers: values}
        where binary_data = [ "<base64 encoded string>", ... ]
        targets =  [ "avr", "x86_64", ... ]
        answers = [one item from targets,]
        """
        if email:
            self.email = email
            
        data = {}
        # If we grab a large data set make it a little more efficient by pre-allocating
        data['binary_data'] = [None]*number
        data['targets'] = [None]*number
        data['answers'] = [None]*number
        for i in range(number):
            self.count = 0
            self.get()
            while((self.status_code != 200) and (self.count < MAX_RETRIES) ):
                print('Status code != 200. Retrying')
                self.count = self.count + 1
                self.get()
            data['binary_data'][i] = self.binary
            data['targets'][i] = self.targets
            if model:
                X = hex_data([self.binary])
                probs = model.predict_proba(X)    # array of shape [1,12]
                targets = class_to_ones_hot_targets([self.targets], model.classes_.tolist())
                #print('data', X)
                #print('probs', probs)
                #print('targets', targets)
                guess_arch = guess_arch_name(model, X, targets)
            else:
                guess_arch = self.targets[0]
            self.post(guess_arch)
            while((self.status_code != 200) and (self.count < MAX_RETRIES) ):
                print('post status code {}'.format(self.status_code))
                self.count = self.count + 1
                self.post(guess_arch)
            #print(i, type(i), self.ans, X, type(data['answers']))
            data['answers'][i] = self.ans
            
        return data
    
    def get_data_sets(self, num_train=1024, num_test=128, num_dev=128, model=None, email=None):
        """
        @param model: If we have a trained model, make trained guesses while downloading data
        
        @returns {'train': {'binary_data': [num_train values],
                            'targets': [num_train [6 values]],
                            'answers': [num_train values],
                  'dev': format as with 'train',
                  'test': format as with 'train'
        }
        """
        data = {}
        data['train'] = self.get_data(num_train, model=model, email=email)
        data['dev'] = self.get_data(num_dev, model=model, email=email)
        data['test'] = self.get_data(num_test, model=model, email=email)
        return data
        

# We only use the server class for interacting with the api
# The methods below can be used with stored data    

        
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
    else:
        merged = load(os.path.abspath(path)
)
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
    # Only python2 version does checking and uses stride, expected_len as it was found
    # that data was uniformly 0 misfits.
    misfits = []
    hex_X = []

    for data in base64_binary_data:
        data = base64.b64decode(data)

        if sys.version_info > (3,0):
            hex_X.append(binascii.hexlify(data).decode('utf-8'))
        else:
            byte_strings = []
            for i in range(0, len(data) , stride):
                byte_strings.append(data[i:i+stride])
            # probably not needed for most text_embeddings, but since most seem 32 or 36 it might help
            if expected_len:
                delta = len(byte_strings) - expected_len
                div = delta/stride
                remainder = delta % stride
                if remainder or (delta < 0):
                    print('misfit data', byte_strings)
                else:
                    byte_strings.extend(['\x00'*stride]*div)
            hex_X.append([ binascii.hexlify(e) for e in byte_strings ])

    return np.array(hex_X)

def class_to_ones_hot_answers(answers, classes):
    """
    Take an list of answers as strings and convert to array of ones hot
    
    @param answers: (m, 1) array of strings
    @param classes: len(classes) array of strings
    @returns: (m, len(classes)) array of 0s and 1s
    """
    get_arch_index = np.vectorize(lambda x: classes.index(x))
    answer_indices = get_arch_index(np.array(answers))
    hots = np.zeros(shape=(len(answers),len(classes)))
    hots[np.arange(len(answers)), answer_indices] = 1
    return hots

def class_to_ones_hot_targets(targets, classes):
    """
    Take an list of targets as strings and convert to array of ones hot
    
    @param answers: (m, 1) array of strings
    @param classes: len(classes) array of strings
    @returns: (m, len(classes)) array of 0s and 1s
    """
    get_arch_index = np.vectorize(lambda x: classes.index(x))
    target_indices = get_arch_index(np.array(targets))
    hots = np.zeros(shape=(len(targets),len(classes)))
    # loop over the six columns of targets array
    for idx in range(target_indices.shape[1]):
        hots[np.arange(len(targets)), target_indices[:,idx]] = 1
    return hots

def class_to_ones_hot(answers, targets, classes):
    """
    Converts lists to arrays and strings to ones-hot
    
    param answers: length m list of strings
    param targets: length m list of [6 strings]
    @returns (m, len(classes) answers, (m, len(classes) targets in ones-hot
    """
    return class_to_ones_hot_answers(answers, classes), class_to_ones_hot_targets(targets, classes) 


def guess_arch_name(model, X, allowed_Y, use_targets=True):
    """
    Get the arch name prediction from the probabilities in ones-hot
    
    model: model trained on (m, 1) input
    X: numerical array of shape (m, 1)
    targets: ones-hot array of shape (m, n_classes), ignored if use_targets = False
    use_targets: if True, Improve our chances by taking the max over the possible targets (6 instead of 12)
    
    returns: (m, 1) of the most likely ISA arch names 
    """
    probs = model.predict_proba(X)
    get_arch = np.vectorize(lambda x: model.classes_.__getitem__(x))
    if use_targets:
        return get_arch(np.argmax(probs*allowed_Y, axis=1))
    else:
        return get_arch(np.argmax(probs, axis=1))
    