const { parentPort, workerData } = require('worker_threads');
const { processImage } = require('./server');
const fs = require('fs');

// Handle both initialization with workerData and dynamic messages
if (workerData) {
  // Legacy mode - process immediately with workerData
  processImageInWorker(workerData);
} else {
  // New mode - listen for messages from recovery manager
  parentPort.on('message', async (data) => {
    await processImageInWorker(data);
  });
}

async function processImageInWorker(data) {
  try {
    const { inputPath, outputDir, originalName, degraded } = data;
    
    console.log(`[WORKER] Starting image processing: ${originalName || inputPath}`);
    console.log(`[WORKER] Degraded mode: ${degraded ? 'ON' : 'OFF'}`);
    
    const startTime = Date.now();
    
    // If in degraded mode, process with reduced quality/size limits
    if (degraded) {
      console.log('[WORKER] Applying degraded mode processing limits');
      // You could modify processImage to accept options for degraded processing
    }
    
    const result = await processImage(inputPath, outputDir);
    
    const processingTime = Date.now() - startTime;
    console.log(`[WORKER] Processing completed in ${processingTime}ms`);
    
    parentPort.postMessage({ success: true, ...result, processingTime });
  } catch (error) {
    console.error(`[WORKER] Processing failed:`, error.message);
    parentPort.postMessage({ success: false, error: error.message });
  }
}
