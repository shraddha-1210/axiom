# Use an official Node runtime as a parent image
FROM node:20-alpine

# Set the working directory in the container
WORKDIR /app

# Copy package.json and package-lock.json (if available)
COPY package*.json ./

# Install dependencies
# RUN npm install # Uncomment when package.json is initialized

# Copy the rest of the application files
COPY . .

# Expose port 3000
EXPOSE 3000

# Start the Next.js development server
# CMD ["npm", "run", "dev"] # Uncomment when Next.js app is generated

# Temporary command to keep the container running until Next.js app is set up
CMD ["tail", "-f", "/dev/null"]
