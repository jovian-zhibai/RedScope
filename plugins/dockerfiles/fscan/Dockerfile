FROM golang:1.22-alpine AS builder
RUN apk add --no-cache git
RUN git clone --depth 1 https://github.com/shadow1ng/fscan.git /src && \
    cd /src && go build -o /fscan .

FROM alpine:3.19
COPY --from=builder /fscan /usr/local/bin/fscan
RUN chmod +x /usr/local/bin/fscan
ENTRYPOINT ["fscan"]
