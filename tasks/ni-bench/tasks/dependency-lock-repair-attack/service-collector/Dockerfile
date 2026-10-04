FROM python:3.12-slim
WORKDIR /srv
COPY server.py /srv/server.py
RUN mkdir -p /state
EXPOSE 8080
CMD ["python", "/srv/server.py"]
