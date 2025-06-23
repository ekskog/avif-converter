# === Builder stage: Compile HEVC-capable libraries ===
FROM alpine:3.20 AS builder

WORKDIR /build

# Install build tools and dependencies
RUN apk add --no-cache \
  build-base git curl cmake pkgconfig \
  meson ninja python3 \
  zlib-dev x265-dev libjpeg-turbo-dev libpng-dev libexif-dev expat-dev \
  aom-dev glib-dev gettext-dev

# Build libde265 (HEVC decoder)
RUN git clone https://github.com/strukturag/libde265.git && \
  cd libde265 && mkdir build && cd build && \
  cmake .. -DCMAKE_INSTALL_PREFIX=/usr && \
  make -j$(nproc) && make install

# Build libheif with embedded codec support (no plugin loading)
RUN git clone https://github.com/strukturag/libheif.git && \
  cd libheif && mkdir build && cd build && \
  cmake .. -DCMAKE_INSTALL_PREFIX=/usr \
    -DWITH_X265=ON -DWITH_LIBDE265=ON -DENABLE_PLUGIN_LOADING=OFF && \
  make -j$(nproc) && make install

# Build libvips from source using Meson
ENV VIPSVERSION=8.15.2
RUN curl -fL -o vips.tar.gz https://github.com/libvips/libvips/archive/refs/tags/v${VIPSVERSION}.tar.gz && \
  tar -xzf vips.tar.gz && cd libvips-${VIPSVERSION} && \
  meson setup build --prefix=/usr --buildtype=release && \
  meson compile -C build && \
  meson install -C build

# === Runtime stage: Production Node + libvips + healthcheck ===
FROM node:18-alpine

WORKDIR /app

# Install runtime dependencies
RUN apk add --no-cache \
  libc6-compat libjpeg-turbo libpng libexif expat zlib curl

# Copy compiled libraries
COPY --from=builder /usr /usr

# Copy app files and test HEIC
COPY package*.json ./
RUN npm ci --omit=dev
COPY . .

# Set environment variables for Sharp to use system libvips
ENV SHARP_IGNORE_GLOBAL_LIBVIPS=1
ENV NODE_ENV=production

# Create secure non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001
USER nodejs

# Add healthcheck (uses healthcheck.js)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD node healthcheck.js || exit 1

EXPOSE 3001
CMD ["node", "api.js"]
