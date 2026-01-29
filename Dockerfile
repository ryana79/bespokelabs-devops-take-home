FROM docker:24-dind

RUN apk add --no-cache bash curl ca-certificates tar gzip

RUN curl -sSL "https://github.com/k3d-io/k3d/releases/download/v5.6.0/k3d-linux-amd64" -o /usr/local/bin/k3d \
  && chmod +x /usr/local/bin/k3d

RUN curl -sSL "https://get.helm.sh/helm-v3.14.2-linux-amd64.tar.gz" \
  | tar -xz -C /tmp \
  && mv /tmp/linux-amd64/helm /usr/local/bin/helm

RUN curl -sSL "https://dl.k8s.io/release/v1.29.0/bin/linux/amd64/kubectl" -o /usr/local/bin/kubectl \
  && chmod +x /usr/local/bin/kubectl

WORKDIR /app
COPY wiki-service /app/wiki-service
COPY wiki-chart /app/wiki-chart
COPY start-cluster.sh /usr/local/bin/start-cluster.sh
RUN chmod +x /usr/local/bin/start-cluster.sh

EXPOSE 8080

ENTRYPOINT ["/usr/local/bin/start-cluster.sh"]
