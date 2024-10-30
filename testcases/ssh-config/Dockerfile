FROM ubuntu:24.04

RUN apt update -y && \
    apt install ssh -y

RUN mkdir /run/sshd; \
    chmod 755 /run/sshd;

ENTRYPOINT ["top", "-b"]