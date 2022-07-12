FROM fedora:latest
WORKDIR /code
RUN dnf install -y python3-pip xorg-x11-server-Xvfb alsa-lib make findutils gdouros-symbola-fonts google-noto-emoji-fonts google-noto-emoji-color-fonts \
    && dnf group install -y fonts \
    && dnf install -y https://github.com/jgraph/drawio-desktop/releases/download/v19.0.3/drawio-x86_64-19.0.3.rpm \
    && dnf clean all \
    && rm -rf /var/cache/dnf
COPY requirements.txt server.py openapi.yaml ./
RUN pip3 install -r requirements.txt
ENV HOME /tmp
EXPOSE 5000
ENV FLASK_APP server.py
ENV FLASK_RUN_HOST 0.0.0.0
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--access-logfile", "-", "server:app"]