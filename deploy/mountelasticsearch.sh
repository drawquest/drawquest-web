#!/bin/bash
set -ex
# If you change the mount command, update the web/init.pp::elasticsearch fstab entry!
sudo mount -t ext4 /dev/xvdf /var/elasticsearch
sudo chown -R elasticsearch.elasticsearch /var/elasticsearch
sudo /etc/init.d/elasticsearch restart

