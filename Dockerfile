# === Builder Stage ===
FROM alpine:3.20 as builder

WORKDIR /build

# Install build dependencies
RUN apk add --no-cache \
  build-base curl git cmake pkgconfig \
  meson ninja python3 \
  zlib-dev x265-dev libjpeg-turbo-dev libpng-dev libexif-dev expat-dev \
  aom-dev glib-dev gettext-dev ffmpeg-dev \
  lcms2-dev libxml2-dev orc-dev

# Build libde265
RUN git clone --depth=1 https://github.com/strukturag/libde265.git && \
  cd libde265 && mkdir build && cd build && \
  cmake .. -DCMAKE_INSTALL_PREFIX=/usr && \
  make -j$(nproc) && make install

# Build libheif with plugin loading disabled
RUN git clone --depth=1 https://github.com/strukturag/libheif.git && \
  cd libheif && mkdir build && cd build && \
  cmake .. -DCMAKE_INSTALL_PREFIX=/usr \
    -DWITH_X265=ON -DWITH_LIBDE265=ON -DWITH_FFMPEG=ON \
    -DENABLE_PLUGIN_LOADING=OFF && \
  make -j$(nproc) && make install

# Build libvips from official tarball (stable version)
ENV VIPS_VERSION=8.14.5
RUN curl -LO https://github.com/libvips/libvips/releases/download/v${VIPS_VERSION}/vips-${VIPS_VERSION}.tar.gz && \
    tar xzf vips-${VIPS_VERSION}.tar.gz && cd vips-${VIPS_VERSION} && \
    meson setup build --prefix=/usr --buildtype=release && \
    meson compile -C build && \
    meson install -C build

# === Runtime Stage ===
FROM node:18-alpine

WORKDIR /app

# Install runtime dependencies
RUN apk add --no-cache \
  libc6-compat libjpeg-turbo libpng libexif expat zlib ffmpeg

# Copy compiled libraries from builder
COPY --from=builder /usr /usr

# Copy app package files
COPY package*.json ./

# Build sharp from source using system libvips
ENV SHARP_IGNORE_GLOBAL_LIBVIPS=0
ENV npm_config_build_from_source=true

RUN npm ci --omit=dev && npm rebuild sharp

# Copy rest of app source
COPY . .

# Clean up
RUN npm cache clean --force

# Use non-root user
RUN addgroup -g 1001 -S nodejs && adduser -S nodejs -u 1001
USER nodejs

ENV NODE_ENV=production

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD node healthcheck.js || exit 1

EXPOSE 3001
CMD ["node", "api.js"]
