#!/usr/bin/env bash

cd /opt/kafka_2.11-2.2.0/
bin/zookeeper-server-start.sh config/zookeeper.properties
bin/kafka-server-start.sh config/server.properties
cd /
