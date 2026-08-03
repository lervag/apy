# apy in a container.
#
# Build:
#   docker build -t apy docker/
#
# Run (mount your local Anki collection so apy can reach it):
#   docker run -it --rm -v /path/to/anki/collection:/root/.local/share/Anki2 apy
#
# This drops you into a shell with `apy` on the PATH.

FROM ubuntu:26.04

ARG DEBIAN_FRONTEND=noninteractive

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

RUN apt update && apt install -y git

RUN uv tool install git+https://github.com/lervag/apy.git
ENV PATH="/root/.local/bin:$PATH"

ENV SHELL=bash

WORKDIR /home/apy

CMD ["bash"]
