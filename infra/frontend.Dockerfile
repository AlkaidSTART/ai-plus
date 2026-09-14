# syntax=docker/dockerfile:1.7

FROM node:24-bookworm-slim AS node

FROM oven/bun:1.4.2 AS build

COPY --from=node /usr/local/bin/node /usr/local/bin/node

WORKDIR /app

COPY frontend/package.json frontend/bun.lock ./
RUN bun install --frozen-lockfile

COPY frontend/ ./
RUN bun run build

FROM nginx:1.29-alpine

COPY infra/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
