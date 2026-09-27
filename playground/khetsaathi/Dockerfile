# KhetSaathi: zero-dependency Node app. Build: docker build -t khetsaathi .
FROM node:22-alpine
WORKDIR /app
COPY package.json server.js ./
COPY public ./public
ENV NODE_ENV=production PORT=8080 DATA_FILE=/data/db.json
# DEMO_MODE=1 shows OTPs on screen and seeds sample data. Set DEMO_MODE=0 once SMS is wired.
ENV DEMO_MODE=1
VOLUME /data
EXPOSE 8080
USER node
HEALTHCHECK CMD wget -qO- http://localhost:8080/api/health || exit 1
CMD ["node", "server.js"]
