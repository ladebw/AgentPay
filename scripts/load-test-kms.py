#!/usr/bin/env python3
"""
Load test for KMS signing endpoint.
Usage: python load-test-kms.py [--url URL] [--requests N] [--concurrency C]
"""
import asyncio
import aiohttp
import time
import argparse
import sys
from typing import List, Dict, Any


async def make_request(session: aiohttp.ClientSession, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Make a single POST request to the signing endpoint."""
    async with session.post(url, json=payload) as resp:
        if resp.status != 200:
            text = await resp.text()
            raise Exception(f"Request failed with status {resp.status}: {text}")
        return await resp.json()


async def run_load_test(url: str, num_requests: int, concurrency: int) -> None:
    """Run concurrent load test."""
    # Simple payload
    payload = {"transaction_id": "test-{i}"}
    
    # Semaphore to limit concurrency
    semaphore = asyncio.Semaphore(concurrency)
    
    async def bounded_request(session, i):
        async with semaphore:
            return await make_request(session, url, {"transaction_id": f"test-{i}"})
    
    start = time.time()
    async with aiohttp.ClientSession() as session:
        tasks = [bounded_request(session, i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    duration = time.time() - start
    
    # Count successes and failures
    successes = sum(1 for r in results if not isinstance(r, Exception))
    failures = num_requests - successes
    
    print(f"Load test completed:")
    print(f"  Requests: {num_requests}")
    print(f"  Concurrency: {concurrency}")
    print(f"  Duration: {duration:.2f}s")
    print(f"  Throughput: {num_requests/duration:.2f} req/sec")
    print(f"  Successes: {successes}")
    print(f"  Failures: {failures}")
    if failures > 0:
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                print(f"    Request {i}: {r}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Load test KMS signing endpoint")
    parser.add_argument("--url", default="http://localhost:8000/api/v1/transactions/sign-test",
                        help="Endpoint URL (default: %(default)s)")
    parser.add_argument("--requests", type=int, default=100,
                        help="Number of requests (default: %(default)s)")
    parser.add_argument("--concurrency", type=int, default=10,
                        help="Number of concurrent requests (default: %(default)s)")
    args = parser.parse_args()
    
    print(f"Starting load test for {args.url}")
    print(f"Configuration: {args.requests} requests, {args.concurrency} concurrent")
    asyncio.run(run_load_test(args.url, args.requests, args.concurrency))


if __name__ == "__main__":
    main()