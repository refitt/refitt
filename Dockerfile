FROM ubuntu:latest
LABEL maintainer="glentner@purdue.edu"

# minimal necessary packages
RUN apt-get update -y && apt-get upgrade -y

# system utilitites
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y wget openssh-client pass postgresql

# Setup base anaconda
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
RUN bash Miniconda3-latest-Linux-x86_64.sh -b -p /opt/conda && rm -f Miniconda3-latest-Linux-x86_64.sh
RUN /opt/conda/bin/conda update -n base -c defaults conda

RUN mkdir -p /app
RUN /opt/conda/bin/conda create -p /app/libexec python=3.10 numpy scipy pyarrow tensorflow "blas=*=mkl" -c conda-forge
RUN /opt/conda/bin/conda install -p /app/libexec pandas numba astropy sqlalchemy psycopg2 requests flask gunicorn \
                                                 matplotlib seaborn h5py pytables -c conda-forge
RUN /app/libexec/bin/pip install cryptography cmdkit toml tomlkit streamkit names_generator \
                                 antares-client slackclient rich pyyaml \
                                 parsl astroplan timezonefinder pytz bs4 jinja2 \
                                 PyPDF2 more_itertools

# Install Refitt
COPY . /app
RUN /app/libexec/bin/pip install /app --no-deps
RUN mkdir -p /var/lib/refitt /var/run/refitt /var/log/refitt

# Configure environment for interactive user
RUN echo 'source /opt/conda/etc/profile.d/conda.sh' >> ~/.bashrc
RUN echo 'conda activate /app/libexec' >> ~/.bashrc

# Set refitt as default application
ENTRYPOINT ["/app/libexec/bin/refitt"]
CMD ["--ascii-art"]
