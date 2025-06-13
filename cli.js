#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const HeicProcessor = require('./server');

// CLI Usage function
function showUsage() {
  console.log(`
PhotoVault Image Converter CLI
Usage: node cli.js <input-file> <output-directory>

Arguments:
  input-file       Path to input image file (HEIC, PNG, JPEG)
  output-directory Directory where converted files will be saved

Examples:
  node cli.js photo.heic ./output/
  node cli.js image.png /path/to/output/

Supported formats:
  Input:  HEIC, HEIF, PNG, JPEG, JPG
  Output: AVIF (full-size and thumbnail variants)
`);
}

// Main processing function
async function processImage(inputPath, outputDir) {
  try {
    // Validate input file exists
    if (!fs.existsSync(inputPath)) {
      throw new Error(`Input file does not exist: ${inputPath}`);
    }

    // Create output directory if it doesn't exist
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
      console.log(`Created output directory: ${outputDir}`);
    }

    // Read input file
    const inputBuffer = fs.readFileSync(inputPath);
    const fileName = path.basename(inputPath);
    
    console.log(`\n=== PhotoVault Image Converter ===`);
    console.log(`Input: ${inputPath} (${(inputBuffer.length / 1024 / 1024).toFixed(2)}MB)`);
    console.log(`Output: ${outputDir}`);
    console.log(`Processing...`);

    // Start timing
    const startTime = Date.now();

    // Initialize processor
    const processor = new HeicProcessor();
    
    // Determine if it's a HEIC file
    const isHeic = HeicProcessor.isHeicFile(fileName);
    let results;

    let variantTimings = {};

    if (isHeic) {
      // Process HEIC file (creates full + thumbnail variants)
      results = await processor.processHeicFile(inputBuffer, fileName);
      // Note: HEIC processing happens internally, so we can't time individual variants
      variantTimings.heic_processing = 'Internal processing';
    } else {
      // For non-HEIC files, use convertToAvif to create similar variants
      const baseName = path.parse(fileName).name;
      
      // Create full-size variant
      console.log('Converting full-size variant...');
      const fullStartTime = Date.now();
      const fullBuffer = await processor.convertToAvif(inputBuffer, { 
        quality: 90,
        maxWidth: null,
        maxHeight: null 
      });
      const fullEndTime = Date.now();
      variantTimings.full = ((fullEndTime - fullStartTime) / 1000).toFixed(2);
      
      // Create thumbnail variant
      console.log('Converting thumbnail variant...');
      const thumbnailStartTime = Date.now();
      const thumbnailBuffer = await processor.convertToAvif(inputBuffer, {
        quality: 80,
        maxWidth: 300,
        maxHeight: 300
      });
      const thumbnailEndTime = Date.now();
      variantTimings.thumbnail = ((thumbnailEndTime - thumbnailStartTime) / 1000).toFixed(2);

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
      console.log(`✓ Saved ${variantName}: ${outputPath} (${(variant.size / 1024).toFixed(2)}KB)`);
    }

    // Calculate processing time
    const endTime = Date.now();
    const processingTimeMs = endTime - startTime;
    const processingTimeSec = (processingTimeMs / 1000).toFixed(2);

    console.log(`\n=== Conversion Complete ===`);
    console.log(`Total processing time: ${processingTimeSec}s`);
    
    // Display individual variant timings
    if (Object.keys(variantTimings).length > 0) {
      console.log(`Variant conversion times:`);
      for (const [variant, time] of Object.entries(variantTimings)) {
        if (time === 'Internal processing') {
          console.log(`  - ${variant}: ${time}`);
        } else {
          console.log(`  - ${variant}: ${time}s`);
        }
      }
    }
    
    console.log(`Generated ${savedFiles.length} variants:`);
    savedFiles.forEach(file => {
      console.log(`  - ${file.variant}: ${file.file} (${file.size})`);
    });

    return { success: true, files: savedFiles };

  } catch (error) {
    console.error(`\n❌ Error: ${error.message}`);
    return { success: false, error: error.message };
  }
}

// Main CLI handler
async function main() {
  const args = process.argv.slice(2);

  if (args.length !== 2) {
    showUsage();
    process.exit(1);
  }

  const [inputPath, outputDir] = args;
  
  const result = await processImage(inputPath, outputDir);
  
  if (result.success) {
    console.log(`\n🎉 Success! Converted image saved to: ${outputDir}`);
    process.exit(0);
  } else {
    console.error(`\n💥 Failed to convert image: ${result.error}`);
    process.exit(1);
  }
}

// Run CLI if this file is executed directly
if (require.main === module) {
  main().catch(error => {
    console.error('Unexpected error:', error);
    process.exit(1);
  });
}

module.exports = { processImage };
