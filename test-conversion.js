#!/usr/bin/env node

const fs = require('fs');

async function testAvifConversion() {
  try {
    console.log('🧪 Testing AVIF Converter...');
    
    // Create a simple 1x1 pixel JPEG for testing
    // This is a minimal valid JPEG file (base64 encoded)
    const minimalJpegBase64 = '/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/2wBDAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/wAARCAABAAEDAREAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwA/wA==';
    
    const testJpegBuffer = Buffer.from(minimalJpegBase64, 'base64');
    const testFilename = 'test-image.jpg';
    
    console.log(`📤 Uploading test JPEG: ${testFilename} (${testJpegBuffer.length} bytes)`);
    
    // Create FormData using built-in FormData
    const formData = new FormData();
    
    // Create a Blob from the buffer
    const blob = new Blob([testJpegBuffer], { type: 'image/jpeg' });
    formData.append('image', blob, testFilename);
    formData.append('returnContents', 'true');
    
    // Send request to converter using built-in fetch
    const response = await fetch('http://localhost:3002/convert', {
      method: 'POST',
      body: formData
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }
    
    const result = await response.json();
    
    console.log('✅ Conversion Response:');
    console.log('  Success:', result.success);
    console.log('  Message:', result.message);
    console.log('  Files count:', result.files ? result.files.length : 0);
    
    if (result.files) {
      result.files.forEach((file, index) => {
        console.log(`  File ${index + 1}:`);
        console.log(`    Variant: ${file.variant}`);
        console.log(`    Filename: ${file.filename}`);
        console.log(`    Size: ${file.sizeFormatted}`);
        console.log(`    Mime: ${file.mimetype}`);
        console.log(`    Content length: ${file.content ? file.content.length : 'N/A'} chars (base64)`);
      });
    }
    
    console.log('🎉 Test completed successfully!');
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
    console.error('Full error:', error);
  }
}

// Run the test
testAvifConversion();
