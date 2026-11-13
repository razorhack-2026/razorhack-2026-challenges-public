FROM alpine:3.24

# password here is unecessary but whatevs
RUN adduser -D -g "Iwakura Lain" iwakuralain && \
    echo "iwakuralain:3522dcd1b258b14f4a62f0d9c74962d00cc9e1e0a87bac10b7a1cd25ac54d39c" | chpasswd

COPY src/sshd_config /etc/ssh/
COPY src/authorized_keys /home/iwakuralain/.ssh/

RUN apk update && \
    apk add --no-cache openssh-server && \
    ssh-keygen -A && \
    chown iwakuralain -R /home/iwakuralain/.ssh && \
    chmod 755 /home/iwakuralain && \
    chmod 700 /home/iwakuralain/.ssh && \
    chmod 600 /home/iwakuralain/.ssh/authorized_keys


EXPOSE 22
CMD ["/usr/sbin/sshd", "-D"]

