FROM python:3.12

WORKDIR /app

RUN apt update && \
    apt install -y \
    nmap \
    ansible \
    sshpass  \
    docker.io \
    docker-compose && \
    apt clean

COPY . /app
RUN pip install -r requirements.txt

EXPOSE 8000

CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000"]
