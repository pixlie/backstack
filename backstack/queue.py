import ujson as json

from .config import settings


async def publish(key, data):
    try:
        import asyncio
    except ImportError:
        raise Exception("You have to install asyncio to run workers,"
                        " see documentation for ERROR_WORKERS_REQUIREMENTS")

    try:
        import aioamqp
    except ImportError:
        raise Exception("You have to install aioamqp to run workers,"
                        " see documentation for ERROR_WORKERS_REQUIREMENTS")

    transport, protocol = await aioamqp.connect(
        settings.RABBITMQ_HOST,
        settings.RABBITMQ_PORT,
    )
    channel = await protocol.channel()
    await channel.exchange_declare(
        exchange_name=settings.get_mq_exchange_name(),
        type_name="topic",
        durable=True
    )

    # This publisher creates a queue with the durable flag and publish a message with the property persistent.
    # https://aioamqp.readthedocs.io/en/latest/examples/work_queue.html
    await channel.basic_publish(
        exchange_name=settings.get_mq_exchange_name(),
        routing_key=key,
        payload=json.dumps(data),
        properties={
            'delivery_mode': 2,
        },
    )
