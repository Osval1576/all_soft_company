from django.core.cache import cache

PRESENCE_TTL = 60  # segundos


def _key(user_id):
    return f"presence:user:{user_id}"


def mark_online(user_id):
    cache.set(_key(user_id), True, PRESENCE_TTL)


def is_online(user_id):
    return bool(cache.get(_key(user_id)))


def mark_offline(user_id):
    cache.delete(_key(user_id))
