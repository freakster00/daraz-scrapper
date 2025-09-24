"""
monitor.py
==========

Performance monitoring and metrics collection for the optimized scraper:
- Memory usage tracking
- Request/response metrics
- Performance analytics
- Health monitoring
"""

import asyncio
import time
import psutil
import os
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import weakref
import gc

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    timestamp: str
    memory_usage: Dict[str, float]
    cpu_usage: float
    active_connections: int
    requests_per_second: float
    average_response_time: float
    error_rate: float
    cache_hit_rate: float

class PerformanceMonitor:
    """Performance monitoring and metrics collection"""
    
    def __init__(self, enable_monitoring: bool = True):
        self.enable_monitoring = enable_monitoring
        self.metrics_history: List[PerformanceMetrics] = []
        self.request_count = 0
        self.error_count = 0
        self.response_times: List[float] = []
        self.cache_hits = 0
        self.cache_misses = 0
        self.start_time = time.time()
        self._active_connections = weakref.WeakSet()
        
        if enable_monitoring:
            self._start_monitoring()
    
    def _start_monitoring(self):
        """Start background monitoring task"""
        asyncio.create_task(self._monitor_loop())
    
    async def _monitor_loop(self):
        """Background monitoring loop"""
        while self.enable_monitoring:
            try:
                await self._collect_metrics()
                await asyncio.sleep(60)  # Collect metrics every minute
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)
    
    async def _collect_metrics(self):
        """Collect current performance metrics"""
        try:
            # Memory usage
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            memory_usage = {
                'rss_mb': memory_info.rss / 1024 / 1024,  # Resident Set Size in MB
                'vms_mb': memory_info.vms / 1024 / 1024,  # Virtual Memory Size in MB
                'percent': process.memory_percent()
            }
            
            # CPU usage
            cpu_usage = process.cpu_percent()
            
            # Active connections
            active_connections = len(self._active_connections)
            
            # Request metrics
            uptime = time.time() - self.start_time
            requests_per_second = self.request_count / uptime if uptime > 0 else 0
            
            # Response time metrics
            avg_response_time = (
                sum(self.response_times) / len(self.response_times)
                if self.response_times else 0
            )
            
            # Error rate
            error_rate = (
                self.error_count / self.request_count
                if self.request_count > 0 else 0
            )
            
            # Cache hit rate
            total_cache_requests = self.cache_hits + self.cache_misses
            cache_hit_rate = (
                self.cache_hits / total_cache_requests
                if total_cache_requests > 0 else 0
            )
            
            # Create metrics object
            metrics = PerformanceMetrics(
                timestamp=datetime.now().isoformat(),
                memory_usage=memory_usage,
                cpu_usage=cpu_usage,
                active_connections=active_connections,
                requests_per_second=requests_per_second,
                average_response_time=avg_response_time,
                error_rate=error_rate,
                cache_hit_rate=cache_hit_rate
            )
            
            # Store metrics
            self.metrics_history.append(metrics)
            
            # Keep only last 100 metrics to prevent memory buildup
            if len(self.metrics_history) > 100:
                self.metrics_history = self.metrics_history[-100:]
            
            # Log metrics
            logger.info(f"Performance metrics: {asdict(metrics)}")
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
    
    def record_request(self, response_time: float, is_error: bool = False):
        """Record a request and its metrics"""
        self.request_count += 1
        self.response_times.append(response_time)
        
        if is_error:
            self.error_count += 1
        
        # Keep only last 1000 response times
        if len(self.response_times) > 1000:
            self.response_times = self.response_times[-1000:]
    
    def record_cache_hit(self):
        """Record a cache hit"""
        self.cache_hits += 1
    
    def record_cache_miss(self):
        """Record a cache miss"""
        self.cache_misses += 1
    
    def add_connection(self, connection):
        """Add a connection to monitoring"""
        self._active_connections.add(connection)
    
    def remove_connection(self, connection):
        """Remove a connection from monitoring"""
        self._active_connections.discard(connection)
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        if not self.metrics_history:
            return {}
        
        latest = self.metrics_history[-1]
        return asdict(latest)
    
    def get_metrics_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get metrics summary for the last N hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_metrics = [
            m for m in self.metrics_history
            if datetime.fromisoformat(m.timestamp) > cutoff_time
        ]
        
        if not recent_metrics:
            return {}
        
        # Calculate averages
        avg_memory_rss = sum(m.memory_usage['rss_mb'] for m in recent_metrics) / len(recent_metrics)
        avg_cpu = sum(m.cpu_usage for m in recent_metrics) / len(recent_metrics)
        avg_rps = sum(m.requests_per_second for m in recent_metrics) / len(recent_metrics)
        avg_response_time = sum(m.average_response_time for m in recent_metrics) / len(recent_metrics)
        avg_error_rate = sum(m.error_rate for m in recent_metrics) / len(recent_metrics)
        
        return {
            'period_hours': hours,
            'sample_count': len(recent_metrics),
            'average_memory_rss_mb': round(avg_memory_rss, 2),
            'average_cpu_percent': round(avg_cpu, 2),
            'average_requests_per_second': round(avg_rps, 2),
            'average_response_time_ms': round(avg_response_time * 1000, 2),
            'average_error_rate': round(avg_error_rate * 100, 2),
            'total_requests': self.request_count,
            'total_errors': self.error_count,
            'uptime_seconds': time.time() - self.start_time
        }
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get detailed memory usage information"""
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            return {
                'rss_mb': memory_info.rss / 1024 / 1024,
                'vms_mb': memory_info.vms / 1024 / 1024,
                'percent': process.memory_percent(),
                'available_mb': psutil.virtual_memory().available / 1024 / 1024,
                'total_mb': psutil.virtual_memory().total / 1024 / 1024,
                'gc_counts': gc.get_count(),
                'gc_threshold': gc.get_threshold()
            }
        except Exception as e:
            logger.error(f"Error getting memory usage: {e}")
            return {}
    
    def force_garbage_collection(self):
        """Force garbage collection and return stats"""
        try:
            before = gc.get_count()
            collected = gc.collect()
            after = gc.get_count()
            
            return {
                'objects_collected': collected,
                'counts_before': before,
                'counts_after': after,
                'memory_freed': True
            }
        except Exception as e:
            logger.error(f"Error in garbage collection: {e}")
            return {'error': str(e)}
    
    def export_metrics(self, filepath: str = None) -> str:
        """Export metrics to JSON file"""
        if filepath is None:
            filepath = f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'summary': self.get_metrics_summary(24),  # Last 24 hours
                'current_metrics': self.get_current_metrics(),
                'memory_usage': self.get_memory_usage(),
                'gc_stats': self.force_garbage_collection()
            }
            
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"Metrics exported to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error exporting metrics: {e}")
            raise

# Global monitor instance
monitor = PerformanceMonitor()

# Convenience functions
def record_request(response_time: float, is_error: bool = False):
    """Record a request for monitoring"""
    monitor.record_request(response_time, is_error)

def record_cache_hit():
    """Record a cache hit"""
    monitor.record_cache_hit()

def record_cache_miss():
    """Record a cache miss"""
    monitor.record_cache_miss()

def get_performance_summary() -> Dict[str, Any]:
    """Get performance summary"""
    return monitor.get_metrics_summary()

def get_memory_usage() -> Dict[str, Any]:
    """Get memory usage"""
    return monitor.get_memory_usage()

def force_cleanup():
    """Force memory cleanup"""
    return monitor.force_garbage_collection()

# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def test_monitoring():
        """Test the monitoring system"""
        print("Testing performance monitoring...")
        
        # Simulate some requests
        for i in range(10):
            start_time = time.time()
            await asyncio.sleep(0.1)  # Simulate processing
            response_time = time.time() - start_time
            monitor.record_request(response_time, is_error=(i % 10 == 0))
        
        # Wait for metrics collection
        await asyncio.sleep(2)
        
        # Print results
        print("Current metrics:", monitor.get_current_metrics())
        print("Performance summary:", monitor.get_metrics_summary())
        print("Memory usage:", monitor.get_memory_usage())
        
        # Export metrics
        export_file = monitor.export_metrics()
        print(f"Metrics exported to: {export_file}")
    
    asyncio.run(test_monitoring())
