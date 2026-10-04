FROM python:3.12-slim
WORKDIR /srv/catalog
COPY server.py /srv/catalog/server.py
COPY release_validation.py /srv/catalog/artifacts/release_validation.py
EXPOSE 8080
CMD ["python", "/srv/catalog/server.py"]
