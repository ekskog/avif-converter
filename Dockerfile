# === Builder stage: Compile HEIC-capable toolchain ===
FROM alpine:3.20 AS builder

WORKDIR /build

RUN apk add --no-cache \
  build-base git curl cmake pkgconfig \
  meson ninja python3 \
  zlib-dev x265-dev libjpeg-turbo-dev libpng-dev libexif-dev expat-dev \
  aom-dev glib-dev gettext-dev ffmpeg-dev

# Build libde265 (HEVC decoder)
RUN git clone --depth=1 https://github.com/strukturag/libde265.git && \
  cd libde265 && mkdir build && cd build && \
  cmake .. -DCMAKE_INSTALL_PREFIX=/usr && \
  make -j$(nproc) && make install

# Build libheif with static codec support
RUN git clone --depth=1 https://github.com/strukturag/libheif.git && \
  cd libheif && mkdir build && cd build && \
  cmake .. -DCMAKE_INSTALL_PREFIX=/usr \
    -DWITH_X265=ON -DWITH_LIBDE265=ON \
    -DWITH_FFMPEG=ON -DENABLE_PLUGIN_LOADING=OFF && \
  make -j$(nproc) && make install

# Build libvips from Git (confirmed v8.14.5 tag)
RUN git clone --depth=1 --branch v8.14.5 https://github.com/libvips/libvips.git && \
  cd libvips && \
  meson setup build --prefix=/usr --buildtype=release && \
  meson compile -C build && \
  meson install -C build

# === Final image with Sharp + runtime deps ===
FROM node:18-alpine

WORKDIR /app

RUN apk add --no-cache \
  libc6-compat libjpeg-turbo libpng libexif expat zlib curl ffmpeg

# Copy over built libraries
COPY --from=builder /usr /usr

# App deps
COPY package*.json ./

# Build sharp using system libvips (the one we just compiled)
ENV SHARP_IGNORE_GLOBAL_LIBVIPS=0
ENV npm_config_build_from_source=true

RUN npm ci --omit=dev && npm rebuild sharp

# App source
COPY . .

# Optional cleanup
RUN npm cache clean --force

# Runtime config
ENV NODE_ENV=production

# Create a secure non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001
USER nodejs

# Healthcheck — make sure ./healthcheck.js exists
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD node healthcheck.js || exit 1

EXPOSE 3001
CMD ["node", "api.js"]
