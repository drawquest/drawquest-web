#!/usr/bin/env python
import os
import signal
import subprocess
import time
from nginx import read_pid
from optparse import OptionParser

parser = OptionParser()
parser.add_option('--project', dest='project', default='canvas')
options, args = parser.parse_args()

def run(command, cwd='/var/canvas/website', **kwargs):
    return subprocess.Popen(command.split(' '), cwd=cwd, **kwargs)#, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def nginx():
    print 'nginx...'
    return run('python nginx.py --project={}'.format(options.project))

def sass():
    return run('sass --watch --style compressed static/scss:static/css')

def launch(pidname, command):
    pid = read_pid(pidname, force_project=options.project)
    if pid:
        print 'Killing %s (%s)...' % (pidname, pid)
        os.kill(pid, signal.SIGTERM)
        while read_pid(pidname, force_project=options.project):
            time.sleep(0.05)
    print 'starting %s...' % pidname
    return run(command)

def redis():
    if 'version 2.2' in run('redis-server --version', stdout=subprocess.PIPE).stdout.read():
        return launch('redis', 'redis-server redis.conf')

    return launch('redis', 'redis-server redis.2.6.conf')

def memcache():
    if options.project == 'canvas':
        launch('memcached', 'memcached -d -P /var/canvas/website/run/memcached.pid')
    elif options.project == 'drawquest':
        launch('memcached', 'memcached -d -P /var/canvas/website/drawquest/run/memcached.pid -p 11212')

def create_ugc_directories():
    for p in ['processed', 'playbacks', 'original']:
        run('mkdir -p drawquest/ugc/{}'.format(p))

def main():
    processes = {}

    create_ugc_directories()

    def restart(*args, **kwargs):
        for app, proc in processes.items():
            if proc:
                print 'killing %s (%s)...' % (app, proc.pid)
                proc.terminate()
                proc.communicate()

        if 'sass' in run('which sass', stdout=subprocess.PIPE).stdout.read():
            sass()

        redis()
        memcache()
        nginx()
        for app in processes.keys():
            processes[app] = globals()[app]()
            print '%s: %s' % (app, processes[app].pid if processes[app] else None)
        print 'All systems go! Ctrl+C to restart everything, Ctrl+Z to end.\n'

    restart()
    signal.signal(signal.SIGINT, restart)
    while True:
        signal.pause()

if __name__ == '__main__':
    main()

