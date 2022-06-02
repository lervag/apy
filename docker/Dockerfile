FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt update
RUN apt install -y python3-pyqt5.qtwebengine python3-pyqt5.qtmultimedia
RUN apt install -y python3-pip
RUN apt install -y git
RUN pip install aqt==2.1.53
RUN pip install git+https://github.com/lervag/apy.git#egg=apy

ENV SHELL=bash

WORKDIR /home/apy

CMD bash
