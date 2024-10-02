FROM python:3.11-alpine

WORKDIR /app

COPY ./requirements.txt /app

RUN pip install -r requirements.txt

COPY . .

EXPOSE 8888

ENV WHEREAMI=DOCKER

CMD ["python", "search_order.py"]
