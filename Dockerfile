FROM python:2.7
MAINTAINER Michal Gebauer, mishak@mishak.net

ENV CHEETAH_VERSION=2.4.4

# Install Cheetah
RUN wget https://pypi.python.org/packages/source/C/Cheetah/Cheetah-$CHEETAH_VERSION.tar.gz && \
    tar -zxvf Cheetah-$CHEETAH_VERSION.tar.gz && \
    cd Cheetah-$CHEETAH_VERSION && \
    python setup.py install && \
    rm -rf Cheetah-$CHEETAH_VERSION.tar.gz Cheetah-$CHEETAH_VERSION

RUN useradd -M -U sickbeard && \
    mkdir -p /var/lib/sickbeard /opt/sickbeard

ADD . /opt/sickbeard

RUN chown -R sickbeard:sickbeard /var/lib/sickbeard /opt/sickbeard

EXPOSE 8081

VOLUME ["/var/lib/sickbeard"]

CMD ["/opt/sickbeard/SickBeard.py", "--nolaunch"]
