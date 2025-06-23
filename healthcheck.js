// healthcheck.js
const { processImage } = require('./server');
const fs = require('fs');

const input = '/test-images/test.heic';
const output = '/tmp/healthcheck-out';

(async () => {
  try {
    if (!fs.existsSync(input)) throw new Error('Missing test.heic input');
    await processImage(input, output);
    console.log('✅ HEIC conversion succeeded');
    process.exit(0);
  } catch (err) {
    console.error('❌ Healthcheck failed:', err.message);
    process.exit(1);
  }
})();
