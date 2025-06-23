# === Builder stage: Compile HEVC-capable libraries ===
FROM alpine:3.20 AS builder

WORKDIR /build

# Install build tools and dependencies
RUN apk add --no-cache \
  build-base git curl cmake pkgconfig \
  zlib-dev x265-dev libjpeg-turbo-dev libpng-dev libexif-dev expat-dev \
  aom-dev glib-dev

# Build libde265 (HEVC decoder)
RUN git clone https://github.com/strukturag/libde265.git && \
  cd libde265 && mkdir build && cd build && \
  cmake .. -DCMAKE_INSTALL_PREFIX=/usr && \
  make -j$(nproc) && make install

# Build libheif with libde265 and x265 support
RUN git clone https://github.com/strukturag/libheif.git && \
  cd libheif && mkdir build && cd build && \
  cmake .. -DCMAKE_INSTALL_PREFIX=/usr -DWITH_X265=ON -DWITH_LIBDE265=ON && \
  make -j$(nproc) && make install

# Build libvips
RUN curl -fL -o vips.tar.gz https://github.com/libvips/libvips/releases/download/v8.15.2/vips-8.15.2.tar.gz && \
  tar -xzf vips.tar.gz && cd vips-8.15.2 && \
  ./configure --prefix=/usr && make -j$(nproc) && make install

# === Runtime stage: Alpine + custom libvips + app ===
FROM node:18-alpine

WORKDIR /app

# Runtime dependencies for custom libvips
RUN apk add --no-cache \
  libc6-compat libjpeg-turbo libpng libexif expat zlib

# Copy built libraries from builder stage
COPY --from=builder /usr /usr

# Copy application and install dependencies
COPY package*.json ./
RUN npm ci --omit=dev
COPY *.js ./

# Environment setup for sharp
ENV SHARP_IGNORE_GLOBAL_LIBVIPS=1
ENV NODE_ENV=production

# Create secure non-root user
RUN addgroup -g 1001 -S nodejs && adduser -S nodejs -u 1001
USER nodejs

EXPOSE 3001
CMD ["node", "api.js"]
