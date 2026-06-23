# syntax=docker/dockerfile:1
FROM node:20-alpine AS base

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci

COPY frontend/ .
COPY THIRD_PARTY_NOTICES.txt /usr/share/jpilot/THIRD_PARTY_NOTICES.txt

EXPOSE 5173

FROM base AS dev
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
