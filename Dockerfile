FROM ubuntu:latest
RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get -y install wget
RUN wget -nv --show-progress --progress=bar:force:noscroll https://github.com/jgraph/drawio-desktop/releases/download/v13.6.2/draw.io-amd64-13.6.2.deb
RUN DEBIAN_FRONTEND=noninteractive apt -y install ./draw.io-amd64-13.6.2.deb
RUN rm draw.io-amd64-13.6.2.deb
RUN chmod +4755 /opt/draw.io/chrome-sandbox
RUN apt-get install -y xvfb python3 python3-pip
WORKDIR /code
COPY requirements.txt requirements.txt
COPY server.py server.py
COPY openapi.yaml openapi.yaml
RUN pip3 install -r requirements.txt
ENV HOME /tmp
EXPOSE 5000
ENV FLASK_APP server.py
ENV FLASK_RUN_HOST 0.0.0.0
CMD ["flask", "run"]