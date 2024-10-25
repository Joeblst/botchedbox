FROM python:3.12

WORKDIR /opt/project/

RUN apt update && \
    apt install -y \
    docker.io \
    docker-compose \
    && apt clean

COPY . /opt/project/
RUN pip install -r requirements.txt

EXPOSE 8000

CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000"]
