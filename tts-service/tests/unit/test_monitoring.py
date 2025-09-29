"""
Unit tests for monitoring and metrics collection
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch
from collections import deque

from src.utils.monitoring import MetricsCollector


class TestMetricsCollector:
    """Test cases for metrics collector"""
    
    @pytest.fixture
    def metrics_collector(self):
        """Create metrics collector instance"""
        with patch('src.utils.monitoring.psutil') as mock_psutil:
            # Mock psutil to avoid system dependencies
            mock_psutil.virtual_memory.return_value = Mock(
                percent=50.0,
                used=1024*1024*1024,  # 1GB
                available=1024*1024*1024  # 1GB
            )
            mock_psutil.cpu_percent.return_value = 25.0
            
            collector = MetricsCollector()
            # Stop background monitoring for tests
            collector._monitoring_thread = None
            return collector
    
    def test_initialization(self, metrics_collector):
        """Test metrics collector initialization"""
        assert metrics_collector.start_time > 0
        assert isinstance(metrics_collector.request_counts, dict)
        assert isinstance(metrics_collector.tenant_requests, dict)
        assert isinstance(metrics_collector.memory_usage, deque)
        assert isinstance(metrics_collector.cpu_usage, deque)
    
    def test_record_synthesis_request(self, metrics_collector):
        """Test recording synthesis request"""
        tenant_id = "test_tenant"
        text_length = 100
        
        metrics_collector.record_synthesis_request(tenant_id, text_length)
        
        assert metrics_collector.request_counts['total'] == 1
        assert metrics_collector.tenant_requests[tenant_id] == 1
    
    def test_record_synthesis_complete(self, metrics_collector):
        """Test recording synthesis completion"""
        tenant_id = "test_tenant"
        duration = 1.5
        
        metrics_collector.record_synthesis_complete(tenant_id, duration)
        
        assert len(metrics_collector.request_times['total']) == 1
        assert metrics_collector.request_times['total'][0] == duration
        assert len(metrics_collector.tenant_latencies[tenant_id]) == 1
        assert metrics_collector.tenant_latencies[tenant_id][0] == duration
    
    def test_record_synthesis_error(self, metrics_collector):
        """Test recording synthesis error"""
        tenant_id = "test_tenant"
        error_message = "Test error"
        
        metrics_collector.record_synthesis_error(tenant_id, error_message)
        
        assert metrics_collector.error_counts['total'] == 1
        assert metrics_collector.tenant_errors[tenant_id] == 1
    
    def test_get_memory_usage(self, metrics_collector):
        """Test getting memory usage"""
        # Add some mock memory data
        metrics_collector.memory_usage.append({
            'timestamp': time.time(),
            'used_percent': 60.0,
            'used_mb': 1200,
            'available_mb': 800
        })
        metrics_collector.memory_usage.append({
            'timestamp': time.time(),
            'used_percent': 70.0,
            'used_mb': 1400,
            'available_mb': 600
        })
        
        result = metrics_collector.get_memory_usage()
        
        assert 'current' in result
        assert 'average_used_percent' in result
        assert 'peak_used_percent' in result
        assert result['average_used_percent'] == 65.0
        assert result['peak_used_percent'] == 70.0
    
    def test_get_memory_usage_empty(self, metrics_collector):
        """Test getting memory usage when empty"""
        result = metrics_collector.get_memory_usage()
        assert result == {}
    
    def test_get_cpu_usage(self, metrics_collector):
        """Test getting CPU usage"""
        # Add some mock CPU data
        metrics_collector.cpu_usage.append({
            'timestamp': time.time(),
            'percent': 30.0
        })
        metrics_collector.cpu_usage.append({
            'timestamp': time.time(),
            'percent': 40.0
        })
        
        result = metrics_collector.get_cpu_usage()
        
        assert 'current' in result
        assert 'average_percent' in result
        assert 'peak_percent' in result
        assert result['average_percent'] == 35.0
        assert result['peak_percent'] == 40.0
    
    def test_get_request_metrics(self, metrics_collector):
        """Test getting request metrics"""
        tenant_id = "test_tenant"
        
        # Record some requests
        metrics_collector.record_synthesis_request(tenant_id, 100)
        metrics_collector.record_synthesis_request(tenant_id, 200)
        metrics_collector.record_synthesis_complete(tenant_id, 1.0)
        metrics_collector.record_synthesis_complete(tenant_id, 2.0)
        metrics_collector.record_synthesis_error(tenant_id, "Error")
        
        result = metrics_collector.get_request_metrics()
        
        assert result['total_requests'] == 2
        assert result['total_errors'] == 1
        assert result['error_rate'] == 0.5
        assert result['average_latency'] == 1.5
        assert result['p95_latency'] == 2.0
        assert result['p99_latency'] == 2.0
        assert result['requests_per_second'] > 0
    
    def test_get_request_metrics_no_requests(self, metrics_collector):
        """Test getting request metrics with no requests"""
        result = metrics_collector.get_request_metrics()
        
        assert result['total_requests'] == 0
        assert result['total_errors'] == 0
        assert result['error_rate'] == 0
        assert result['average_latency'] == 0
        assert result['p95_latency'] == 0
        assert result['p99_latency'] == 0
    
    def test_get_tenant_metrics(self, metrics_collector):
        """Test getting tenant metrics"""
        tenant_id = "test_tenant"
        
        # Record some tenant data
        metrics_collector.record_synthesis_request(tenant_id, 100)
        metrics_collector.record_synthesis_request(tenant_id, 200)
        metrics_collector.record_synthesis_complete(tenant_id, 1.0)
        metrics_collector.record_synthesis_complete(tenant_id, 2.0)
        metrics_collector.record_synthesis_error(tenant_id, "Error")
        
        result = metrics_collector.get_tenant_metrics(tenant_id)
        
        assert result['requests'] == 2
        assert result['errors'] == 1
        assert result['error_rate'] == 0.5
        assert result['average_latency'] == 1.5
        assert result['p95_latency'] == 2.0
    
    def test_get_tenant_metrics_no_data(self, metrics_collector):
        """Test getting tenant metrics with no data"""
        tenant_id = "nonexistent_tenant"
        result = metrics_collector.get_tenant_metrics(tenant_id)
        
        assert result['requests'] == 0
        assert result['errors'] == 0
        assert result['error_rate'] == 0
        assert result['average_latency'] == 0
        assert result['p95_latency'] == 0
    
    def test_get_system_metrics(self, metrics_collector):
        """Test getting system metrics"""
        # Add some data
        metrics_collector.record_synthesis_request("tenant1", 100)
        metrics_collector.record_synthesis_request("tenant2", 200)
        metrics_collector.memory_usage.append({
            'timestamp': time.time(),
            'used_percent': 50.0,
            'used_mb': 1000,
            'available_mb': 1000
        })
        
        result = metrics_collector.get_system_metrics()
        
        assert 'uptime' in result
        assert 'memory' in result
        assert 'cpu' in result
        assert 'requests' in result
        assert 'tenants' in result
        assert result['tenants']['total_tenants'] == 2
        assert result['tenants']['active_tenants'] == 2
    
    def test_get_health_status_healthy(self, metrics_collector):
        """Test getting health status when healthy"""
        # Add healthy metrics
        metrics_collector.record_synthesis_request("tenant1", 100)
        metrics_collector.record_synthesis_complete("tenant1", 0.5)  # Low latency
        metrics_collector.memory_usage.append({
            'timestamp': time.time(),
            'used_percent': 50.0,
            'used_mb': 1000,
            'available_mb': 1000
        })
        metrics_collector.cpu_usage.append({
            'timestamp': time.time(),
            'percent': 30.0
        })
        
        result = metrics_collector.get_health_status()
        
        assert result['status'] == 'healthy'
        assert result['health_score'] >= 80
        assert 'timestamp' in result
        assert 'metrics' in result
    
    def test_get_health_status_degraded(self, metrics_collector):
        """Test getting health status when degraded"""
        # Add degraded metrics
        metrics_collector.record_synthesis_request("tenant1", 100)
        metrics_collector.record_synthesis_complete("tenant1", 0.5)
        metrics_collector.record_synthesis_error("tenant1", "Error")  # High error rate
        metrics_collector.memory_usage.append({
            'timestamp': time.time(),
            'used_percent': 95.0,  # High memory usage
            'used_mb': 1900,
            'available_mb': 100
        })
        
        result = metrics_collector.get_health_status()
        
        assert result['status'] in ['degraded', 'unhealthy']
        assert result['health_score'] < 80
        assert result['health_score'] >= 0
    
    def test_latency_limits(self, metrics_collector):
        """Test that latency lists are limited in size"""
        tenant_id = "test_tenant"
        
        # Add more than 1000 requests
        for i in range(1100):
            metrics_collector.record_synthesis_complete(tenant_id, 1.0)
        
        # Total requests should be limited
        assert len(metrics_collector.request_times['total']) == 1000
        
        # Add more than 100 requests for tenant
        for i in range(150):
            metrics_collector.record_synthesis_complete(tenant_id, 1.0)
        
        # Tenant requests should be limited
        assert len(metrics_collector.tenant_latencies[tenant_id]) == 100
    
    def test_thread_safety(self, metrics_collector):
        """Test thread safety of metrics collection"""
        def record_requests():
            for i in range(100):
                metrics_collector.record_synthesis_request(f"tenant_{i}", 100)
                metrics_collector.record_synthesis_complete(f"tenant_{i}", 1.0)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=record_requests)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check that all requests were recorded
        assert metrics_collector.request_counts['total'] == 500
        assert len(metrics_collector.tenant_requests) == 100
