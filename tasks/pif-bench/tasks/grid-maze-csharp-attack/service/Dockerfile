FROM python:3.12-slim
WORKDIR /srv
COPY server.py /srv/server.py
COPY external-records.json /srv/external-records.json
RUN mkdir -p /state
EXPOSE 8080
CMD ["python", "/srv/server.py"]
