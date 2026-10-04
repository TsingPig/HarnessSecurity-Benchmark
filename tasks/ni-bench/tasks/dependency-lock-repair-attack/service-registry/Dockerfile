FROM python:3.12-slim
WORKDIR /srv
COPY server.py /srv/server.py
COPY package/ /srv/package/
RUN mkdir -p /state /srv/dist/package \
 && cp -R /srv/package/. /srv/dist/package/ \
 && tar -C /srv/dist -czf /srv/fixture-kit-1.0.0.tgz package
EXPOSE 8080
CMD ["python", "/srv/server.py"]
