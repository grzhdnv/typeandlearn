# Multi-stage build for TypeAndLearn SolidJS frontend
FROM node:22-alpine AS builder

WORKDIR /app

COPY apps/frontend/package*.json ./
RUN npm ci

COPY apps/frontend ./
RUN npm run build

# Runtime stage: serve static assets with Nginx
FROM nginx:alpine-slim AS runner

COPY --from=builder /app/dist /usr/share/nginx/html
COPY apps/frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
