#!/usr/bin/env python

# Copyright (C) 2014 Fabien Boucher <fabien.dot.boucher@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os
import sys
import time
import jinja2
import shlex
import argparse
import tempfile
import subprocess

loader = jinja2.FileSystemLoader(searchpath="templates")
env = jinja2.Environment(loader=loader)
td = tempfile.mkdtemp()
starcmd = "heat stack-create -f %(path)s -P 'key_name=%(key_name)s;" \
          "ext_net_uuid=%(ext_net_uuid)s;r_image_id=%(r_image_id)s;" \
          "instance_type=%(instance_type)s' teststack"
waitcmd = "heat stack-show teststack"
stopcmd = "heat stack-delete teststack"
getipcmd = "heat output-show teststack %s_public_address"
connectcmd = "ssh -o StrictHostKeyChecking=no root@%s ls /root/witness"
waitsshupcmd = "ssh-keyscan %s"
template1 = env.get_template("stack.yaml.tmpl")

parser = argparse.ArgumentParser()
parser.add_argument('--anodes', help="amount of nodes")
parser.add_argument('--keyname', help="name of the SSH key to use")
parser.add_argument('--nuuid', help="external network UUID")
parser.add_argument('--iid', help="instance image UUID")
parser.add_argument('--itype', help="instace type")
parser.add_argument('--debug', help="do not destroy the stack at the end", action='store_true', default=False)
args = parser.parse_args()

def stop(msg, error=None):
    print msg
    if error:
        print error.message
    sys.exit(1)

if not args.anodes or not args.keyname or not args.nuuid or \
       not args.iid or not args.itype:
    parser.print_help()
    stop("Missing arguments ...")

nodes = int(args.anodes)

def waitforstack():
    waitamount = 0
    waitmax = 10
    while True:
        time.sleep(10)
        print "Waiting for stack to be UP ..."
        try:
           o = subprocess.check_output(
                shlex.split(waitcmd))
           if o.find('CREATE_COMPLETE') > 0:
               return
           if o.find('CREATE_FAILED') > 0:
               stop("Stack failed to start")
           if waitamount >= waitmax:
               stop("Stack took too long to start")
           waitamount += 1
        except subprocess.CalledProcessError, e:
            pass

def getoutput():
    ret = dict()
    for x in xrange(nodes):
        name = "t%s" % x
        try:
            print "Get IP of node %s with cmd: %s" % (x, getipcmd % name)
            out = subprocess.check_output(
                shlex.split(getipcmd % name))
            ret[name] = out.strip().strip('"')
        except subprocess.CalledProcessError, e:
            stop("Unable to get IP from output", e)
    return ret

def startstack():
    startargs = {"path": os.path.join(td, 'stack.yaml'),
                 "key_name": args.keyname,
                 "ext_net_uuid": args.nuuid,
                 "r_image_id": args.iid,
                 "instance_type": args.itype}
    try:
        print "Starting stack with cmd: %s" % starcmd % startargs
        subprocess.check_output(
            shlex.split(starcmd % startargs))
    except subprocess.CalledProcessError, e:
        stop("Unable to start the stack", e)

def stopstack():
    try:
        print "Stoping stack with cmd: %s" % stopcmd
        subprocess.check_output(
            shlex.split(stopcmd))
    except subprocess.CalledProcessError, e:
        stop("Unable to stop the stack", e)

def wait_sshup(host, ip):
    attempt = 0
    maxattempt = 10
    while True:
        if attempt >= maxattempt:
            return False
        try:
            print "Check SSH fingerprint on %s to be sure is UP with %s" % (host, waitsshupcmd % ip)
            out = subprocess.check_output(
                shlex.split(waitsshupcmd % ip))
            if len(out) > 1:
                break
            else:
                attempt += 1
        except subprocess.CalledProcessError, e:
            print "Unable to ssh scan %s" % host
        time.sleep(5)

def check_connect(host, ip):
    ret = wait_sshup(host, ip)
    if ret == False:
        print "Skip as SSH not up after timeout %s ..." % host
        return False
    try:
        print "Check connection status on %s with %s" % (host, connectcmd % ip)
        subprocess.check_output(
            shlex.split(connectcmd % ip))
        print "Success"
        return True
    except subprocess.CalledProcessError, e:
        print "Unable to connect on %s" % host
        return False

# Fill stack.yaml.tmpl
nodes_desc = {'nodes': []}
for x in xrange(nodes):
    nodes_desc['nodes'].append({'name': 't%s' % x})
output = template1.render(nodes_desc)
file(os.path.join(td, 'stack.yaml'), 'w').write(output)

startstack()
waitforstack()
ips = getoutput()

status = {"success": [],
          "fail": []}
for host, ip in ips.items():
    s = check_connect(host, ip)
    if s:
        status["success"].append(ip)
    else:
        status["fail"].append(ip)

print "Summary:"
print status

if not args.debug:
    stopstack()
