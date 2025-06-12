# PhotoVault Image Converter Service

A standalone Node.js service for converting images (HEIC, PNG, JPEG) to AVIF format. Extracted from the PhotoVault API to run as an independent microservice.

## Features

- Converts HEIC/HEIF files to AVIF format
- Converts PNG/JPEG files to AVIF format  
- Generates two variants: full-size and thumbnail (300x300)
- Preserves EXIF metadata where possible
- Memory-efficient processing with timeout protection
- Command-line interface for testing

## Installation

```bash
npm install
```

## Usage

### Command Line Interface

```bash
node cli.js <input-file> <output-directory>
```

### Examples

```bash
# Convert HEIC file
node cli.js photo.heic ./output/

# Convert PNG file  
node cli.js image.png ./converted/

# Convert JPEG file
node cli.js picture.jpg /tmp/output/
```

### Output

The converter will generate two files:
- `filename_full.avif` - Full-size converted image
- `filename_thumbnail.avif` - 300x300 thumbnail

## Supported Formats

- **Input**: HEIC, HEIF, PNG, JPEG, JPG
- **Output**: AVIF (optimized for web delivery)

## Requirements

- Node.js >= 18.0.0
- Sharp library with HEIC support
- heic-convert library

## Development

This service maintains the exact same functionality as the original heic-processor from the PhotoVault API, ensuring consistent image processing behavior.

## Future Plans

- HTTP API interface for microservice deployment
- Kubernetes deployment configuration
- Docker containerization
