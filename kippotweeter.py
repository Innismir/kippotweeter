#!/usr/bin/env python
#
# kippotweeter.py - Script that monitors a Kippo log file and sends 
# alerts to Twitter
#
# USAGE: nohup ./kippotweeter.py &
#
# All code Copyright (c) 2013, Ben Jackson and Mayhemic Labs -
# bbj@mayhemiclabs.com. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
# * Neither the name of the author nor the names of contributors may be
# used to endorse or promote products derived from this software without
# specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# ACHTUNG/WARNING/PELIGRO/DANGXERO: This code is abysmal right now and may 
# cause the universe to end. Run at your own risk.

import time, os, re, syslog, string, sqlite3
from twitter import *
from ConfigParser import SafeConfigParser

#Read the configuration file
config = SafeConfigParser()
config.read('config.ini')

syslog.openlog("kippotweeter", 0, syslog.LOG_AUTH)

syslog.syslog('kippotweeter Starting...')

login = re.compile("SSHService ssh-userauth on HoneyPotTransport,\d+,(\d+\.\d+\.\d+\.\d+)\] login attempt \[(.+)\/(.+)\] (failed|succeeded)")
new_connection = re.compile("New connection\: (\d+\.\d+\.\d+\.\d+)\:")
lost_connection = re.compile("HoneyPotTransport,\d+,(\d+\.\d+\.\d+\.\d+)\] connection lost")

file = open(config.get('kippotweeter', 'filename'),'r')

st_results = os.stat(config.get('kippotweeter', 'filename'))
st_size = st_results[6]
file.seek(st_size)

MY_TWITTER_CREDS = os.path.expanduser('~/.my_app_credentials')

if not os.path.exists(MY_TWITTER_CREDS):
    oauth_dance(config.get('oauth', 'app_name'), config.get('oauth', 'consumer_key'), config.get('oauth', 'consumer_secret'), MY_TWITTER_CREDS)

oauth_token, oauth_secret = read_token_file(MY_TWITTER_CREDS)

t = Twitter(auth=OAuth(oauth_token, oauth_secret, config.get('oauth', 'consumer_key'), config.get('oauth', 'consumer_secret')))

probedb = sqlite3.connect(config.get('kippotweeter', 'db_file'))
probecursor = probedb.cursor()

syslog.syslog('kippotweeter Ready!')

drive_by_tracker = 0

while 1:
    message = None
    where = file.tell()
    line = file.readline()

    if line:

        for search_term in (login, new_connection, lost_connection):
            result = search_term.search(line)
            if result is not None:
                probecursor.execute("SELECT ipaddress FROM probes WHERE ipaddress = ?" , (result.group(1),))

                if not probecursor.fetchall():
                    probecursor.execute("INSERT INTO probes(ipaddress,first_seen,times_success,times_fail) VALUES (?,?,0,0)", (result.group(1), int(time.time()))) 


        result = login.search(line)

        if result is not None:
            drive_by_tracker = 0

            probecursor.execute('SELECT times_fail, times_success FROM probes WHERE ipaddress = ?', (result.group(1),))

            (success,fail) = probecursor.fetchone()
 
            if result.group(4) == "succeeded":
                message = config.get('kippotweeter', 'node_name') + " auth success (" + result.group(2) + "/" + result.group(3) + ") from " + result.group(1)
                probecursor.execute("UPDATE probes SET times_fail=times_fail+1, last_seen=?, last_success=? WHERE ipaddress=?", (time.time(), time.time(), result.group(1)))

            elif (result.group(4) == "failed"):
                message = config.get('kippotweeter', 'node_name') + " auth fail (" + result.group(2) + "/" + result.group(3) + ") from " + result.group(1) 
                probecursor.execute("UPDATE probes SET times_success=times_success+1, last_seen=?, last_fail=? WHERE ipaddress=?", (time.time(), time.time(), result.group(1)))
 
            message = message + " [S:" + str(success) + "/F:" + str(fail) + "] #TwittIR"

        result = new_connection.search(line)

        if result is not None:
            drive_by_tracker=result.group(1)
 
        result = lost_connection.search(line)

        if drive_by_tracker != 0:
            message = config.get('kippotweeter', 'node_name') + " empty SSH connection from " + drive_by_tracker + " #TwittIR"
            drive_by_tracker = 0

        if message is not None:
            t.statuses.update(status=message)


    else:
        time.sleep(1)
        file.seek(where)

        new_size = os.stat(config.get('kippotweeter', 'filename'))[6]

        if new_size < st_size:
            syslog.syslog('Log file rotated. Recycling...')
            file.close()
            file = open(config.get('kippotweeter', 'filename'),'r')
            file.seek(new_size)
            syslog.syslog('Recycling Complete!')

            st_size = new_size


