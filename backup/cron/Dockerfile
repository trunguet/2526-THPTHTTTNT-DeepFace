FROM alpine:3.20

RUN apk add --no-cache bash curl postgresql-client aws-cli ca-certificates \
    && curl -fsSL https://github.com/aptible/supercronic/releases/download/v0.2.30/supercronic-linux-amd64 \
        -o /usr/local/bin/supercronic \
    && chmod +x /usr/local/bin/supercronic

COPY backup.sh /usr/local/bin/backup.sh
COPY backup.cron /etc/supercronic/backup.cron

RUN chmod +x /usr/local/bin/backup.sh

ENV AWS_EC2_METADATA_DISABLED=true

CMD ["/usr/local/bin/supercronic", "/etc/supercronic/backup.cron"]
