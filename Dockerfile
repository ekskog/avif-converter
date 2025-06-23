# === Builder stage: Build HEIC-capable system libvips ===
FROM alpine:3.20 AS builder

WORKDIR /build

RUN apk add --no-cache \
  build-base git curl cmake pkgconfig \
  meson ninja python3 \
  zlib-dev x265-dev libjpeg-turbo-dev libpng-dev libexif-dev expat-dev \
  aom-dev glib-dev gettext-dev ffmpeg-dev

# libde265
RUN git clone --depth=1 https://github.com/strukturag/libde265 && \
  cd libde265 && mkdir build && cd build && \
  cmake .. -DCMAKE_INSTALL_PREFIX=/usr && \
  make -j$(nproc) && make install

# libheif with plugin loading disabled
RUN git clone --depth=1 https://github.com/strukturag/libheif && \
  cd libheif && mkdir build && cd build && \
  cmake .. -DCMAKE_INSTALL_PREFIX=/usr \
    -DWITH_X265=ON -DWITH_LIBDE265=ON \
    -DWITH_FFMPEG=ON -DENABLE_PLUGIN_LOADING=OFF && \
  make -j$(nproc) && make install

# libvips from Git
RUN git clone --depth=1 --branch v8.14.5 https://github.com/libvips/libvips.git && \
  cd libvips && \
  meson setup build --prefix=/usr --buildtype=release && \
  meson compile -C build && \
  meson install -C build

# === Final stage: Runtime with Node, Sharp, and system libvips ===
FROM node:18-alpine

WORKDIR /app

RUN apk add --no-cache \
  libc6-compat libjpeg-turbo libpng libexif expat zlib curl ffmpeg

# Copy HEIC-capable libraries
COPY --from=builder /usr /usr

# App deps
COPY package*.json ./

# Force Sharp to use our system libvips
ENV SHARP_IGNORE_GLOBAL_LIBVIPS=0
ENV npm_config_build_from_source=true

RUN npm ci --omit=dev && npm rebuild sharp

# App source
COPY . .

# Optional: clean up
RUN npm cache clean --force

# Runtime config
ENV NODE_ENV=production

# Secure non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001
USER nodejs

# Healthcheck script must exist in app root
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD node healthcheck.js || exit 1

EXPOSE 3001
CMD ["node", "api.js"]
