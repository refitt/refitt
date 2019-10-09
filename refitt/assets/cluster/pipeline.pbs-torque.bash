#!/bin/bash
#PBS: -N REFITT_PIPELINE

# configuration
module purge --force --quiet 
module load refitt
cd $REFITT_SITE

# ensure isolated profile
mkdir -p etc run log lib/ipyparallel
PROFILE=lib/ipyparallel
ipython profile create --parallel --profile-dir=${PROFILE}

# start the ipython controller
ipcontroller --ip="*" --profile-dir=${PROFILE} &>>log/controller.log &
CONTROLLER=$!

# start the ipython engines
mpiexec ipengine --profile-dir=${PROFILE} &>>log/engines.log &
ENGINES=$!

# start the plasma in-memory object store
MEM=${REFITT_PLASMA_MEMORY:-"10000000000"} # 10 GBs
mpiexec -machinefile <(echo $PBS_NODEFILE | sort -u) \
	plasma_store -m ${MEM} -s lib/plasma.sock &>>log/plasma.log &
PLASMA=$!

# run pipeline
touch lib/MANIFEST
tail -n +1 -f lib/MANIFEST \
	| refitt app.pipeline --profile-dir ${PROFILE} --plasma lib/plasma.sock \
	  &>>log/refitt.log
