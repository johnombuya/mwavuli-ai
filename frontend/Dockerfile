# Frontend Dockerfile
FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy application
COPY . .

# Expose port
EXPOSE 3000

# Run development server
# For production, use: RUN npm run build && npm start
CMD ["npm", "run", "dev"]
