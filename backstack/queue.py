import ujson as json
import pika

from .config import settings


def publish(key, data):
    connection = pika.BlockingConnection(pika.ConnectionParameters(
        host=settings.RABBITMQ_HOST,
        port=settings.RABBITMQ_PORT
    ))
    channel = connection.channel()
    channel.exchange_declare(
        exchange=settings.RABBITMQ_EXCHANGE,
        exchange_type="topic"
    )

    channel.basic_publish(
        exchange=settings.RABBITMQ_EXCHANGE,
        routing_key=key,
        body=json.dumps(data)
    )
    connection.close()
