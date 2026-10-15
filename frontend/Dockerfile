FROM node:22-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

# Optional map tile settings, baked in at build time (see .env.example).
ARG VITE_TILE_URL=""
ARG VITE_TILE_ATTRIBUTION=""
ARG VITE_TILE_DARKEN="true"
ENV VITE_TILE_URL=$VITE_TILE_URL \
    VITE_TILE_ATTRIBUTION=$VITE_TILE_ATTRIBUTION \
    VITE_TILE_DARKEN=$VITE_TILE_DARKEN

COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
