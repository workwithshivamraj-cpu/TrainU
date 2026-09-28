# Build context is the repository root (see docker-compose.yml), so paths
# below are rooted at the repo, not at frontend/.
FROM node:20-alpine AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/. .
RUN npm run build -- --configuration production

FROM nginx:1.27-alpine
COPY --from=build /app/dist/frontend/browser /usr/share/nginx/html
COPY infrastructure/nginx/default.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
