FROM node:22-alpine AS dependencies
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-alpine AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=dependencies /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3005 HOSTNAME=0.0.0.0
RUN addgroup --system --gid 1001 careconnect && adduser --system --uid 1001 --ingroup careconnect careconnect
COPY --from=build --chown=careconnect:careconnect /app/.next/standalone ./
COPY --from=build --chown=careconnect:careconnect /app/.next/static ./.next/static
USER careconnect
EXPOSE 3005
CMD ["node", "server.js"]
