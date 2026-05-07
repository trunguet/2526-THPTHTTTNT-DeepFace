FROM mysql:8.4
RUN microdnf install -y bash tar gzip findutils && microdnf clean all
WORKDIR /app
COPY backup.sh /app/backup.sh
RUN chmod +x /app/backup.sh
ENTRYPOINT ["/app/backup.sh"]