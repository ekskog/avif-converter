# PhotoVault Image Converter Service

A standalone Node.js microservice for converting images (HEIC, PNG, JPEG) to AVIF format. Provides a REST API for image conversion with multiple output variants.

## Features

- Converts HEIC/HEIF files to AVIF format
- Converts PNG/JPEG files to AVIF format  
- Generates two variants: full-size and thumbnail (300x300)
- Preserves EXIF metadata where possible
- Memory-efficient processing with timeout protection
- HTTP REST API for microservice integration

## Installation

```bash
npm install
```

## Usage

### Start the HTTP API Server

```bash
npm start
```

The server will start on port 3002 (or the port specified in the PORT environment variable).

### API Endpoints

#### Health Check
```bash
GET /health
```

#### Convert Image
```bash
POST /convert
```

**Request**: Multipart form with an image file in the `image` field

**Optional Parameters**:
- `returnContents=true` - Returns base64-encoded file contents instead of file paths

### Examples

```bash
# Convert HEIC file
curl -X POST -F "image=@photo.heic" http://localhost:3002/convert

# Convert PNG file with contents returned
curl -X POST -F "image=@image.png" -F "returnContents=true" http://localhost:3002/convert

# Convert JPEG file
curl -X POST -F "image=@picture.jpg" http://localhost:3002/convert
```

### Response Format

**Success Response**:
```json
{
  "success": true,
  "message": "Image converted successfully",
  "files": [
    {
      "variant": "full",
      "filename": "image_full.avif",
      "size": "1.2 MB",
      "file": "/path/to/output/image_full.avif"
    },
    {
      "variant": "thumbnail", 
      "filename": "image_thumbnail.avif",
      "size": "45.3 KB",
      "file": "/path/to/output/image_thumbnail.avif"
    }
  ]
}
```

**With returnContents=true**:
```json
{
  "success": true,
  "message": "Image converted successfully", 
  "files": [
    {
      "variant": "full",
      "filename": "image_full.avif",
      "size": 1234567,
      "sizeFormatted": "1.2 MB",
      "mimetype": "image/avif",
      "content": "base64-encoded-file-data..."
    }
  ]
}
```

### Output

The converter generates two AVIF variants:
- **Full-size**: Original dimensions with 90% quality
- **Thumbnail**: 300x300 pixels with 80% quality

## Supported Formats

- **Input**: HEIC, HEIF, PNG, JPEG, JPG
- **Output**: AVIF (optimized for web delivery)

## Requirements

- Node.js >= 18.0.0
- Sharp library with HEIC support
- heic-convert library

## Development

This service maintains the exact same image processing functionality as the original heic-processor from the PhotoVault API, now exposed through a REST API for microservice deployment.

### Running in Development
```bash
npm run dev
```

## Docker Deployment

### Build Docker Image
```bash
docker build -t photovault-avif-converter .
```

### Run Container
```bash
docker run -p 3002:3002 photovault-avif-converter
```

## API Integration

This microservice is designed to be integrated with other services. Example integration:

```javascript
const FormData = require('form-data');
const fs = require('fs');

async function convertImage(imagePath) {
  const form = new FormData();
  form.append('image', fs.createReadStream(imagePath));
  form.append('returnContents', 'true');
  
  const response = await fetch('http://localhost:3002/convert', {
    method: 'POST',
    body: form
  });
  
  return await response.json();
}
```
