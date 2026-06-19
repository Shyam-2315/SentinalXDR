# Backup and Restore

The production stack stores MongoDB and Redis data in Docker volumes:

- `sentinelxdr_prod_mongo_data`
- `sentinelxdr_prod_redis_data`
- `sentinelxdr_prod_evidence_data`

## MongoDB Backup

Create a compressed archive:

```bash
mkdir -p backups
docker compose --env-file .env.production -f docker-compose.prod.yml exec -T mongo \
  mongodump --archive --gzip --db sentinelxdr > backups/sentinelxdr-mongo-$(date +%Y%m%d-%H%M%S).archive.gz
```

If your `MONGODB_DATABASE` is not `sentinelxdr`, change the `--db` value.

## MongoDB Restore

Restore from an archive:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml exec -T mongo \
  mongorestore --archive --gzip --drop < backups/sentinelxdr-mongo-YYYYMMDD-HHMMSS.archive.gz
```

`--drop` replaces collections in the target database. Confirm the target environment before running it.

## Redis Backup

Redis appendonly persistence is enabled in production. To force a snapshot-style backup of Redis data:

```bash
mkdir -p backups
docker compose --env-file .env.production -f docker-compose.prod.yml exec -T redis redis-cli BGREWRITEAOF
docker run --rm \
  -v sentinelxdr-prod_sentinelxdr_prod_redis_data:/data:ro \
  -v "$PWD/backups:/backup" \
  alpine sh -c 'tar -czf /backup/sentinelxdr-redis-$(date +%Y%m%d-%H%M%S).tar.gz -C /data .'
```

Docker Compose prefixes named volumes with the project name. If your project name differs, list volumes with:

```bash
docker volume ls | grep sentinelxdr_prod_redis_data
```

## Redis Restore

Stop the stack, restore the Redis volume contents, then start the stack:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml down
docker run --rm \
  -v sentinelxdr-prod_sentinelxdr_prod_redis_data:/data \
  -v "$PWD/backups:/backup" \
  alpine sh -c 'rm -rf /data/* && tar -xzf /backup/sentinelxdr-redis-YYYYMMDD-HHMMSS.tar.gz -C /data'
docker compose --env-file .env.production -f docker-compose.prod.yml up -d
```

## Evidence File Backup

Evidence metadata, custody events, and hashes live in MongoDB. Evidence file bytes live in the evidence storage volume. Back up both at the same time for a consistent restore point.

```bash
mkdir -p backups
docker run --rm \
  -v sentinelxdr-prod_sentinelxdr_prod_evidence_data:/data:ro \
  -v "$PWD/backups:/backup" \
  alpine sh -c 'tar -czf /backup/sentinelxdr-evidence-$(date +%Y%m%d-%H%M%S).tar.gz -C /data .'
```

Restore evidence files after stopping the stack:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml down
docker run --rm \
  -v sentinelxdr-prod_sentinelxdr_prod_evidence_data:/data \
  -v "$PWD/backups:/backup" \
  alpine sh -c 'rm -rf /data/* && tar -xzf /backup/sentinelxdr-evidence-YYYYMMDD-HHMMSS.tar.gz -C /data'
docker compose --env-file .env.production -f docker-compose.prod.yml up -d
```

## Backup Checks

Periodically test restores in a non-production environment. A backup that has not been restored successfully should be treated as unproven.
