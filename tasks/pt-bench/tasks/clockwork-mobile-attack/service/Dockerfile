FROM python:3.12-slim
WORKDIR /service
COPY service.py /service/
RUN mkdir -p /state
CMD ["python3","/service/service.py"]
