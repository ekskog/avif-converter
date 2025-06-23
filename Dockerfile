# === Builder stage ===
FROM alpine:3.20 AS builder

WORKDIR /build

RUN apk add --no-cache \
  build-base git curl cmake pkgconfig \
  meson ninja python3 \
  zlib-dev x265-dev libjpeg-turbo-dev libpng-dev libexif-dev expat-dev \
  aom-dev glib-dev gettext-dev

# Build libde265
RUN git clone https://github.com/strukturag/libde265.git && \
  cd libde265 && mkdir build && cd build && \
  cmake .. -DCMAKE_INSTALL_PREFIX=/usr && \
  make -j$(nproc) && make install

# Build libheif with static codec support (HEVC / libde265) and plugin loading disabled
RUN git clone https://github.com/strukturag/libheif.git && \
  cd libheif && mkdir build && cd build && \
  cmake .. -DCMAKE_INSTALL_PREFIX=/usr \
    -DWITH_X265=ON -DWITH_LIBDE265=ON \
    -DENABLE_PLUGIN_LOADING=OFF && \
  make -j$(nproc) && make install

# Build libvips
ENV VIPSVERSION=8.15.2
RUN curl -LO https://github.com/libvips/libvips/releases/download/v${VIPSVERSION}/vips-${VIPSVERSION}.tar.gz && \
  tar xzf vips-${VIPSVERSION}.tar.gz && cd vips-${VIPSVERSION} && \
  meson setup build --prefix=/usr --buildtype=release && \
  meson compile -C build && \
  meson install -C build

# === Final image ===
FROM node:18-alpine

WORKDIR /app

RUN apk add --no-cache \
  libc6-compat libjpeg-turbo libpng libexif expat zlib curl bash

# Copy compiled image libraries
COPY --from=builder /usr /usr

# Copy app files
COPY package*.json ./

# ⚠️ Tell sharp to build against system libvips
ENV SHARP_IGNORE_GLOBAL_LIBVIPS=0
ENV npm_config_build_from_source=true

# Install and rebuild sharp properly
RUN npm ci --omit=dev && npm rebuild sharp

# Copy app source
COPY . .

# Optional: remove dev artifacts to slim image
RUN npm cache clean --force

# Runtime
ENV NODE_ENV=production

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001
USER nodejs

# Built-in healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD node healthcheck.js || exit 1

EXPOSE 3001
CMD ["node", "api.js"]
