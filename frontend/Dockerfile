# ==============================================================================
# Stage 1: Build the React/Vite application
# ==============================================================================
FROM node:18-alpine AS build

# Set the working directory
WORKDIR /app

# Copy package management files
# This leverages Docker's layer caching. These layers are only rebuilt if these files change.
COPY package*.json ./
# If using Bun, you may also copy bun.lockb (optional).
COPY bun.lockb ./

# Install dependencies. Use `npm install` here because `npm ci` requires a
# package-lock.json file which is not present in this repository. Installing
# devDependencies is necessary for the production build (Vite, TypeScript, etc.).
RUN npm install

# Copy the rest of the application source code
COPY . .

# Build argument for the API Gateway URL
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# Build the application for production.
# This creates a static 'dist' folder with optimized assets.
RUN npm run build

# ==============================================================================
# Stage 2: Serve the built application with Nginx
# ==============================================================================
FROM nginx:alpine

# Install curl, which is required for the HEALTHCHECK command
RUN apk add --no-cache curl

# Copy the built static assets from the 'build' stage into the Nginx public directory
COPY --from=build /app/dist /usr/share/nginx/html

# Copy the custom Nginx configuration file.
# This is crucial for correctly routing a Single-Page Application (SPA).
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose the port that Nginx will be configured to listen on.
# This MUST match the port in nginx.conf and the HEALTHCHECK.
EXPOSE 5100

# Health check to ensure the Nginx server is running and responding.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5100 || exit 1

# The main command to start the Nginx server in the foreground.
CMD ["nginx", "-g", "daemon off;"]