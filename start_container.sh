#!/bin/bash

# Damn Elasticsearch memory limits
echo "Setting VM max map count..."\n
sudo sysctl -w vm.max_map_count=262144

echo "Calling the aniciliary build script to build the runtime container..."\n
bash build_runtime.sh
echo "Runtime container built!"\n

echo "Brace yourself motherfuckers, we're starting it up!"\n

docker-compose up
