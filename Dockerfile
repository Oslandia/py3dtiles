FROM debian:buster-slim

RUN apt-get update \
    && apt-get install -y git libgmp-dev libatlas-base-dev liblas-dev liblas-c3 python3.6 python3.6-dev python3-pip python3-numpy\
    && rm -rf /var/lib/apt/lists/*

RUN cd /opt \
    && git clone https://github.com/Oslandia/py3dtiles.git \
    && cd py3dtiles \
    && git checkout lasTo3dtiles \
    && pip3 install . \

CMD ["/usr/local/bin/py3dtiles"]
