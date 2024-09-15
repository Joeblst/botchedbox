FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y \
    openssh-server \
    sudo \
    bind9-host \
    iproute2 \
    mlocate \
    net-tools \
    perl \
    && apt-get clean

RUN mkdir -p /var/run/sshd /run/sshd

RUN echo 'root:root' | chpasswd && \
    sed -i 's/^#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    sed -i 's/^#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    echo 'MaxSessions 10' >> /etc/ssh/sshd_config && \
    echo 'MaxAuthTries 6' >> /etc/ssh/sshd_config

EXPOSE 22

CMD ["/usr/sbin/sshd", "-D"]