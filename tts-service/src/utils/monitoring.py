"""
Monitoring and Metrics Collection
Tracks performance, usage, and system health
"""

import time
import psutil
import threading
from typing import Dict, Any, List
from collections import defaultdict, deque
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class MetricsCollector:
    """Collect and track system and application metrics"""
    
    def __init__(self):
        self.start_time = time.time()
        self.lock = threading.Lock()
        
        # Request metrics
        self.request_counts = defaultdict(int)
        self.request_times = defaultdict(list)
        self.error_counts = defaultdict(int)
        
        # Tenant metrics
        self.tenant_requests = defaultdict(int)
        self.tenant_errors = defaultdict(int)
        self.tenant_latencies = defaultdict(list)
        
        # System metrics
        self.memory_usage = deque(maxlen=100)
        self.cpu_usage = deque(maxlen=100)
        
        # Start background monitoring
        self._start_background_monitoring()
    
    def _start_background_monitoring(self):
        """Start background thread for system monitoring"""
        def monitor_system():
            while True:
                try:
                    # Collect system metrics
                    memory = psutil.virtual_memory()
                    cpu = psutil.cpu_percent()
                    
                    with self.lock:
                        self.memory_usage.append({
                            'timestamp': time.time(),
                            'used_percent': memory.percent,
                            'used_mb': memory.used / 1024 / 1024,
                            'available_mb': memory.available / 1024 / 1024
                        })
                        
                        self.cpu_usage.append({
                            'timestamp': time.time(),
                            'percent': cpu
                        })
                    
                    time.sleep(5)  # Collect every 5 seconds
                    
                except Exception as e:
                    logger.error(f"Error in system monitoring: {e}")
                    time.sleep(10)
        
        monitor_thread = threading.Thread(target=monitor_system, daemon=True)
        monitor_thread.start()
    
    def record_synthesis_request(self, tenant_id: str, text_length: int):
        """Record a synthesis request"""
        with self.lock:
            self.request_counts['total'] += 1
            self.tenant_requests[tenant_id] += 1
    
    def record_synthesis_complete(
        self, 
        tenant_id: str, 
        duration: float, 
        streaming_metrics: Dict[str, Any] = None
    ):
        """Record completion of synthesis request"""
        with self.lock:
            self.request_times['total'].append(duration)
            self.tenant_latencies[tenant_id].append(duration)
            
            # Keep only recent latencies (last 1000 requests)
            if len(self.request_times['total']) > 1000:
                self.request_times['total'] = self.request_times['total'][-1000:]
            
            if len(self.tenant_latencies[tenant_id]) > 100:
                self.tenant_latencies[tenant_id] = self.tenant_latencies[tenant_id][-100:]
    
    def record_synthesis_error(self, tenant_id: str, error_message: str):
        """Record a synthesis error"""
        with self.lock:
            self.error_counts['total'] += 1
            self.tenant_errors[tenant_id] += 1
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get current memory usage"""
        with self.lock:
            if not self.memory_usage:
                return {}
            
            latest = self.memory_usage[-1]
            return {
                'current': latest,
                'average_used_percent': sum(m['used_percent'] for m in self.memory_usage) / len(self.memory_usage),
                'peak_used_percent': max(m['used_percent'] for m in self.memory_usage)
            }
    
    def get_cpu_usage(self) -> Dict[str, Any]:
        """Get current CPU usage"""
        with self.lock:
            if not self.cpu_usage:
                return {}
            
            latest = self.cpu_usage[-1]
            return {
                'current': latest,
                'average_percent': sum(c['percent'] for c in self.cpu_usage) / len(self.cpu_usage),
                'peak_percent': max(c['percent'] for c in self.cpu_usage)
            }
    
    def get_request_metrics(self) -> Dict[str, Any]:
        """Get request metrics"""
        with self.lock:
            total_requests = self.request_counts['total']
            total_errors = self.error_counts['total']
            
            if not self.request_times['total']:
                return {
                    'total_requests': total_requests,
                    'total_errors': total_errors,
                    'error_rate': 0,
                    'average_latency': 0,
                    'p95_latency': 0,
                    'p99_latency': 0
                }
            
            latencies = sorted(self.request_times['total'])
            avg_latency = sum(latencies) / len(latencies)
            p95_latency = latencies[int(len(latencies) * 0.95)]
            p99_latency = latencies[int(len(latencies) * 0.99)]
            
            return {
                'total_requests': total_requests,
                'total_errors': total_errors,
                'error_rate': total_errors / total_requests if total_requests > 0 else 0,
                'average_latency': avg_latency,
                'p95_latency': p95_latency,
                'p99_latency': p99_latency,
                'requests_per_second': total_requests / (time.time() - self.start_time)
            }
    
    def get_tenant_metrics(self, tenant_id: str) -> Dict[str, Any]:
        """Get metrics for a specific tenant"""
        with self.lock:
            requests = self.tenant_requests.get(tenant_id, 0)
            errors = self.tenant_errors.get(tenant_id, 0)
            latencies = self.tenant_latencies.get(tenant_id, [])
            
            if not latencies:
                return {
                    'requests': requests,
                    'errors': errors,
                    'error_rate': 0,
                    'average_latency': 0,
                    'p95_latency': 0
                }
            
            avg_latency = sum(latencies) / len(latencies)
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
            
            return {
                'requests': requests,
                'errors': errors,
                'error_rate': errors / requests if requests > 0 else 0,
                'average_latency': avg_latency,
                'p95_latency': p95_latency
            }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system metrics"""
        return {
            'uptime': time.time() - self.start_time,
            'memory': self.get_memory_usage(),
            'cpu': self.get_cpu_usage(),
            'requests': self.get_request_metrics(),
            'tenants': {
                'total_tenants': len(self.tenant_requests),
                'active_tenants': len([t for t in self.tenant_requests.values() if t > 0])
            }
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status"""
        request_metrics = self.get_request_metrics()
        memory_usage = self.get_memory_usage()
        cpu_usage = self.get_cpu_usage()
        
        # Determine health status
        health_score = 100
        
        # Check error rate
        if request_metrics['error_rate'] > 0.01:  # > 1% error rate
            health_score -= 20
        
        # Check latency
        if request_metrics['average_latency'] > 2.0:  # > 2 seconds
            health_score -= 20
        
        # Check memory usage
        if memory_usage and memory_usage['current']['used_percent'] > 90:
            health_score -= 30
        
        # Check CPU usage
        if cpu_usage and cpu_usage['current']['percent'] > 90:
            health_score -= 30
        
        if health_score >= 80:
            status = "healthy"
        elif health_score >= 60:
            status = "degraded"
        else:
            status = "unhealthy"
        
        return {
            'status': status,
            'health_score': health_score,
            'timestamp': time.time(),
            'metrics': {
                'error_rate': request_metrics['error_rate'],
                'average_latency': request_metrics['average_latency'],
                'memory_usage': memory_usage['current']['used_percent'] if memory_usage else 0,
                'cpu_usage': cpu_usage['current']['percent'] if cpu_usage else 0
            }
        }
