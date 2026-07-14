FROM alpine:3.20
RUN apk add --no-cache openssl
COPY generate-certs.sh /certs/generate-certs.sh
RUN chmod +x /certs/generate-certs.sh
ENTRYPOINT ["/certs/generate-certs.sh"]
