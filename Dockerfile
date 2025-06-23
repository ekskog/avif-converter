# === Builder stage: Compile dependencies with HEVC support ===
FROM alpine:3.20 AS builder

WORKDIR /build

# Install build tools & dependencies
RUN apk add --no-cache \
    build-base git curl pkgconfig autoconf automake libtool cmake nasm yasm \
    zlib-dev x265-dev libjpeg-turbo-dev libpng-dev libexif-dev expat-dev \
    aom-dev

# Build libde265
RUN git clone https://github.com/strukturag/libde265.git && \
    cd libde265 && ./autogen.sh && ./configure --prefix=/usr && make -j$(nproc) && make install

# Build libheif with libde265 and x265 support
RUN git clone https://github.com/strukturag/libheif.git && \
    cd libheif && ./autogen.sh && \
    ./configure --prefix=/usr --enable-x265 --enable-libde265 && \
    make -j$(nproc) && make install

# Build libvips
RUN curl -LO https://github.com/libvips/libvips/releases/download/v8.15.2/vips-8.15.2.tar.gz && \
    tar -xzf vips-8.15.2.tar.gz && cd vips-8.15.2 && \
    ./configure --prefix=/usr && make -j$(nproc) && make install

# === Runtime stage: Lean Node app with sharp + HEVC-ready vips ===
FROM node:18-alpine

WORKDIR /app

# Install vips runtime dependencies
RUN apk add --no-cache \
    libc6-compat libjpeg-turbo libpng libexif expat zlib

# Copy custom vips + heif libs from builder
COPY --from=builder /usr /usr

# Copy app source and dependencies
COPY package*.json ./
RUN npm ci --omit=dev

COPY *.js ./

# Set sharp env vars
ENV SHARP_IGNORE_GLOBAL_LIBVIPS=1
ENV NODE_ENV=production

# Create secure user
RUN addgroup -g 1001 -S nodejs && adduser -S nodejs -u 1001
USER nodejs

EXPOSE 3001

CMD ["node", "api.js"]
