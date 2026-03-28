"""Load test for the inventory API. See README for usage."""

import asyncio
import random
import string
import threading
import time

import httpx

BASE = "http://127.0.0.1:8000"
CONCURRENCY = 400
TOTAL_REQUESTS = 4000
HEALTH_INTERVAL_S = 0.02
MAX_HEALTH_P99_MS = 25.0


def random_sku() -> str:
    return "SKU-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


def health_prober(latencies: list[float], stop: threading.Event) -> None:
    with httpx.Client(timeout=5.0) as client:
        while not stop.is_set():
            t0 = time.perf_counter()
            try:
                r = client.get(f"{BASE}/health")
                r.raise_for_status()
                latencies.append(time.perf_counter() - t0)
            except Exception:
                latencies.append(float("inf"))
            time.sleep(HEALTH_INTERVAL_S)


async def send_check(client: httpx.AsyncClient, results: list) -> None:
    payload = {"sku": random_sku(), "quantity": random.randint(1, 50)}
    t0 = time.perf_counter()
    try:
        resp = await client.post(f"{BASE}/check", json=payload)
        elapsed = time.perf_counter() - t0
        results.append(("ok", resp.status_code, elapsed))
    except Exception as e:
        elapsed = time.perf_counter() - t0
        results.append(("err", str(e), elapsed))


async def main() -> None:
    print(
        f"{CONCURRENCY} concurrent × {TOTAL_REQUESTS} POST /check | "
        f"/health p99 must be ≤ {MAX_HEALTH_P99_MS:.0f} ms\n",
    )

    results: list = []
    health_latencies: list[float] = []
    stop_probe = threading.Event()
    probe_thread = threading.Thread(
        target=health_prober,
        args=(health_latencies, stop_probe),
        daemon=True,
    )
    probe_thread.start()

    sem = asyncio.Semaphore(CONCURRENCY)

    async def throttled(c: httpx.AsyncClient) -> None:
        async with sem:
            await send_check(c, results)

    async with httpx.AsyncClient(timeout=30.0) as client:
        await send_check(client, [])  # warm-up

        t_start = time.perf_counter()
        tasks = [asyncio.create_task(throttled(client)) for _ in range(TOTAL_REQUESTS)]
        await asyncio.gather(*tasks)
        t_end = time.perf_counter()

    stop_probe.set()
    probe_thread.join(timeout=5.0)

    wall = t_end - t_start
    ok = sum(1 for r in results if r[0] == "ok")
    errs = sum(1 for r in results if r[0] == "err")
    latencies = sorted(r[2] for r in results if r[0] == "ok")
    rps = ok / wall if wall > 0 else 0

    p50 = latencies[len(latencies) // 2] if latencies else 0.0
    p99 = latencies[int(len(latencies) * 0.99)] if latencies else 0.0

    health_latencies.sort()
    h_n = len(health_latencies)
    h_p50 = health_latencies[h_n // 2] if h_n else 0.0
    h_p99 = health_latencies[int(h_n * 0.99)] if h_n else float("inf")

    print(f"Wall time:        {wall:.2f}s")
    print(f"/check ok:        {ok}  errors: {errs}  throughput: {rps:,.0f} req/s")
    print(f"/check latency:   p50 {p50*1000:.1f} ms  p99 {p99*1000:.1f} ms")
    print(f"/health latency:  p50 {h_p50*1000:.1f} ms  p99 {h_p99*1000:.1f} ms  (n={h_n})")
    print()

    if h_p99 * 1000 <= MAX_HEALTH_P99_MS:
        print(
            f"PASS — /health p99 {h_p99*1000:.1f} ms <= {MAX_HEALTH_P99_MS:.0f} ms",
        )
        raise SystemExit(0)
    print(f"FAIL — /health p99 {h_p99*1000:.1f} ms > {MAX_HEALTH_P99_MS:.0f} ms")
    raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
