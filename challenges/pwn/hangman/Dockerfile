FROM gcc:4.9

WORKDIR /app
COPY src/hangman.c .
RUN gcc hangman.c -fno-stack-protector -std=c11 -static -o hangman


FROM alpine:3.24

RUN apk add --no-cache python3 socat
WORKDIR /app
COPY --from=0 /app/hangman .
COPY src/dictionary.txt src/test_dict.txt src/start.sh .
RUN chmod +x /app/hangman /app/start.sh
# Run as non-root; only use ports >=1024

USER nobody
ENV PORTS=10001,10002,10003,10004,10005,10006,10007,10008,10009,10010,10011,10012,10013,10014,10015,10016,10017,10018,10019,10020,10021,10022,10023,10024,10025,10026,10027,10028,10029,10030,10031,10032,10033,10034
EXPOSE 10001-10034

CMD ["/app/start.sh"]
