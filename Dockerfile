FROM ubuntu:18.04

RUN apt-get update && apt-get install -y \
    python3.7 \
    python3-pip \
    libopenblas-base \
    liblas-c3 \
    && rm -rf /var/lib/apt/lists/*

ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8

ADD . /py3dtiles_src
WORKDIR py3dtiles_src
RUN pip3 install -e .


CMD ["py3dtiles", "-h" ]
