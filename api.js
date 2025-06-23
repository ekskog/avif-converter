const express = require('express');
const multer = require('multer');
const { processImage } = require('./server.js');
const path = require('path');
const fs = require('fs');

const app = express();
const port = process.env.PORT || 3002;

// Configure multer for file uploads
const upload = multer({ 
  dest: 'uploads/',
  limits: {
    fileSize: 100 * 1024 * 1024 // 100MB limit
  },
  fileFilter: (req, file, cb) => {
    // Accept image files and HEIC files
    if (file.mimetype.startsWith('image/') || 
        file.originalname.toLowerCase().endsWith('.heic') ||
        file.originalname.toLowerCase().endsWith('.heif')) {
      cb(null, true);
    } else {
      cb(new Error('Only image files are allowed!'));
    }
  }
});

// Health endpoint
app.get('/health', (req, res) => {
  console.log(`[${new Date().toISOString()}] Health check request received`);
  res.json({ 
    status: 'ok', 
    service: 'avif-converter',
    timestamp: new Date().toISOString()
  });
});

// Convert endpoint
app.post('/convert', upload.single('image'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No image file provided' });
    }

    const inputPath = req.file.path;
    const originalName = req.file.originalname;
    const outputDir = 'temp-output';
    
    console.log(`Processing file: ${originalName} (${req.file.size} bytes)`);
    console.log('Request body fields:', Object.keys(req.body));
    console.log('returnContents parameter:', req.body.returnContents);
    
    // Ensure output directory exists
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }

    // Process the image using CLI logic
    // The processImage function needs the original filename to detect HEIC files
    // But we need to pass the temp file path for the actual file content
    // Let's create a temporary file with the correct extension
    const tempPath = inputPath + path.extname(originalName);
    fs.renameSync(inputPath, tempPath);
    
    const result = await processImage(tempPath, outputDir);

    if (result.success) {
      // Check if client wants file contents instead of just paths
      const returnContents = req.body.returnContents === 'true' || req.query.returnContents === 'true';
      
      if (returnContents) {
        // Read the actual file contents and return them
        const filesWithContents = [];
        for (const fileInfo of result.files) {
          try {
            const fileBuffer = fs.readFileSync(fileInfo.file);
            filesWithContents.push({
              variant: fileInfo.variant,
              filename: path.basename(fileInfo.file),
              size: fileBuffer.length,
              sizeFormatted: fileInfo.size,
              mimetype: 'image/avif',
              content: fileBuffer.toString('base64') // Base64 encode for JSON transport
            });
            
            // Clean up the temp file
            fs.unlinkSync(fileInfo.file);
          } catch (readError) {
            console.error(`Failed to read converted file: ${fileInfo.file}`, readError.message);
          }
        }
        
        res.json({
          success: true,
          message: 'Image converted successfully',
          files: filesWithContents
        });
      } else {
        // Return file paths as before
        res.json({
          success: true,
          message: 'Image converted successfully',
          files: result.files
        });
      }
    } else {
      res.status(500).json({
        success: false,
        error: result.error
      });
    }

    // Clean up uploaded file
    if (fs.existsSync(tempPath)) {
      fs.unlinkSync(tempPath);
    }

  } catch (error) {
    console.error('Conversion error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.listen(port, () => {
  console.log(`AVIF Converter API running on port ${port}`);
});
