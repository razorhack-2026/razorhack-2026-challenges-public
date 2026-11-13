FROM rust:latest AS build

WORKDIR /usr/wasm
COPY ./src/wasm/ .

RUN cargo install wasm-pack && wasm-pack build --debug --target web

# Taken from `https://lipanski.com/posts/smallest-docker-image-static-website`
FROM busybox:1.35

# Create a non-root user to own the files and run our server
RUN adduser -D wasm
USER wasm
WORKDIR /home/wasm

COPY --from=build /usr/wasm/pkg ./pkg
COPY ./src/index.* ./src/helper.js ./
RUN ls

CMD ["busybox", "httpd", "-f", "-v"]
