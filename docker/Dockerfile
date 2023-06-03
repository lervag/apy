FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt update
RUN apt install -y git python3-pip
RUN pip install git+https://github.com/lervag/apy.git

ENV SHELL=bash

WORKDIR /home/apy

CMD bash
