#!/usr/bin/env bash
set -eo pipefail

# Create mount directory for service
mkdir -p $MNT_DIR
echo "Mounting GCS Fuse."

#gcsfuse --debug_gcs --debug_fuse dplengine_bucket $MNT_DIR
gcsfuse dplharmony $MNT_DIR  
echo "Mounting completed."
#ls -l /u01/apps/config/dplharmony
#echo "after dplharmony mount"
#ls -l /u01/apps/config/dplharmony/properties
#cat /u01/apps/config/dplharmony/properties/dpl_ui.properties

exec python /u01/apps/config/dplengine/dplengine.py &

# Exit immediately when one of the background processes terminate.
wait -n
# [END cloudrun_fuse_script]
