# === CopIlot Builder stage: Compile HEVC-capable libraries ===
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

# Build libheif with libde265 and x265 support
RUN git clone https://github.com/strukturag/libheif.git && \
  cd libheif && mkdir build && cd build && \
  cmake .. -DCMAKE_INSTALL_PREFIX=/usr -DWITH_X265=ON -DWITH_LIBDE265=ON && \
  make -j$(nproc) && make install

# Build libvips from source using Meson
ENV VIPSVERSION=8.15.2
RUN curl -fL -o vips.tar.gz https://github.com/libvips/libvips/archive/refs/tags/v${VIPSVERSION}.tar.gz && \
  tar -xzf vips.tar.gz && cd libvips-${VIPSVERSION} && \
  meson setup build --prefix=/usr --buildtype=release && \
  meson compile -C build && \
  meson install -C build

# === Runtime stage: Lean production image with libvips + Node ===
FROM node:18-alpine

WORKDIR /app

# Runtime dependencies for custom libvips (including curl for test image)
RUN apk add --no-cache \
  libc6-compat libjpeg-turbo libpng libexif expat zlib curl

# Copy built libraries
COPY --from=builder /usr /usr

# Add test HEIC image for debugging/validation
RUN mkdir -p /test-images && \
  curl -fL -o /test-images/sample.heic https://github.com/alexcorvi/heic2any/raw/master/demo/flower.heic

# Copy app files
COPY package*.json ./
RUN npm ci --omit=dev
COPY *.js ./

# Environment variables for Sharp
ENV SHARP_IGNORE_GLOBAL_LIBVIPS=1
ENV NODE_ENV=production

# Create unprivileged user
RUN addgroup -g 1001 -S nodejs && adduser -S nodejs -u 1001
USER nodejs

EXPOSE 3001
CMD ["node", "api.js"]
