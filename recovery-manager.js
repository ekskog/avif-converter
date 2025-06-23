// Process Recovery Manager for AVIF Converter
// Implements circuit breaker, auto-restart, and graceful degradation

class CircuitBreaker {
  constructor(failureThreshold = 5, resetTimeout = 60000) {
    this.failureThreshold = failureThreshold;
    this.resetTimeout = resetTimeout;
    this.failureCount = 0;
    this.lastFailureTime = null;
    this.state = 'CLOSED'; // CLOSED, OPEN, HALF_OPEN
  }

  async execute(operation) {
    if (this.state === 'OPEN') {
      if (Date.now() - this.lastFailureTime > this.resetTimeout) {
        this.state = 'HALF_OPEN';
        console.log('[CIRCUIT] Circuit breaker moving to HALF_OPEN state');
      } else {
        throw new Error('Circuit breaker is OPEN - service temporarily unavailable');
      }
    }

    try {
      const result = await operation();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  onSuccess() {
    this.failureCount = 0;
    this.state = 'CLOSED';
  }

  onFailure() {
    this.failureCount++;
    this.lastFailureTime = Date.now();
    
    if (this.failureCount >= this.failureThreshold) {
      this.state = 'OPEN';
      console.error(`[CIRCUIT] Circuit breaker OPENED after ${this.failureCount} failures`);
    }
  }

  getState() {
    return {
      state: this.state,
      failureCount: this.failureCount,
      lastFailureTime: this.lastFailureTime
    };
  }
}

class WorkerManager {
  constructor(workerScript, maxWorkers = 2) {
    this.workerScript = workerScript;
    this.maxWorkers = maxWorkers;
    this.workers = new Map();
    this.workerQueue = [];
    this.workerStats = new Map();
    this.restartCount = 0;
    this.maxRestarts = 10;
  }

  async getWorker() {
    // Find an available worker
    for (const [id, worker] of this.workers) {
      const stats = this.workerStats.get(id);
      if (!stats.busy) {
        return { id, worker };
      }
    }

    // Create new worker if under limit
    if (this.workers.size < this.maxWorkers) {
      return this.createWorker();
    }

    // Wait for worker to become available
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('No workers available - timeout'));
      }, 30000);

      this.workerQueue.push({ resolve, reject, timeout });
    });
  }

  createWorker() {
    const workerId = `worker_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const { Worker } = require('worker_threads');
    
    console.log(`[WORKER] Creating new worker: ${workerId}`);
    
    const worker = new Worker(this.workerScript);
    
    // Track worker stats
    this.workerStats.set(workerId, {
      busy: false,
      created: Date.now(),
      jobsCompleted: 0,
      errors: 0,
      lastActivity: Date.now()
    });

    // Handle worker errors and exits
    worker.on('error', (error) => {
      console.error(`[WORKER] Worker ${workerId} error:`, error);
      this.handleWorkerFailure(workerId, error);
    });

    worker.on('exit', (code) => {
      console.log(`[WORKER] Worker ${workerId} exited with code ${code}`);
      this.handleWorkerExit(workerId, code);
    });

    this.workers.set(workerId, worker);
    return { id: workerId, worker };
  }

  async executeWithWorker(workerId, data) {
    const worker = this.workers.get(workerId);
    const stats = this.workerStats.get(workerId);
    
    if (!worker || !stats) {
      throw new Error(`Worker ${workerId} not found`);
    }

    stats.busy = true;
    stats.lastActivity = Date.now();

    try {
      const result = await new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
          reject(new Error('Worker timeout'));
        }, 120000); // 2 minute timeout

        worker.postMessage(data);
        
        const messageHandler = (result) => {
          clearTimeout(timeout);
          worker.off('message', messageHandler);
          worker.off('error', errorHandler);
          
          if (result.error) {
            reject(new Error(result.error));
          } else {
            resolve(result);
          }
        };

        const errorHandler = (error) => {
          clearTimeout(timeout);
          worker.off('message', messageHandler);
          worker.off('error', errorHandler);
          reject(error);
        };

        worker.once('message', messageHandler);
        worker.once('error', errorHandler);
      });

      stats.jobsCompleted++;
      return result;
    } catch (error) {
      stats.errors++;
      throw error;
    } finally {
      stats.busy = false;
      stats.lastActivity = Date.now();
      
      // Release waiting jobs
      if (this.workerQueue.length > 0) {
        const { resolve, timeout } = this.workerQueue.shift();
        clearTimeout(timeout);
        resolve({ id: workerId, worker });
      }
    }
  }

  handleWorkerFailure(workerId, error) {
    const stats = this.workerStats.get(workerId);
    if (stats) {
      stats.errors++;
    }

    // If worker has too many errors, restart it
    if (stats && stats.errors > 3) {
      console.log(`[WORKER] Restarting worker ${workerId} due to excessive errors`);
      this.restartWorker(workerId);
    }
  }

  handleWorkerExit(workerId, code) {
    this.workers.delete(workerId);
    this.workerStats.delete(workerId);

    // Auto-restart if we have capacity and haven't restarted too many times
    if (this.restartCount < this.maxRestarts && code !== 0) {
      this.restartCount++;
      console.log(`[WORKER] Auto-restarting worker (restart #${this.restartCount})`);
      setTimeout(() => this.createWorker(), 1000);
    }
  }

  async restartWorker(workerId) {
    const worker = this.workers.get(workerId);
    if (worker) {
      console.log(`[WORKER] Terminating worker ${workerId}`);
      await worker.terminate();
    }
    
    // handleWorkerExit will be called automatically and create a new worker
  }

  getStats() {
    const workers = Array.from(this.workerStats.entries()).map(([id, stats]) => ({
      id,
      ...stats,
      uptime: Date.now() - stats.created
    }));

    return {
      totalWorkers: this.workers.size,
      queueLength: this.workerQueue.length,
      restartCount: this.restartCount,
      workers
    };
  }

  async shutdown() {
    console.log('[WORKER] Shutting down all workers...');
    
    // Clear the queue
    while (this.workerQueue.length > 0) {
      const { reject, timeout } = this.workerQueue.shift();
      clearTimeout(timeout);
      reject(new Error('Service shutting down'));
    }

    // Terminate all workers
    const terminations = Array.from(this.workers.values()).map(worker => 
      worker.terminate()
    );
    
    await Promise.all(terminations);
    this.workers.clear();
    this.workerStats.clear();
  }
}

class ProcessRecoveryManager {
  constructor() {
    this.circuitBreaker = new CircuitBreaker(5, 60000); // 5 failures, 1 minute reset
    this.workerManager = new WorkerManager('./worker.js', 2);
    this.degradedMode = false;
    this.healthCheck = {
      lastCheck: Date.now(),
      consecutiveFailures: 0,
      status: 'healthy'
    };
    
    // Start health monitoring
    this.startHealthMonitoring();
  }

  async processWithRecovery(data) {
    return this.circuitBreaker.execute(async () => {
      const { id: workerId, worker } = await this.workerManager.getWorker();
      
      if (this.degradedMode) {
        console.log('[RECOVERY] Running in degraded mode - using fallback processing');
        data.degraded = true;
      }
      
      return this.workerManager.executeWithWorker(workerId, data);
    });
  }

  startHealthMonitoring() {
    setInterval(() => {
      this.performHealthCheck();
    }, 30000); // Check every 30 seconds
  }

  async performHealthCheck() {
    try {
      const workerStats = this.workerManager.getStats();
      const circuitState = this.circuitBreaker.getState();
      
      console.log('[HEALTH] Worker stats:', workerStats);
      console.log('[HEALTH] Circuit breaker state:', circuitState.state);
      
      // Check if we should enter degraded mode
      const shouldDegrade = (
        workerStats.restartCount > 5 ||
        circuitState.state === 'OPEN' ||
        workerStats.totalWorkers === 0
      );
      
      if (shouldDegrade && !this.degradedMode) {
        console.warn('[RECOVERY] Entering degraded mode due to system stress');
        this.degradedMode = true;
        this.healthCheck.status = 'degraded';
      } else if (!shouldDegrade && this.degradedMode) {
        console.log('[RECOVERY] Exiting degraded mode - system recovered');
        this.degradedMode = false;
        this.healthCheck.status = 'healthy';
      }
      
      this.healthCheck.lastCheck = Date.now();
      this.healthCheck.consecutiveFailures = 0;
      
    } catch (error) {
      console.error('[HEALTH] Health check failed:', error);
      this.healthCheck.consecutiveFailures++;
      
      if (this.healthCheck.consecutiveFailures > 3) {
        this.healthCheck.status = 'unhealthy';
        console.error('[RECOVERY] System marked as unhealthy');
      }
    }
  }

  getSystemStatus() {
    return {
      timestamp: new Date().toISOString(),
      degradedMode: this.degradedMode,
      healthCheck: this.healthCheck,
      circuitBreaker: this.circuitBreaker.getState(),
      workers: this.workerManager.getStats()
    };
  }

  async shutdown() {
    console.log('[RECOVERY] Shutting down recovery manager...');
    await this.workerManager.shutdown();
  }
}

module.exports = { ProcessRecoveryManager, CircuitBreaker, WorkerManager };
