"""Load test for the inventory API. See README for usage."""

import asyncio
import random
import string
import threading
import time

import httpx

BASE = "http://127.0.0.1:8000"
WARM_CONCURRENCY = 20
WARM_REQUESTS = 200
STRESS_CONCURRENCY = 400
STRESS_REQUESTS = 4000
HEALTH_INTERVAL_S = 0.02
MAX_HEALTH_P99_MS = 25.0


def random_sku() -> str:
    return "SKU-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


def health_prober(target: dict[str, list[float]], stop: threading.Event) -> None:
    with httpx.Client(timeout=5.0) as client:
        while not stop.is_set():
            t0 = time.perf_counter()
            try:
                r = client.get(f"{BASE}/health")
                r.raise_for_status()
                target["latencies"].append(time.perf_counter() - t0)
            except Exception:
                target["latencies"].append(float("inf"))
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


def summarize(latencies: list[float]) -> tuple[float, float]:
    if not latencies:
        return 0.0, float("inf")
    values = sorted(latencies)
    return values[len(values) // 2], values[int(len(values) * 0.99)]


async def main() -> None:
    print(
        f"warm: {WARM_CONCURRENCY}×{WARM_REQUESTS} | "
        f"stress: {STRESS_CONCURRENCY}×{STRESS_REQUESTS} | "
        f"stress /health p99 must be ≤ {MAX_HEALTH_P99_MS:.0f} ms\n",
    )

    warm_results: list = []
    stress_results: list = []
    warm_health_latencies: list[float] = []
    stress_health_latencies: list[float] = []
    current_health_latencies = {"latencies": warm_health_latencies}
    stop_probe = threading.Event()
    probe_thread = threading.Thread(
        target=health_prober,
        args=(current_health_latencies, stop_probe),
        daemon=True,
    )
    probe_thread.start()

    async def run_phase(
        client: httpx.AsyncClient,
        *,
        concurrency: int,
        total_requests: int,
        results: list,
    ) -> tuple[float, float]:
        sem = asyncio.Semaphore(concurrency)

        async def throttled() -> None:
            async with sem:
                await send_check(client, results)

        t_start = time.perf_counter()
        tasks = [asyncio.create_task(throttled()) for _ in range(total_requests)]
        await asyncio.gather(*tasks)
        t_end = time.perf_counter()
        return t_start, t_end

    async with httpx.AsyncClient(timeout=30.0) as client:
        await send_check(client, [])  # warm-up
        warm_start, warm_end = await run_phase(
            client,
            concurrency=WARM_CONCURRENCY,
            total_requests=WARM_REQUESTS,
            results=warm_results,
        )
        current_health_latencies["latencies"] = stress_health_latencies
        stress_start, stress_end = await run_phase(
            client,
            concurrency=STRESS_CONCURRENCY,
            total_requests=STRESS_REQUESTS,
            results=stress_results,
        )

    stop_probe.set()
    probe_thread.join(timeout=5.0)

    warm_wall = warm_end - warm_start
    warm_ok = sum(1 for r in warm_results if r[0] == "ok")
    warm_errs = sum(1 for r in warm_results if r[0] == "err")
    warm_check_p50, warm_check_p99 = summarize(
        [r[2] for r in warm_results if r[0] == "ok"]
    )
    warm_health_p50, warm_health_p99 = summarize(warm_health_latencies)

    stress_wall = stress_end - stress_start
    stress_ok = sum(1 for r in stress_results if r[0] == "ok")
    stress_errs = sum(1 for r in stress_results if r[0] == "err")
    stress_check_p50, stress_check_p99 = summarize(
        [r[2] for r in stress_results if r[0] == "ok"]
    )
    stress_health_p50, stress_health_p99 = summarize(stress_health_latencies)

    print(f"warm wall:        {warm_wall:.2f}s")
    print(
        f"warm /check:      ok {warm_ok}  errors {warm_errs}  "
        f"throughput {warm_ok / warm_wall:,.0f} req/s"
    )
    print(
        f"warm latencies:   /check p50 {warm_check_p50*1000:.1f} ms  "
        f"p99 {warm_check_p99*1000:.1f} ms | "
        f"/health p50 {warm_health_p50*1000:.1f} ms  "
        f"p99 {warm_health_p99*1000:.1f} ms"
    )
    print()
    print(f"stress wall:      {stress_wall:.2f}s")
    print(
        f"stress /check:    ok {stress_ok}  errors {stress_errs}  "
        f"throughput {stress_ok / stress_wall:,.0f} req/s"
    )
    print(
        f"stress latencies: /check p50 {stress_check_p50*1000:.1f} ms  "
        f"p99 {stress_check_p99*1000:.1f} ms | "
        f"/health p50 {stress_health_p50*1000:.1f} ms  "
        f"p99 {stress_health_p99*1000:.1f} ms"
    )
    print()

    if stress_health_p99 * 1000 <= MAX_HEALTH_P99_MS:
        print(
            f"PASS — stress /health p99 {stress_health_p99*1000:.1f} ms <= {MAX_HEALTH_P99_MS:.0f} ms",
        )
        raise SystemExit(0)
    print(
        f"FAIL — stress /health p99 {stress_health_p99*1000:.1f} ms > {MAX_HEALTH_P99_MS:.0f} ms"
    )
    raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
