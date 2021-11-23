FROM ubuntu:20.04
LABEL maintainer="glentner@purdue.edu"

# minimal necessary packages
RUN apt-get update -y && apt-get upgrade -y && apt-get install wget -y

# anaconda for cross-platform performance
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
RUN bash Miniconda3-latest-Linux-x86_64.sh -b -p /opt/conda && rm -f Miniconda3-latest-Linux-x86_64.sh
RUN /opt/conda/bin/conda update -n base -c defaults conda && \
    /opt/conda/bin/conda install python=3.8 && \
    /opt/conda/bin/conda install numpy scipy pyarrow "tensorflow==2.6.0" "blas=*=mkl" -c conda-forge && \
    /opt/conda/bin/conda install pandas numba astropy sqlalchemy psycopg2 requests flask gunicorn \
                                 matplotlib seaborn h5py pytables -c conda-forge
RUN /opt/conda/bin/pip install cryptography cmdkit toml streamkit names_generator \
                               antares-client slackclient rich pyyaml \
                               parsl astroplan timezonefinder pytz bs4 jinja2 \
                               PyPDF2 more_itertools

RUN mkdir -p /app
COPY . /app
RUN /opt/conda/bin/pip install /app --no-deps
RUN mkdir -p /var/lib/refitt /var/run/refitt /var/log/refitt

# environment for interactive user
RUN echo 'source /opt/conda/etc/profile.d/conda.sh' >> ~/.bashrc

# set refitt as default application
ENTRYPOINT ["/opt/conda/bin/refitt"]
CMD ["--ascii-art"]
