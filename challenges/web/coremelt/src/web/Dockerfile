# CoreWatch — deliberately vulnerable ICARUS reactor console.
# Pinned to next@15.0.3 / react@19.0.0 for CVE-2025-55182 ("React2Shell").
# DO NOT `npm update` or bump these — the challenge REQUIRES the vulnerable
# RSC Flight deserializer. A future maintainer "fixing" the versions kills it.
FROM node:20-slim
RUN apt-get update -qq && DEBIAN_FRONTEND=noninteractive \
      apt-get install -y -qq python3 sqlite3 openssl openssh-client >/dev/null 2>&1
WORKDIR /app
COPY package.json ./
# next@15.0.3 pins its react peer to an RC; react@19.0.0 stable is the vulnerable
# pairing we want, so --legacy-peer-deps is required (not an oversight).
RUN npm install --no-audit --no-fund --legacy-peer-deps
COPY next.config.mjs tsconfig.json middleware.ts ./
COPY app ./app
COPY lib ./lib
RUN npm run build
# -- challenge artifacts: loot DB (+ encrypted engineer memo), config, flags --
COPY seed_db.py c2_memo.txt ./
# Seed the DB and encrypt the engineer memo INTO it with the reused password.
# Then delete the plaintext memo + seed script so the running container ships
# only ciphertext — the memo flag is recoverable only by cracking the hash.
RUN python3 seed_db.py /app/corewatch.db c2_memo.txt supernova1 \
 && rm -f c2_memo.txt seed_db.py
COPY .env ./.env
COPY flag.txt /flag.txt
RUN chmod 644 /flag.txt /app/corewatch.db /app/.env && chown -R node:node /app
USER node
EXPOSE 3000
CMD ["npm","run","start"]
