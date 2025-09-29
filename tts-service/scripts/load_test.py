#!/usr/bin/env python3
"""
Load Testing Script for TTS Service
Tests performance, latency, and throughput under various load conditions
"""

import asyncio
import aiohttp
import time
import json
import argparse
import statistics
from typing import List, Dict, Any
import matplotlib.pyplot as plt
import pandas as pd
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import sys


@dataclass
class TestResult:
    """Result of a single test request"""
    success: bool
    response_time: float
    status_code: int
    error_message: str = ""
    audio_size: int = 0


class TTSLoadTester:
    """Load testing tool for TTS service"""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.results: List[TestResult] = []
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60),
            headers={'Authorization': f'Bearer {self.api_key}'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def single_request(self, text: str, voice_id: str = "naija_female") -> TestResult:
        """Make a single TTS request"""
        start_time = time.time()
        
        try:
            data = {
                'text': text,
                'voice_id': voice_id,
                'streaming': 'true'
            }
            
            async with self.session.post(
                f"{self.base_url}/v1/synthesize",
                data=data
            ) as response:
                response_time = time.time() - start_time
                
                if response.status == 200:
                    audio_data = await response.read()
                    return TestResult(
                        success=True,
                        response_time=response_time,
                        status_code=response.status,
                        audio_size=len(audio_data)
                    )
                else:
                    error_text = await response.text()
                    return TestResult(
                        success=False,
                        response_time=response_time,
                        status_code=response.status,
                        error_message=error_text
                    )
        
        except Exception as e:
            response_time = time.time() - start_time
            return TestResult(
                success=False,
                response_time=response_time,
                status_code=0,
                error_message=str(e)
            )
    
    async def concurrent_requests(self, num_requests: int, text: str, voice_id: str = "naija_female") -> List[TestResult]:
        """Make multiple concurrent requests"""
        tasks = []
        for _ in range(num_requests):
            task = self.single_request(text, voice_id)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                processed_results.append(TestResult(
                    success=False,
                    response_time=0,
                    status_code=0,
                    error_message=str(result)
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def ramp_up_test(self, max_concurrent: int, ramp_duration: int, text: str) -> List[TestResult]:
        """Ramp up test - gradually increase load"""
        print(f"🚀 Starting ramp-up test: {max_concurrent} concurrent users over {ramp_duration}s")
        
        all_results = []
        start_time = time.time()
        
        while time.time() - start_time < ramp_duration:
            # Calculate current concurrent users
            elapsed = time.time() - start_time
            current_concurrent = int((elapsed / ramp_duration) * max_concurrent)
            
            if current_concurrent > 0:
                print(f"   Testing with {current_concurrent} concurrent users...")
                results = await self.concurrent_requests(current_concurrent, text)
                all_results.extend(results)
                
                # Brief pause between batches
                await asyncio.sleep(1)
        
        return all_results
    
    async def sustained_load_test(self, concurrent_users: int, duration: int, text: str) -> List[TestResult]:
        """Sustained load test - maintain constant load"""
        print(f"⏱️  Starting sustained load test: {concurrent_users} users for {duration}s")
        
        all_results = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            # Launch batch of requests
            results = await self.concurrent_requests(concurrent_users, text)
            all_results.extend(results)
            
            # Brief pause between batches
            await asyncio.sleep(0.5)
        
        return all_results
    
    async def spike_test(self, base_load: int, spike_load: int, spike_duration: int, text: str) -> List[TestResult]:
        """Spike test - sudden increase in load"""
        print(f"📈 Starting spike test: {base_load} -> {spike_load} users for {spike_duration}s")
        
        all_results = []
        
        # Base load
        print("   Running base load...")
        base_results = await self.sustained_load_test(base_load, 30, text)
        all_results.extend(base_results)
        
        # Spike load
        print(f"   Running spike load ({spike_load} users)...")
        spike_results = await self.sustained_load_test(spike_load, spike_duration, text)
        all_results.extend(spike_results)
        
        # Return to base load
        print("   Returning to base load...")
        recovery_results = await self.sustained_load_test(base_load, 30, text)
        all_results.extend(recovery_results)
        
        return all_results
    
    def analyze_results(self, results: List[TestResult]) -> Dict[str, Any]:
        """Analyze test results and generate statistics"""
        if not results:
            return {}
        
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]
        
        response_times = [r.response_time for r in successful_results]
        audio_sizes = [r.audio_size for r in successful_results]
        
        analysis = {
            "total_requests": len(results),
            "successful_requests": len(successful_results),
            "failed_requests": len(failed_results),
            "success_rate": len(successful_results) / len(results) if results else 0,
            "error_rate": len(failed_results) / len(results) if results else 0,
            "response_times": {
                "min": min(response_times) if response_times else 0,
                "max": max(response_times) if response_times else 0,
                "mean": statistics.mean(response_times) if response_times else 0,
                "median": statistics.median(response_times) if response_times else 0,
                "p95": self._percentile(response_times, 95) if response_times else 0,
                "p99": self._percentile(response_times, 99) if response_times else 0,
                "std_dev": statistics.stdev(response_times) if len(response_times) > 1 else 0
            },
            "audio_sizes": {
                "min": min(audio_sizes) if audio_sizes else 0,
                "max": max(audio_sizes) if audio_sizes else 0,
                "mean": statistics.mean(audio_sizes) if audio_sizes else 0,
                "median": statistics.median(audio_sizes) if audio_sizes else 0
            },
            "throughput": {
                "requests_per_second": len(successful_results) / max(response_times) if response_times else 0,
                "total_duration": max(response_times) if response_times else 0
            },
            "errors": {
                "status_codes": {},
                "error_messages": {}
            }
        }
        
        # Analyze errors
        for result in failed_results:
            status_code = result.status_code
            if status_code in analysis["errors"]["status_codes"]:
                analysis["errors"]["status_codes"][status_code] += 1
            else:
                analysis["errors"]["status_codes"][status_code] = 1
            
            error_msg = result.error_message[:100]  # Truncate long messages
            if error_msg in analysis["errors"]["error_messages"]:
                analysis["errors"]["error_messages"][error_msg] += 1
            else:
                analysis["errors"]["error_messages"][error_msg] = 1
        
        return analysis
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of data"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def print_analysis(self, analysis: Dict[str, Any], test_name: str):
        """Print analysis results"""
        print(f"\n📊 {test_name} Results:")
        print("=" * 50)
        
        print(f"Total Requests: {analysis['total_requests']}")
        print(f"Successful: {analysis['successful_requests']}")
        print(f"Failed: {analysis['failed_requests']}")
        print(f"Success Rate: {analysis['success_rate']:.2%}")
        print(f"Error Rate: {analysis['error_rate']:.2%}")
        
        print(f"\nResponse Times:")
        rt = analysis['response_times']
        print(f"  Min: {rt['min']:.3f}s")
        print(f"  Max: {rt['max']:.3f}s")
        print(f"  Mean: {rt['mean']:.3f}s")
        print(f"  Median: {rt['median']:.3f}s")
        print(f"  P95: {rt['p95']:.3f}s")
        print(f"  P99: {rt['p99']:.3f}s")
        print(f"  Std Dev: {rt['std_dev']:.3f}s")
        
        print(f"\nThroughput:")
        tp = analysis['throughput']
        print(f"  Requests/sec: {tp['requests_per_second']:.2f}")
        print(f"  Total Duration: {tp['total_duration']:.2f}s")
        
        if analysis['errors']['status_codes']:
            print(f"\nError Status Codes:")
            for status, count in analysis['errors']['status_codes'].items():
                print(f"  {status}: {count}")
        
        if analysis['errors']['error_messages']:
            print(f"\nError Messages:")
            for msg, count in list(analysis['errors']['error_messages'].items())[:5]:
                print(f"  {msg}: {count}")
    
    def save_results(self, results: List[TestResult], analysis: Dict[str, Any], filename: str):
        """Save results to JSON file"""
        data = {
            "timestamp": time.time(),
            "analysis": analysis,
            "raw_results": [
                {
                    "success": r.success,
                    "response_time": r.response_time,
                    "status_code": r.status_code,
                    "error_message": r.error_message,
                    "audio_size": r.audio_size
                }
                for r in results
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"💾 Results saved to {filename}")
    
    def plot_results(self, results: List[TestResult], filename: str):
        """Create performance plots"""
        if not results:
            return
        
        # Prepare data
        timestamps = list(range(len(results)))
        response_times = [r.response_time for r in results]
        success_flags = [1 if r.success else 0 for r in results]
        
        # Create plots
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        # Response time over time
        ax1.plot(timestamps, response_times, alpha=0.7)
        ax1.set_title('Response Time Over Time')
        ax1.set_xlabel('Request Number')
        ax1.set_ylabel('Response Time (s)')
        ax1.grid(True)
        
        # Success rate over time (rolling window)
        window_size = min(50, len(results) // 10)
        if window_size > 1:
            rolling_success = pd.Series(success_flags).rolling(window=window_size).mean()
            ax2.plot(timestamps, rolling_success)
            ax2.set_title(f'Success Rate Over Time (Window: {window_size})')
            ax2.set_xlabel('Request Number')
            ax2.set_ylabel('Success Rate')
            ax2.set_ylim(0, 1)
            ax2.grid(True)
        
        # Response time histogram
        ax3.hist(response_times, bins=50, alpha=0.7, edgecolor='black')
        ax3.set_title('Response Time Distribution')
        ax3.set_xlabel('Response Time (s)')
        ax3.set_ylabel('Frequency')
        ax3.grid(True)
        
        # Audio size distribution
        audio_sizes = [r.audio_size for r in results if r.success]
        if audio_sizes:
            ax4.hist(audio_sizes, bins=30, alpha=0.7, edgecolor='black')
            ax4.set_title('Audio Size Distribution')
            ax4.set_xlabel('Audio Size (bytes)')
            ax4.set_ylabel('Frequency')
            ax4.grid(True)
        
        plt.tight_layout()
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"📈 Performance plots saved to {filename}")


async def main():
    """Main load testing function"""
    parser = argparse.ArgumentParser(description="Load test TTS service")
    parser.add_argument("--url", default="http://localhost:8000", help="TTS service URL")
    parser.add_argument("--api-key", default="sk_test_1234567890abcdef", help="API key")
    parser.add_argument("--test-type", choices=["concurrent", "ramp-up", "sustained", "spike"], 
                       default="concurrent", help="Type of test to run")
    parser.add_argument("--concurrent", type=int, default=10, help="Number of concurrent users")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")
    parser.add_argument("--text", default="Hello, this is a load test for the TTS service.", 
                       help="Text to synthesize")
    parser.add_argument("--voice", default="naija_female", help="Voice ID to use")
    parser.add_argument("--output", default="load_test_results", help="Output file prefix")
    
    args = parser.parse_args()
    
    print("🧪 TTS Service Load Testing")
    print("=" * 50)
    print(f"URL: {args.url}")
    print(f"Test Type: {args.test_type}")
    print(f"Concurrent Users: {args.concurrent}")
    print(f"Duration: {args.duration}s")
    print(f"Text: {args.text}")
    print(f"Voice: {args.voice}")
    
    async with TTSLoadTester(args.url, args.api_key) as tester:
        # Run appropriate test
        if args.test_type == "concurrent":
            results = await tester.concurrent_requests(args.concurrent, args.text, args.voice)
        elif args.test_type == "ramp-up":
            results = await tester.ramp_up_test(args.concurrent, args.duration, args.text)
        elif args.test_type == "sustained":
            results = await tester.sustained_load_test(args.concurrent, args.duration, args.text)
        elif args.test_type == "spike":
            spike_load = args.concurrent * 3
            results = await tester.spike_test(args.concurrent, spike_load, 30, args.text)
        
        # Analyze results
        analysis = tester.analyze_results(results)
        tester.print_analysis(analysis, args.test_type.title())
        
        # Save results
        timestamp = int(time.time())
        json_file = f"{args.output}_{args.test_type}_{timestamp}.json"
        plot_file = f"{args.output}_{args.test_type}_{timestamp}.png"
        
        tester.save_results(results, analysis, json_file)
        tester.plot_results(results, plot_file)
        
        # Performance assessment
        print(f"\n🎯 Performance Assessment:")
        if analysis['success_rate'] >= 0.99:
            print("✅ Excellent: Success rate >= 99%")
        elif analysis['success_rate'] >= 0.95:
            print("✅ Good: Success rate >= 95%")
        elif analysis['success_rate'] >= 0.90:
            print("⚠️  Fair: Success rate >= 90%")
        else:
            print("❌ Poor: Success rate < 90%")
        
        if analysis['response_times']['p95'] <= 2.0:
            print("✅ Excellent: P95 latency <= 2s")
        elif analysis['response_times']['p95'] <= 5.0:
            print("✅ Good: P95 latency <= 5s")
        else:
            print("⚠️  Poor: P95 latency > 5s")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Load test interrupted by user")
    except Exception as e:
        print(f"\n❌ Load test failed: {e}")
        sys.exit(1)
