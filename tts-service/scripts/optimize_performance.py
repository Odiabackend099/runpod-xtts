#!/usr/bin/env python3
"""
Performance Optimization Script for TTS Service
Configures optimal settings for production deployment
"""

import os
import sys
import argparse
import json
import subprocess
import psutil
import torch
from pathlib import Path


class PerformanceOptimizer:
    """Optimizes TTS service performance for production"""
    
    def __init__(self):
        self.system_info = self._get_system_info()
        self.optimization_config = {}
    
    def _get_system_info(self):
        """Get system information for optimization"""
        info = {
            "cpu_count": psutil.cpu_count(),
            "memory_gb": psutil.virtual_memory().total / (1024**3),
            "gpu_available": torch.cuda.is_available(),
            "gpu_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
            "gpu_memory": []
        }
        
        if info["gpu_available"]:
            for i in range(info["gpu_count"]):
                gpu_memory = torch.cuda.get_device_properties(i).total_memory / (1024**3)
                info["gpu_memory"].append(gpu_memory)
        
        return info
    
    def optimize_model_loading(self):
        """Optimize model loading configuration"""
        config = {
            "model_cache_size": 2,  # Number of models to keep in memory
            "preload_models": True,
            "lazy_loading": False,  # Load all models at startup
            "model_compression": "fp16" if self.system_info["gpu_available"] else "fp32"
        }
        
        # Adjust based on available memory
        if self.system_info["memory_gb"] < 8:
            config["model_cache_size"] = 1
            config["lazy_loading"] = True
        elif self.system_info["memory_gb"] >= 32:
            config["model_cache_size"] = 4
        
        self.optimization_config["model_loading"] = config
        return config
    
    def optimize_streaming(self):
        """Optimize streaming configuration"""
        config = {
            "chunk_size": 1024,
            "buffer_size": 8192,
            "max_concurrent_streams": 50,
            "backpressure_threshold": 0.8
        }
        
        # Adjust based on CPU cores
        cpu_cores = self.system_info["cpu_count"]
        if cpu_cores >= 8:
            config["max_concurrent_streams"] = 100
            config["buffer_size"] = 16384
        elif cpu_cores < 4:
            config["max_concurrent_streams"] = 25
            config["buffer_size"] = 4096
        
        self.optimization_config["streaming"] = config
        return config
    
    def optimize_gpu_settings(self):
        """Optimize GPU settings if available"""
        if not self.system_info["gpu_available"]:
            return {"enabled": False}
        
        config = {
            "enabled": True,
            "device": "cuda:0",
            "mixed_precision": True,
            "memory_fraction": 0.8,
            "allow_growth": True
        }
        
        # Adjust based on GPU memory
        if self.system_info["gpu_memory"]:
            gpu_memory = self.system_info["gpu_memory"][0]
            if gpu_memory < 8:
                config["memory_fraction"] = 0.6
            elif gpu_memory >= 16:
                config["memory_fraction"] = 0.9
        
        self.optimization_config["gpu"] = config
        return config
    
    def optimize_database(self):
        """Optimize database configuration"""
        config = {
            "pool_size": 20,
            "max_overflow": 30,
            "pool_timeout": 30,
            "pool_recycle": 3600,
            "echo": False
        }
        
        # Adjust based on system resources
        if self.system_info["memory_gb"] >= 16:
            config["pool_size"] = 50
            config["max_overflow"] = 100
        
        self.optimization_config["database"] = config
        return config
    
    def optimize_redis(self):
        """Optimize Redis configuration"""
        config = {
            "max_connections": 100,
            "socket_timeout": 5,
            "socket_connect_timeout": 5,
            "retry_on_timeout": True,
            "health_check_interval": 30
        }
        
        # Adjust based on system resources
        if self.system_info["memory_gb"] >= 16:
            config["max_connections"] = 200
        
        self.optimization_config["redis"] = config
        return config
    
    def optimize_worker_processes(self):
        """Optimize worker process configuration"""
        cpu_cores = self.system_info["cpu_count"]
        
        # Calculate optimal worker count
        if cpu_cores <= 2:
            workers = 1
        elif cpu_cores <= 4:
            workers = 2
        elif cpu_cores <= 8:
            workers = 4
        else:
            workers = min(cpu_cores, 8)
        
        config = {
            "workers": workers,
            "worker_class": "uvicorn.workers.UvicornWorker",
            "worker_connections": 1000,
            "max_requests": 1000,
            "max_requests_jitter": 100,
            "preload_app": True
        }
        
        self.optimization_config["workers"] = config
        return config
    
    def generate_environment_config(self):
        """Generate optimized environment configuration"""
        env_config = {
            # Server Configuration
            "HOST": "0.0.0.0",
            "PORT": "8000",
            "WORKERS": str(self.optimization_config["workers"]["workers"]),
            
            # TTS Configuration
            "TTS_AGREE_TO_CPML": "1",
            "TTS_MODEL_PATH": "tts_models/multilingual/multi-dataset/xtts_v2",
            "TTS_MODEL_CACHE_SIZE": str(self.optimization_config["model_loading"]["model_cache_size"]),
            "TTS_PRELOAD_MODELS": str(self.optimization_config["model_loading"]["preload_models"]),
            "TTS_LAZY_LOADING": str(self.optimization_config["model_loading"]["lazy_loading"]),
            
            # Streaming Configuration
            "STREAMING_CHUNK_SIZE": str(self.optimization_config["streaming"]["chunk_size"]),
            "STREAMING_BUFFER_SIZE": str(self.optimization_config["streaming"]["buffer_size"]),
            "STREAMING_MAX_CONCURRENT": str(self.optimization_config["streaming"]["max_concurrent_streams"]),
            
            # Database Configuration
            "DATABASE_POOL_SIZE": str(self.optimization_config["database"]["pool_size"]),
            "DATABASE_MAX_OVERFLOW": str(self.optimization_config["database"]["max_overflow"]),
            
            # Redis Configuration
            "REDIS_MAX_CONNECTIONS": str(self.optimization_config["redis"]["max_connections"]),
            
            # Logging
            "LOG_LEVEL": "INFO",
            "PYTHONUNBUFFERED": "1"
        }
        
        # Add GPU configuration if available
        if self.optimization_config["gpu"]["enabled"]:
            env_config.update({
                "CUDA_VISIBLE_DEVICES": "0",
                "TORCH_CUDA_ALLOC_CONF": "max_split_size_mb:512",
                "TTS_GPU_ENABLED": "true",
                "TTS_GPU_MEMORY_FRACTION": str(self.optimization_config["gpu"]["memory_fraction"])
            })
        
        return env_config
    
    def generate_docker_compose_override(self):
        """Generate Docker Compose override for optimization"""
        override = {
            "version": "3.8",
            "services": {
                "tts-service": {
                    "deploy": {
                        "resources": {
                            "limits": {
                                "memory": f"{int(self.system_info['memory_gb'] * 0.8)}G",
                                "cpus": str(self.system_info["cpu_count"])
                            },
                            "reservations": {
                                "memory": f"{int(self.system_info['memory_gb'] * 0.4)}G",
                                "cpus": str(max(1, self.system_info["cpu_count"] // 2))
                            }
                        }
                    },
                    "environment": self.generate_environment_config(),
                    "ulimits": {
                        "nofile": {
                            "soft": 65536,
                            "hard": 65536
                        }
                    }
                }
            }
        }
        
        # Add GPU support if available
        if self.system_info["gpu_available"]:
            override["services"]["tts-service"]["deploy"]["resources"]["reservations"]["devices"] = [
                {
                    "driver": "nvidia",
                    "count": 1,
                    "capabilities": ["gpu"]
                }
            ]
        
        return override
    
    def generate_nginx_config(self):
        """Generate optimized Nginx configuration"""
        config = f"""
upstream tts_backend {{
    least_conn;
    server tts-service:8000 max_fails=3 fail_timeout=30s;
    keepalive 32;
}}

server {{
    listen 80;
    server_name _;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
    
    # Connection limits
    limit_conn_zone $binary_remote_addr zone=conn_limit_per_ip:10m;
    limit_conn conn_limit_per_ip 20;
    
    # Timeouts
    proxy_connect_timeout 5s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
    
    # Buffering
    proxy_buffering on;
    proxy_buffer_size 4k;
    proxy_buffers 8 4k;
    proxy_busy_buffers_size 8k;
    
    # Health check
    location /v1/health {{
        proxy_pass http://tts_backend;
        access_log off;
    }}
    
    # API endpoints
    location /v1/ {{
        proxy_pass http://tts_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Streaming support
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
    }}
    
    # Static files
    location /docs {{
        proxy_pass http://tts_backend;
        proxy_set_header Host $host;
    }}
}}
"""
        return config
    
    def run_optimization(self):
        """Run all optimization steps"""
        print("🔧 Starting TTS Service Performance Optimization")
        print(f"📊 System Info: {self.system_info['cpu_count']} CPUs, {self.system_info['memory_gb']:.1f}GB RAM")
        
        if self.system_info["gpu_available"]:
            print(f"🎮 GPU Available: {self.system_info['gpu_count']} device(s)")
            for i, memory in enumerate(self.system_info["gpu_memory"]):
                print(f"   GPU {i}: {memory:.1f}GB")
        
        print("\n⚙️  Optimizing configurations...")
        
        # Run all optimizations
        self.optimize_model_loading()
        self.optimize_streaming()
        self.optimize_gpu_settings()
        self.optimize_database()
        self.optimize_redis()
        self.optimize_worker_processes()
        
        print("✅ Optimization complete!")
        return self.optimization_config
    
    def save_configurations(self, output_dir="optimized_configs"):
        """Save all optimized configurations to files"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Save optimization config
        with open(output_path / "optimization_config.json", "w") as f:
            json.dump(self.optimization_config, f, indent=2)
        
        # Save environment config
        env_config = self.generate_environment_config()
        with open(output_path / ".env.optimized", "w") as f:
            for key, value in env_config.items():
                f.write(f"{key}={value}\n")
        
        # Save Docker Compose override
        override = self.generate_docker_compose_override()
        with open(output_path / "docker-compose.override.yml", "w") as f:
            import yaml
            yaml.dump(override, f, default_flow_style=False)
        
        # Save Nginx config
        nginx_config = self.generate_nginx_config()
        with open(output_path / "nginx.conf", "w") as f:
            f.write(nginx_config)
        
        print(f"📁 Configurations saved to {output_dir}/")
        print("   - optimization_config.json")
        print("   - .env.optimized")
        print("   - docker-compose.override.yml")
        print("   - nginx.conf")


def main():
    """Main optimization script"""
    parser = argparse.ArgumentParser(description="Optimize TTS Service Performance")
    parser.add_argument("--output-dir", default="optimized_configs", 
                       help="Output directory for configurations")
    parser.add_argument("--save", action="store_true", 
                       help="Save configurations to files")
    parser.add_argument("--show-config", action="store_true", 
                       help="Show optimization configuration")
    
    args = parser.parse_args()
    
    optimizer = PerformanceOptimizer()
    config = optimizer.run_optimization()
    
    if args.show_config:
        print("\n📋 Optimization Configuration:")
        print(json.dumps(config, indent=2))
    
    if args.save:
        optimizer.save_configurations(args.output_dir)
    
    print("\n🚀 Performance optimization complete!")
    print("💡 Apply the generated configurations to your deployment.")


if __name__ == "__main__":
    main()
