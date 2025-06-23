// HEIC Processing Module for PhotoVault API
const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

class HeicProcessor {
  constructor() {
    // Use heic-convert library which has better HEIC codec support
    this.heicSupported = true; // heic-convert always works
  }

  /**
   * Process HEIC file and generate multiple formats/sizes
   * @param {Buffer} heicBuffer - Original HEIC file buffer
   * @param {string} fileName - Original filename
   * @returns {Object} Processed variants
   */
  async processHeicFile(heicBuffer, fileName) {
    console.log(`Processing HEIC file...`);
    
    // Check file size limit to prevent memory issues
    const maxSizeMB = 100; // 100MB limit
    const fileSizeMB = heicBuffer.length / 1024 / 1024;
    if (fileSizeMB > maxSizeMB) {
      throw new Error(`File too large: ${fileSizeMB.toFixed(2)}MB. Maximum allowed: ${maxSizeMB}MB`);
    }
    
    if (!this.heicSupported) {
      throw new Error('HEIC processing not supported - please install libheif');
    }

    const baseName = path.parse(fileName).name;
    const results = {};

    try {
      // First convert HEIC to JPEG using heic-convert with timeout
      console.log('Converting HEIC to JPEG...');
      const jpegBuffer = await Promise.race([
        heicConvert({
          buffer: heicBuffer,
          format: 'JPEG',
          quality: 1 // Use maximum quality for initial conversion
        }),
        new Promise((_, reject) => setTimeout(() => reject(new Error('HEIC conversion timeout')), 120000)) // 2 minutes timeout
      ]);
      console.log('HEIC conversion complete');

      // Then use Sharp to create variants from the JPEG
      const image = sharp(jpegBuffer);
      const metadata = await image.metadata();

      // Generate full-size AVIF and thumbnail variants
      const variants = [
        {
          name: 'full',
          width: null, // Keep original dimensions
          height: null,
          quality: 90,
          format: 'avif'
        },
        {
          name: 'thumbnail',
          width: 300,
          height: 300,
          quality: 80,
          format: 'avif'
        }
      ];

      // Process each variant with timeout protection
      for (const variant of variants) {
        console.log(`Creating ${variant.name} variant...`);
        let processedBuffer;
        
        try {
          if (variant.name === 'full') {
            // For full-size, just convert format without resizing, preserve metadata
            processedBuffer = await Promise.race([
              image
                .rotate() // Auto-rotate based on EXIF orientation data
                .withMetadata() // Preserve EXIF metadata
                .heif({ quality: variant.quality, compression: 'av1' })
                .toBuffer(),
              new Promise((_, reject) => setTimeout(() => reject(new Error('Sharp processing timeout')), 180000)) // 3 minutes timeout
            ]);
          } else if (variant.name === 'thumbnail') {
            // For thumbnail, resize and convert
            processedBuffer = await Promise.race([
              image
                .rotate() // Auto-rotate based on EXIF orientation data
                .resize(variant.width, variant.height, { 
                  fit: 'cover', 
                  position: 'center' 
                })
                .withMetadata() // Preserve EXIF metadata for thumbnails too
                .heif({ quality: variant.quality, compression: 'av1' })
                .toBuffer(),
              new Promise((_, reject) => setTimeout(() => reject(new Error('Sharp processing timeout')), 60000)) // 1 minute timeout for thumbnails
            ]);
          }
        } catch (variantError) {
          console.error(`Failed to create ${variant.name} variant:`, variantError.message);
          continue; // Skip this variant but continue with others
        }

        const filename = `${baseName}_${variant.name}.${variant.format === 'avif' ? 'avif' : variant.format}`;
        const mimetype = `image/${variant.format === 'avif' ? 'avif' : variant.format}`;
        console.log(`✓ Generated ${variant.name}: ${filename} (${(processedBuffer.length / 1024).toFixed(2)}KB)`);

        results[variant.name] = {
          buffer: processedBuffer,
          filename: filename,
          size: processedBuffer.length,
          mimetype: mimetype,
          dimensions: variant.name === 'full' ? {
            width: metadata.width || 'unknown',
            height: metadata.height || 'unknown'
          } : {
            width: variant.width,
            height: variant.height
          }
        };
      }
      
      console.log(`HEIC processing completed: ${Object.keys(results).length} variants created`);
      
      // Force garbage collection if available
      if (global.gc) {
        global.gc();
      }
      
      return results;

    } catch (error) {
      console.error(`HEIC processing failed:`, error.message);
      
      // Force garbage collection on error
      if (global.gc) {
        global.gc();
      }
      
      throw new Error(`HEIC processing failed: ${error.message}`);
    }
  }

  /**
   * Quick HEIC to AVIF conversion for immediate use
   * @param {Buffer} heicBuffer 
   * @param {Object} options 
   */
  async quickConvert(heicBuffer, options = {}) {
    const {
      quality = 85,
      maxWidth = 1200,
      maxHeight = 1200,
      format = 'avif' // Default to AVIF for better compression
    } = options;

    if (!this.heicSupported) {
      throw new Error('HEIC processing not supported');
    }

    // First convert HEIC to JPEG using heic-convert
    const jpegBuffer = await heicConvert({
      buffer: heicBuffer,
      format: 'JPEG',
      quality: 1 // Use maximum quality for intermediate conversion
    });

    // Then convert to desired format (AVIF/JPEG) and optionally resize with Sharp
    let sharpImage = sharp(jpegBuffer);
    
    if (maxWidth || maxHeight) {
      sharpImage = sharpImage.resize(maxWidth, maxHeight, {
        fit: 'inside',
        withoutEnlargement: true
      });
    }

    if (format === 'avif') {
      return await sharpImage.heif({ quality, compression: 'av1' }).toBuffer();
    } else {
      return await sharpImage.jpeg({ quality }).toBuffer();
    }
  }

  /**
   * Convert any image buffer to AVIF (for testing and general use)
   * @param {Buffer} imageBuffer 
   * @param {Object} options 
   */
  async convertToAvif(imageBuffer, options = {}) {
    const {
      quality = 85,
      maxWidth = 1200,
      maxHeight = 1200
    } = options;

    let sharpImage = sharp(imageBuffer);
    
    if (maxWidth || maxHeight) {
      sharpImage = sharpImage.resize(maxWidth, maxHeight, {
        fit: 'inside',
        withoutEnlargement: true
      });
    }

    return await sharpImage
      .rotate() // Auto-rotate based on EXIF orientation data
      .withMetadata() // Preserve EXIF metadata
      .heif({ quality, compression: 'av1' })
      .toBuffer();
  }

  /**
   * Check if file is HEIC format
   */
  static isHeicFile(filename) {
    return /\.(heic|heif)$/i.test(filename);
  }

  /**
   * Get Sharp installation instructions
   */
  static getInstallInstructions() {
    return `
To enable HEIC processing, install Sharp with HEIC support:

npm uninstall sharp
npm install --platform=darwin --arch=x64 sharp
# or for Linux:
# npm install --platform=linux --arch=x64 sharp

For production, you may also need:
sudo apt-get install libheif-dev  # Ubuntu/Debian
# or
brew install libheif  # macOS
    `;
  }
}

/**
 * Process image file: HEIC -> AVIF variants (full + thumbnail)
 * @param {string} inputPath - Path to input image file (HEIC or other)
 * @param {string} outputDir - Directory to save output AVIF files
 * @returns {Object} Result object with success status and file info
 */
async function processImage(inputPath, outputDir) {
  try {
    // Validate input file exists
    if (!fs.existsSync(inputPath)) {
      throw new Error(`Input file does not exist: ${inputPath}`);
    }

    // Create output directory if it doesn't exist
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }

    // Read input file
    const inputBuffer = fs.readFileSync(inputPath);
    const fileName = path.basename(inputPath);

    // Initialize processor
    const processor = new HeicProcessor();
    
    // Determine if it's a HEIC file
    const isHeic = HeicProcessor.isHeicFile(fileName);
    let results;

    if (isHeic) {
      // Process HEIC file (creates full + thumbnail variants)
      results = await processor.processHeicFile(inputBuffer, fileName);
    } else {
      // For non-HEIC files, use convertToAvif to create similar variants
      const baseName = path.parse(fileName).name;
      
      // Create full-size variant
      const fullBuffer = await processor.convertToAvif(inputBuffer, { 
        quality: 90,
        maxWidth: null,
        maxHeight: null 
      });
      
      // Create thumbnail variant
      const thumbnailBuffer = await processor.convertToAvif(inputBuffer, {
        quality: 80,
        maxWidth: 300,
        maxHeight: 300
      });

      results = {
        full: {
          buffer: fullBuffer,
          filename: `${baseName}_full.avif`,
          size: fullBuffer.length,
          mimetype: 'image/avif'
        },
        thumbnail: {
          buffer: thumbnailBuffer,
          filename: `${baseName}_thumbnail.avif`,
          size: thumbnailBuffer.length,
          mimetype: 'image/avif'
        }
      };
    }

    // Save all variants to output directory
    const savedFiles = [];
    for (const [variantName, variant] of Object.entries(results)) {
      const outputPath = path.join(outputDir, variant.filename);
      fs.writeFileSync(outputPath, variant.buffer);
      savedFiles.push({
        variant: variantName,
        file: outputPath,
        size: `${(variant.size / 1024).toFixed(2)}KB`
      });
    }

    return { success: true, files: savedFiles };

  } catch (error) {
    return { success: false, error: error.message };
  }
}

module.exports = { HeicProcessor, processImage };
