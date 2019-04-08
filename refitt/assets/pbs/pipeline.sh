#!/bin/bash
#PBS: -N REFITT_{ID}
#PBS: -o {REFITT_HOME}/log/refitt-{TIMESTAMP}.stdout.log
#PBS: -e {REFITT_HOME}/log/refitt-{TIMESTAMP}.stderr.log


# configuration
REFITT_SITE=`dirname ${0}`/..
REFITT_HOME=${REFITT_HOME:-"$HOME/.refitt"}
REFITT_DATA=${REFITT_HOME}/data
REFITT_RUN=${REFITT_HOME}/run
REFITT_LOG=${REFITT_HOME}/log
mkdir -p ${REFITT_DATA} ${REFITT_RUN} ${REFITT_LOG}

# environment
module purge --force --quiet 
PATH="${REFITT_SITE}/bin:/bin:/usr/bin:/usr/local/bin"
source activate "${REFITT_SITE}"

# logging
TIME=`date +"%Y%m%d-%H:%M:%S"` # fixed timestamp
CTRL_LOG=${REFITT_LOG}/refitt-controller-${TIME}.log
ENGS_LOG=${REFITT_LOG}/refitt-engines-${TIME}.log
PLSM_LOG=${REFITT_LOG}/refitt-plasma-${TIME}.log
function _time()     { date +"%Y%m%d-%H:%M:%S"; }
function debug()    { echo -n "DEBUG    `_time` refitt:"; }
function info()     { echo -n "INFO     `_time` refitt:"; }
function warn()     { echo -n "WARNING  `_time` refitt:"; }
function error()    { echo -n "ERROR    `_time` refitt:"; }
function critical() { echo -n "CRITICAL `_time` refitt:"; }

# ensure isolated profile
PROFILE=${PBS_JOBID:-"localhost"}
ipython profile create --parallel --profile=${PROFILE}

# start the ipython controller
ipcontroller --ip="*" --profile=${PROFILE} &>${CTRL_LOG} &
CTRL_PID=$! CTRL_RUN=${REFITT_RUN}/controller-${TIME}.pid
echo ${CTRL_PID} >${CTRL_RUN}
echo "`info` started controller (${CTRL_PID})>${CTRL_RUN}"

# start the ipython engines
mpiexec ipengine --profile=${PROFILE} &>${ENGS_LOG} &
ENGS_PID=$! ENGS_RUN=${REFITT_RUN}/engines-${TIME}.pid
echo ${ENGS_PID} >${ENGS_RUN}
echo "`info` started engines (${ENGS_PID})>${ENGS_RUN}"

# start the plasma in-memory object store
MEM=${REFITT_PLASMA_MEMORY:-"10000000000"} # 10 GBs
plasma_store -m ${MEM} -s ${REFITT_RUN}/plasma-${TIME}.sock &>${PLSM_LOG} &
PLSM_PID=$! PLSM_RUN=${REFITT_RUN}/plasma-${TIME}.pid
echo ${PLSM_PID} >${PLSM_RUN}
echo "`info` started plasma store (${PLSM_PID})>${PLSM_RUN}"

# run pipeline
ENV=`env | grep -E "^REFITT_"`
REFITT_TASKFILE=${REFITT_TASKFILE:-"${REFITT_DATA}/TARGETS"}
touch ${REFITT_TASKFILE} && tail -f -n -1 ${REFITT_TASKFILE} |\
	${ENV} refitt app.pipeline \
		--profile=${PROFILE} \
		--plasma=${REFITT_RUN}/plasma-${TIME}.sock \
		>${REFITT_DATA}/pipeline.stdout
