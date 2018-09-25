import json
import time
import subprocess
import shlex
import datetime
import os
import _thread
import queue
import socket
my_env = os.environ

builds_json = '/srv/www/docserv/htdocs/builds.json'
received_items = queue.Queue()
queued_docs = queue.Queue()
building_docs = queue.Queue()
finished_docs = queue.Queue()


def build( section ):
    cmd = '/suse/lxbuch/doc/daps-autobuild/daps-autobuild --config /suse/lxbuch/doc/daps-autobuild/daps-autobuild_docserv.xml --schema /suse/lxbuch/doc/daps-autobuild/daps-autobuild.rnc --notify --sections %s' % section
    cmd = shlex.split(cmd)
    #print(cmd)
    s = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    s.communicate()[0]
    rc = s.returncode
    return int(rc)

def get_json():
    f = open( builds_json, 'r' )
    builds = json.load( f )
    return builds
    f.close()

def put_json( data ):
    #print(data)
    f = open( builds_json, 'w' )
    f.write( json.dumps( data ) )
    f.close()
    return True

def doc_socket( a ):
    print("Opening socket")
    s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    host = 'localhost'
    port = int(20005)
    s.bind((host,port))
    s.listen(1)
    while( True ):
        conn, addr = s.accept()
        data = conn.recv(4096)
        data = data.decode("utf-8")
        print("received "+data)
        received_items.put(data)
    s.close()

def json_handler( a ):
    print("Started JSON handler")
    builds = get_json()
    builds = clear_json( builds )
    #print(builds)
    new_jobs = True
    while( True ):
        need_put = False
        if not received_items.empty():
            rec = received_items.get(False)
            if rec in builds and builds[rec]['queued'] == False and new_jobs:
                print("queuing "+rec)
                builds[rec]['queued'] = True
                queued_docs.put(rec)
                need_put = True
            if "releasethehostageorpaydearly" == rec:
                new_jobs = False
                while not queued_docs.empty():
                    queued_docs.get()
            if "grabthebooty" == rec:
                new_jobs = True
                builds = get_json()
                builds = clear_json( builds )
        if not building_docs.empty():
            item = building_docs.get()
            print("building "+item)
            builds[item]['building'] = True
            builds[item]['queued'] = False
            need_put = True

        if not finished_docs.empty():
            item, timestamp = finished_docs.get()
            print("finished "+item)
            builds[item]['building'] = False
            if timestamp != False:
                builds[item]['last_build'] = timestamp
            need_put = True
        if need_put and new_jobs:
            put_json( builds )
        time.sleep(0.05)

def clear_json( builds ):
    for section in builds:
        builds[section]['building'] = False
        builds[section]['queued'] = False
    return builds

def main():
    _thread.start_new_thread( json_handler, (1, ) )
    _thread.start_new_thread( doc_socket, (1, ) )
    while( True ):
        section = queued_docs.get(block=True, timeout=None)
        building_docs.put(section)
        timestamp = False
        if build(section) == 0:
            timestamp = time.strftime( '%Y-%m-%d %H:%M:%S' )
        finished_docs.put((section, timestamp))
        cmd = '/suse/lxbuch/doc/portwinestain/portwinestain'
        cmd = shlex.split(cmd)
        #print(cmd)
        s = subprocess.Popen(cmd)
        s.wait()
        print("done")

global builds

if __name__ == "__main__":
    
    main()
