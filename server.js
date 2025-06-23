const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

sharp.cache(false); // disable Sharp internal cache

class HeicProcessor {
  /**
   * Convert a HEIC/HEIF buffer to AVIF variants
   * @param {Buffer} buffer
   * @param {string} originalName
   * @returns {Promise<Object>} full and thumbnail variants
   */
  async convert(buffer, originalName) {
    const base = path.parse(originalName).name;
    const metadata = await sharp(buffer).metadata();
    const results = {};

    const variants = [
      { name: 'full', width: null, height: null, quality: 90 },
      { name: 'thumbnail', width: 300, height: 300, quality: 80 }
    ];

    for (const v of variants) {
      let transformer = sharp(buffer)
        .rotate()
        .withMetadata()
        .heif({ compression: 'av1', quality: v.quality });

      if (v.width && v.height) {
        transformer = transformer.resize(v.width, v.height, {
          fit: 'cover',
          position: 'center'
        });
      }

      const buf = await transformer.toBuffer();
      transformer.destroy();

      results[v.name] = {
        filename: `${base}_${v.name}.avif`,
        buffer: buf,
        size: buf.length,
        mimetype: 'image/avif',
        dimensions: v.width
          ? { width: v.width, height: v.height }
          : { width: metadata.width, height: metadata.height }
      };

      if (global.gc) global.gc(); // encourage cleanup
    }

    return results;
  }

  static isHeic(filename) {
    return /\.(heic|heif)$/i.test(filename);
  }
}

/**
 * Process a HEIC image file and write output variants to disk
 * @param {string} inputPath
 * @param {string} outputDir
 */
async function processImage(inputPath, outputDir) {
  if (!fs.existsSync(inputPath)) throw new Error(`Not found: ${inputPath}`);
  if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });

  const inputBuffer = fs.readFileSync(inputPath);
  const name = path.basename(inputPath);
  if (!HeicProcessor.isHeic(name)) throw new Error('Only HEIC/HEIF input allowed');

  const processor = new HeicProcessor();
  const variants = await processor.convert(inputBuffer, name);

  const saved = [];
  for (const key in variants) {
    const v = variants[key];
    const outPath = path.join(outputDir, v.filename);
    fs.writeFileSync(outPath, v.buffer);
    saved.push({ variant: key, path: outPath, sizeKB: (v.size / 1024).toFixed(1) });
  }

  return { success: true, files: saved };
}

module.exports = { HeicProcessor, processImage };
