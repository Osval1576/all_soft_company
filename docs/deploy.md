# Deploy de AllSafe en producción (VPS + Docker Compose)

Runbook para llevar AllSafe a un VPS con Docker Compose: Django (daphne) + Vue (nginx) + MySQL + Redis, con TLS y checklist de verificación post-deploy.

## 1. Requisitos del VPS

- Docker Engine + el plugin `docker compose` (v2). Verificar con `docker compose version`.
- Un dominio (por ejemplo `allsafe.example.com`) con el registro `A` apuntando a la IP pública del VPS. Necesario para poder emitir el certificado TLS con certbot.
- Puertos `80` y `443` abiertos y libres (ningún otro servicio — Apache, otro nginx, etc. — escuchando ahí).
- Al menos ~2 GB de RAM libres (MySQL + Redis + Django + nginx + build de Vue en la imagen del frontend).
- Acceso SSH con un usuario que pueda correr `docker` (grupo `docker` o `sudo`).

## 2. Primer deploy

```bash
# 1. Clonar el repo en el VPS
git clone <url-del-repo> allsafe
cd allsafe

# 2. Copiar y completar el .env
cp .env.example .env
nano .env   # completar DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS, DB_PASSWORD,
            # MYSQL_ROOT_PASSWORD, CSRF_TRUSTED_ORIGINS, etc.

# Generar un DJANGO_SECRET_KEY nuevo:
python3 -c "import secrets; print(secrets.token_urlsafe(64))"

# 3. Levantar todo (build + up en un solo paso)
docker compose up -d --build

# 4. Ver que los servicios estén sanos
docker compose ps

# 5. Crear el superusuario admin
docker compose exec web python manage.py createsuperuser
```

En este primer `up`, el servicio `web` corre `migrate`, el guard de producción (`check --deploy`, ver sección 6) y `collectstatic` antes de arrancar daphne (ver `backend/entrypoint.sh`). Si el `.env` está incompleto, `web` va a fallar el boot con un error `config.E001`/`config.E002` — completar el `.env` y volver a correr `docker compose up -d --build`.

En este punto el sitio queda accesible por HTTP en el puerto 80 (todavía sin TLS). Seguir con la sección 3 antes de exponerlo públicamente en un dominio real.

## 3. TLS

AllSafe sirve HTTPS terminando TLS en el propio contenedor `nginx` del frontend, usando certificados de Let's Encrypt obtenidos con certbot en modo standalone (parando nginx momentáneamente para la emisión inicial).

### 3.1 Emitir el certificado

```bash
# Parar nginx para liberar el puerto 80 (certbot standalone lo necesita)
docker compose stop nginx

# Emitir el certificado (instalar certbot en el host si no está: apt install certbot)
sudo certbot certonly --standalone -d allsafe.example.com

# Los certificados quedan en /etc/letsencrypt/live/allsafe.example.com/
```

### 3.2 Copiar los certificados al volumen que usa nginx

```bash
mkdir -p ./certs
sudo cp /etc/letsencrypt/live/allsafe.example.com/fullchain.pem ./certs/
sudo cp /etc/letsencrypt/live/allsafe.example.com/privkey.pem ./certs/
sudo chmod 644 ./certs/fullchain.pem ./certs/privkey.pem
```

(`./certs` ya está montado en el contenedor `nginx` en `/etc/nginx/certs` — ver `docker-compose.yml`.)

### 3.3 Agregar el bloque 443 a `frontend/nginx.conf`

Agregar el bloque 443 de abajo **antes** del bloque `server { listen 80; ... }` existente. El bloque `server { listen 80; server_name _; ... }` original (el que sirve la app directamente por HTTP) debe ser **reemplazado por completo** por el bloque de redirect 80→443 que aparece al final — no debe quedar ningún vhost HTTP sin redirect sirviendo la app en el puerto 80 en paralelo al 443 (dejando `/api/health/` fuera del redirect no es necesario acá porque el healthcheck del compose pega directo a `web:8000`, no pasa por nginx):

```nginx
server {
    listen 443 ssl;
    server_name allsafe.example.com;
    client_max_body_size 12m;

    ssl_certificate     /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    root /usr/share/nginx/html;
    index index.html;

    location /api/ {
        proxy_pass http://web:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /django-admin/ {
        proxy_pass http://web:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /static/ {
        alias /staticfiles/;
    }

    location /ws/ {
        proxy_pass http://web:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 3600s;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}

server {
    listen 80;
    server_name allsafe.example.com;
    # Redirect a HTTPS. Todo lo demás queda servido por el bloque 443 de arriba.
    return 301 https://$host$request_uri;
}
```

Con `SECURE_SSL_REDIRECT=true` en el `.env` (default en `.env.example`), Django también redirige internamente cualquier request que le llegue como HTTP puro — el redirect en nginx es la primera línea de defensa, el de Django es el respaldo.

### 3.4 Rebuild de nginx con el nuevo `nginx.conf`

```bash
docker compose up -d --build nginx
```

### 3.5 Renovación del certificado

Let's Encrypt vence a los 90 días. Renovar y reiniciar nginx (con el sitio ya activo no hace falta pararlo: usar el modo `webroot` o simplemente aceptar el breve corte con `stop`/`certonly`/`start`, ya que la renovación tarda segundos):

```bash
docker compose stop nginx
sudo certbot renew
sudo cp /etc/letsencrypt/live/allsafe.example.com/fullchain.pem ./certs/
sudo cp /etc/letsencrypt/live/allsafe.example.com/privkey.pem ./certs/
docker compose start nginx
```

Automatizar con un cron mensual (correr como root, o con `sudo` sin password para ese comando puntual):

```cron
# /etc/cron.d/allsafe-certbot-renew — primer día de cada mes a las 3am
0 3 1 * * root cd /ruta/a/allsafe && docker compose stop nginx && certbot renew --quiet && cp /etc/letsencrypt/live/allsafe.example.com/fullchain.pem ./certs/ && cp /etc/letsencrypt/live/allsafe.example.com/privkey.pem ./certs/ && docker compose start nginx
```

## 4. Smoke checklist post-deploy

Correr esta lista completa después de cada deploy a producción (primer deploy y cada actualización posterior):

- [ ] **Health verde**: `docker compose ps` muestra `web`, `mysql`, `redis`, `nginx` y `scheduler` como `healthy`/`running` (mysql, redis y web tienen healthcheck explícito).
- [ ] **Login por el dominio**: entrar a `https://allsafe.example.com`, loguearse con un usuario real y confirmar que el dashboard carga.
- [ ] **WS de chat conecta**: abrir un ticket con chat y verificar que el badge de estado marca "conectado" (no queda en reconexión/desconectado).
- [ ] **Upload + download de adjunto**: subir un archivo a un ticket y volver a descargarlo — confirma que el volumen `media_volume` y el servido autenticado por Django funcionan.
- [ ] **Notificaciones entre 2 sesiones** (prueba real de Redis pub/sub entre workers): ver el bloque de verificación Redis abajo.
- [ ] **`/django-admin/` accesible**: entrar a `https://allsafe.example.com/django-admin/` con el superusuario creado en el paso 2 y confirmar que carga el admin de Django con sus estáticos (CSS) bien servidos.

### 4.1 Verificación específica de Redis (sin cobertura automatizada — hacerla a mano)

El código que usa Redis (`channels_redis` para WS multi-proceso, `django_redis` para cache) no tiene tests automatizados que lo ejerciten contra un Redis real, así que esta verificación manual es la única red de seguridad:

**(a) `check` pasa con `REDIS_URL` seteado:**

```bash
docker compose exec web python manage.py check
```

No debe haber errores relacionados a `CHANNEL_LAYERS` ni `CACHES`.

**(b) El cache round-trip pega contra Redis de verdad** (no un fallback silencioso a LocMem):

```bash
docker compose exec web python manage.py shell -c "
from django.core.cache import cache
cache.set('smoke_test_key', 'ok', 30)
print(cache.get('smoke_test_key'))
"
# Debe imprimir: ok

docker compose exec redis redis-cli keys '*smoke_test_key*'
# Debe listar la key (con el prefijo que use django-redis, ej ':1:smoke_test_key')
```

**(c) La notificación WS cruza dos workers de `web`** (confirma que `channels_redis` está haciendo de channel layer compartido y no cada proceso quedó aislado):

```bash
docker compose up -d --scale web=2
```

Abrir dos sesiones de navegador (o una normal + una privada) logueadas con usuarios distintos, y disparar una acción que genere notificación en tiempo real (ej. actualizar un ticket asignado a otro técnico). Como nginx hace round-robin entre las dos réplicas de `web`, si la notificación llega igual en ambas sesiones confirma que el pub/sub de Redis está uniendo los procesos. Si algún browser se queda sin la notificación, sospechar que quedó pegado al worker que no la generó — revisar `docker compose logs web`.

Volver a una sola réplica después de la prueba (`docker compose up -d --scale web=1`) salvo que se quiera dejar escalado — ver sección 5.

**(d) Matar Redis produce una falla ruidosa, no degradación silenciosa:**

`/api/health/` **no** sirve para esta prueba: solo hace `SELECT 1` contra MySQL y no toca Redis, así que va a seguir devolviendo 200 aunque Redis esté caído. Hay que ejercer un camino que sí dependa de Redis:

```bash
docker compose stop redis

# 1. Cache: debe fallar con un error de conexión visible, no degradarse en silencio
docker compose exec web python manage.py shell -c "
from django.core.cache import cache
cache.set('probe', 1)
"
# Debe levantar una excepción de conexión a Redis (ej. ConnectionError/RedisError), no
# completar en silencio ni caer a un fallback en memoria.

# 2. Channel layer / WS: recargar la app en el navegador y abrir un ticket con chat.
#    El badge de estado de notificaciones/WS debe marcar "desconectado" — no debe
#    quedar conectado con datos parciales.
```

Con Redis caído, tanto el cache como el channel layer deben fallar de forma ruidosa (excepción/errores visibles), confirmando que una caída de Redis se nota de inmediato en monitoreo, en vez de degradarse en silencio. Volver a levantar Redis y confirmar la recuperación:

```bash
docker compose start redis
```

Repetir el paso del cache (`cache.set`) y refrescar el navegador: el `cache.set` debe completar sin error y el badge de WS debe volver a "conectado".

## 5. Escalar `web`

Como el channel layer y el cache ya están en Redis (no in-process), `web` puede escalar a múltiples réplicas sin perder notificaciones ni sesiones WS:

```bash
docker compose up -d --scale web=2
```

nginx hace proxy a `web:8000` y Docker Compose resuelve ese nombre a todas las réplicas activas (round-robin por DNS interno).

Escalar solo **después** del primer deploy exitoso con `web=1`: las réplicas nuevas vuelven a correr `migrate`/`collectstatic` en el boot pero son no-op sobre un esquema ya migrado; si el arranque en frío se hace directamente con `web=2`, dos réplicas correrían `migrate` en paralelo sobre una base recién creada, lo cual es una condición de carrera evitable.

**`scheduler` SIEMPRE debe quedar en una sola réplica.** `check_sla --loop` no está diseñado para correr en paralelo — dos réplicas del scheduler generarían notificaciones/violaciones de SLA duplicadas. No agregar `--scale scheduler=N` con N>1. Esto es justamente lo que gatea `SLA_SCHEDULER_MODE`: en `web` queda en `"off"` (el scheduler in-process está apagado) porque el servicio `scheduler` dedicado es el único que corre `check_sla --loop`.

## 6. Troubleshooting

**El boot falla con `config.E001` o `config.E002`:**

Significa que falta una variable de entorno obligatoria en producción (`DJANGO_DEBUG=false` activa el guard `check --deploy` registrado en `backend/config/checks.py`, que corre automáticamente en el `entrypoint.sh` antes de levantar daphne):

- `config.E001`: falta `DJANGO_SECRET_KEY` (o quedó en el valor placeholder de dev) — completar `DJANGO_SECRET_KEY` en `.env` con un valor generado (ver sección 2) y volver a `docker compose up -d --build web`.
- `config.E002`: falta `DJANGO_ALLOWED_HOSTS` — completar con el dominio real en `.env`.

Nota: `check --deploy` también imprime los *warnings* propios de Django (por ejemplo `W008` sobre `SECURE_SSL_REDIRECT`, o similares) — esos **no** hacen fallar el boot, son solo informativos. Únicamente los `Error` (como `config.E001`/`E002`) detienen el arranque del contenedor.

**Redirect loop en staging http-only:**

Si el sitio está corriendo sin TLS (staging, o detrás de otro proxy externo que ya termina TLS) y el navegador entra en un loop de redirects, es porque `SECURE_SSL_REDIRECT=true` le pide a Django que redirija todo a HTTPS pero nada en la cadena está sirviendo HTTPS de verdad. Solución: poner `SECURE_SSL_REDIRECT=false` en el `.env` para ese entorno y reiniciar `web` (`docker compose up -d web`).

**`web` no levanta y no hay ningún error de `config.E00x` en los logs:**

Revisar `docker compose logs web` — puede ser que `mysql` todavía no esté healthy (el `depends_on: condition: service_healthy` debería evitarlo, pero si `mysql` tarda más de lo que tolera el `retries` del healthcheck, `web` puede arrancar antes de que la base esté lista). Reintentar con `docker compose up -d web` una vez que `docker compose ps` muestre `mysql` como healthy.

**`/static/` (estáticos del admin) da 404 en nginx:**

Confirmar que `collectstatic` corrió (variable `COLLECT_STATIC=true` en el servicio `web` del compose, ya seteada por default) y que el volumen `static_volume` está montado tanto en `web` (`/app/staticfiles`) como en `nginx` (`/staticfiles`, solo lectura) — son el mismo volumen con distinto path de montaje en cada contenedor, ver `docker-compose.yml`.
