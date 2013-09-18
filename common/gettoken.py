#!/usr/bin/python

import httplib
import json
import os
import re

# arguments
##export OS_AUTH_URL="http://10.13.217.41:5000/v2.0/"
url = os.environ['OS_AUTH_URL']
ip = re.findall( r'[0-9]+(?:\.[0-9]+){3}:[0-9]{4}', url).pop()
##
osuser = os.environ['OS_USERNAME']
##
ospassword = os.environ['OS_PASSWORD']
##

def get_token(ip,osuser,ospassword):
 params = '{"auth":{"passwordCredentials":{"username":"%s", "password":"%s"}}}' % (osuser,ospassword)
 headers = {"Content-Type": "application/json"}
 # HTTP connection
 conn = httplib.HTTPConnection(ip)
 conn.request("POST", "/v2.0/tokens", params, headers)

 # HTTP response

 response = conn.getresponse()
 data = response.read()
 dd = json.loads(data)
 conn.close()
 try:
  dd['access']
  apitoken = dd['access']['token']['id']
 except KeyError as e:
  print e
  exit()

 print "Your token is: %s" % apitoken
 return apitoken