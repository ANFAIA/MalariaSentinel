# ClickHouse for Raspberry Pi 4 — ARMv8.0 compatible build.
#
# Based on: https://github.com/sqooid/docker-clickhouse-pi4
# The official image needs ARMv8.2-A. Pi 4 has ARMv8.0-A (Cortex-A72).
# This uses the ARMv8.0 compat binary from builds.clickhouse.com.

FROM curlimages/curl AS downloader
WORKDIR /app
RUN curl -OL https://builds.clickhouse.com/master/aarch64v80compat/clickhouse

FROM ubuntu:20.04 AS glibc-donor
ARG TARGETARCH=arm64
RUN arch=${TARGETARCH:-arm64} \
  && case $arch in \
  amd64) rarch=x86_64 ;; \
  arm64) rarch=aarch64 ;; \
  esac \
  && ln -s "${rarch}-linux-gnu" /lib/linux-gnu

FROM alpine

ENV LANG=en_US.UTF-8 \
  LANGUAGE=en_US:en \
  LC_ALL=en_US.UTF-8 \
  TZ=UTC \
  CLICKHOUSE_CONFIG=/etc/clickhouse-server/config.xml

COPY --from=glibc-donor /lib/linux-gnu/libc.so.6 /lib/linux-gnu/libdl.so.2 /lib/linux-gnu/libm.so.6 /lib/linux-gnu/libpthread.so.0 /lib/linux-gnu/librt.so.1 /lib/linux-gnu/libnss_dns.so.2 /lib/linux-gnu/libnss_files.so.2 /lib/linux-gnu/libresolv.so.2 /lib/linux-gnu/ld-2.31.so /lib/
COPY --from=glibc-donor /etc/nsswitch.conf /etc/
COPY docker_related_config.xml /etc/clickhouse-server/config.d/
COPY config.xml /etc/clickhouse-server/config.xml
COPY users.xml /etc/clickhouse-server/users.xml
COPY entrypoint.sh /entrypoint.sh

ARG TARGETARCH
RUN arch=${TARGETARCH:-arm64} \
  && case $arch in \
  amd64) mkdir -p /lib64 && ln -sf /lib/ld-2.31.so /lib64/ld-linux-x86-64.so.2 ;; \
  arm64) ln -sf /lib/ld-2.31.so /lib/ld-linux-aarch64.so.1 ;; \
  esac

ARG DEFAULT_UID="101"
ARG DEFAULT_GID="101"
RUN addgroup -S -g "${DEFAULT_GID}" clickhouse && \
  adduser -S -h "/var/lib/clickhouse" -s /bin/bash -G clickhouse -g "ClickHouse server" -u "${DEFAULT_UID}" clickhouse

RUN cd /tmp \
  && for package in clickhouse-common-static; do \
  echo "Get https://packages.clickhouse.com/tgz/stable/${package}-24.8.2.3-${arch}.tgz" \
  && wget -c -q "https://packages.clickhouse.com/tgz/stable/${package}-24.8.2.3-${arch}.tgz" \
  ; done \
  && for file in *.tgz; do \
  if [ -f "$file" ]; then \
  echo "Unpacking $file"; \
  tar xvzf "$file" --strip-components=1 -C /; \
  fi \
  ; done \
  && rm /tmp/*.tgz \
  && chmod +x /entrypoint.sh \
  && apk add --no-cache bash tzdata \
  && cp /usr/share/zoneinfo/UTC /etc/localtime \
  && echo "UTC" > /etc/timezone

COPY --from=downloader /app/clickhouse /usr/bin/clickhouse
RUN chmod +x /usr/bin/clickhouse

RUN mkdir -p \
  /var/lib/clickhouse \
  /var/log/clickhouse-server \
  /etc/clickhouse-client \
  /etc/clickhouse-server/config.d \
  /etc/clickhouse-server/users.d \
  /docker-entrypoint-initdb.d \
  && chown clickhouse:clickhouse /var/lib/clickhouse \
  && chown root:clickhouse /var/log/clickhouse-server \
  && chmod ugo+Xrw -R /var/lib/clickhouse /var/log/clickhouse-server /etc/clickhouse-client /etc/clickhouse-server

VOLUME /var/lib/clickhouse
EXPOSE 9000 8123 9009

ENTRYPOINT ["/entrypoint.sh"]