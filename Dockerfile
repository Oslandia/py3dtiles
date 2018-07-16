FROM ubuntu:18.04

RUN apt-get update && apt-get install -y \
    git \
    python3 \
    python3-pip \
    libopenblas-base \
    liblas-c3 \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/Oslandia/py3dtiles
WORKDIR py3dtiles

# TODO(tofull) Remove fetch and checkout operations once lasTo3dtiles branch is merged with master.
RUN git fetch && git checkout lasTo3dtiles

ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8

RUN pip3 install -e .
RUN python3 setup.py install
RUN pip3 install pythran

# Tweak for faster computation
RUN pythran -Ofast -march=native -ffast-math /py3dtiles/py3dtiles/points/distance_test.py

CMD ["py3dtiles", "-h" ]