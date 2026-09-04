FROM python:3.6.13-slim-buster
RUN set -e; \
    apt-get update -y && apt-get install -y \
    libpq-dev \
    zlib1g-dev \
    build-essential \
    shared-mime-info \
    libaio1 \
    libaio-dev \
    zip \
    unzip \
    wget \
    curl \
    lzma \
    liblzma-dev \
    libcurl4-gnutls-dev \
    librtmp-dev \
    tini \
    lsb-release; \
    gcsFuseRepo=gcsfuse-`lsb_release -c -s`; \
    echo "deb https://packages.cloud.google.com/apt $gcsFuseRepo main" | \
    tee /etc/apt/sources.list.d/gcsfuse.list; \
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | \
    apt-key add -; \
    apt-get update; \
    apt-get install -y gcsfuse \
    && wget https://download.oracle.com/otn_software/linux/instantclient/214000/instantclient-basic-linux.x64-21.4.0.0.0dbru.zip \
    && mkdir -p /u01/apps/config/products \
    && mkdir -p /u01/apps/config/products/instantclient_21_4 \    
    && cp instantclient-* /u01/apps/config/products/ \
    && cd /u01/apps/config/products \
    && unzip instantclient-basic-linux.x64-21.4.0.0.0dbru.zip \
    && rm -rf /var/lib/apt/lists/* instantclient-basic-linux.x64-21.4.0.0.0dbru.zip \
    && apt -y remove wget \
    && apt -y autoremove \
    && rm -rf /var/cache/apt \
    && apt-get clean

# Set fallback mount directory
ENV MNT_DIR /u01/apps/config/dplharmony
ENV LD_LIBRARY_PATH /u01/apps/config/products/instantclient_21_4
# Copy local code to the container image.
ENV DPL_ROOT /u01/apps/config/
WORKDIR $DPL_ROOT
COPY . ./

# Install dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# Ensure the script is executable
RUN chmod ug+x /u01/apps/config/gcsfuse_run.sh 

# Use tini to manage zombie processes and signal forwarding
# https://github.com/krallin/tini
ENTRYPOINT ["/usr/bin/tini", "--"] 

# Pass the startup script as arguments to Tini
CMD ["/u01/apps/config/gcsfuse_run.sh"]
# [END cloudrun_fuse_dockerfile]
