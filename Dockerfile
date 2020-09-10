FROM debian:buster-slim
WORKDIR /code
COPY requirements.txt requirements.txt
RUN DEBIAN_FRONTEND=noninteractive apt-get update && \
    apt-get -y install wget && \
    wget -nv --show-progress --progress=bar:force:noscroll https://github.com/jgraph/drawio-desktop/releases/download/v13.6.2/draw.io-amd64-13.6.2.deb && \
    DEBIAN_FRONTEND=noninteractive apt -y --no-install-recommends install ./draw.io-amd64-13.6.2.deb && \
    chmod +4755 /opt/draw.io/chrome-sandbox && \
    rm draw.io-amd64-13.6.2.deb && \
    apt-get install -y --no-install-recommends xvfb python3 python3-setuptools python3-pip python3-wheel libgbm1 libasound2 xauth && \
    pip3 install -r requirements.txt && \
    apt-get remove -y wget python3-pip python3-wheel && \
    apt autoremove -y && \
    rm -rf /var/lib/apt/lists/
COPY server.py server.py
COPY openapi.yaml openapi.yaml
ENV HOME /tmp
EXPOSE 5000
ENV FLASK_APP server.py
ENV FLASK_RUN_HOST 0.0.0.0
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--access-logfile", "-", "server:app"]