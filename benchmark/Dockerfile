FROM python:3.12

WORKDIR /app

RUN apt update && \
    apt install -y \
    nmap \
    ansible \
    sshpass && \
    apt clean

COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

CMD ["tail", "-f", "/dev/null"]
