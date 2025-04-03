FROM node:latest-alpine as build

WORKDIR /app

COPY package.json package-lock.json ./

RUN npm install -g @angular/cli && npm install

COPY . .

# Build the application
RUN ng build

# Default to port 4200, but can be overridden
EXPOSE 4200 

# Run the server with HTTPS enabled
CMD ["sh", "-c", "USE_HTTPS=true node dist/test-project-app/server/server.mjs"]