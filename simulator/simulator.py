#!/usr/bin/env python3
"""
Event Simulator for Aegis

Generates realistic test events and sends them to the ingestion service.
Creates test projects and API keys automatically on first run.
"""

import asyncio
import random
import json
import os
from datetime import datetime, UTC
from typing import Optional
import httpx

# Configuration from environment
API_SERVICE_URL = os.getenv("API_SERVICE_URL", "http://api_service:8000")
INGESTION_SERVICE_URL = os.getenv("INGESTION_SERVICE_URL", "http://ingestion_service:8001")
SIMULATOR_USER_EMAIL = os.getenv("SIMULATOR_USER_EMAIL", "simulator@example.com")
SIMULATOR_USER_PASSWORD = os.getenv("SIMULATOR_USER_PASSWORD", "simulator123")
EVENTS_PER_MINUTE = int(os.getenv("EVENTS_PER_MINUTE", "120"))

# Simulated services and their event patterns
SERVICES = [
    {
        "project_name": "E-Commerce API",
        "sources": ["order-service", "payment-service", "inventory-service"],
        "event_types": ["REQUEST", "ORDER_CREATED", "PAYMENT_PROCESSED", "STOCK_UPDATE"],
        "error_rate": 0.05,  # 5% errors
        "critical_rate": 0.01,  # 1% critical
    },
    {
        "project_name": "User Authentication",
        "sources": ["auth-service", "session-manager", "oauth-provider"],
        "event_types": ["LOGIN", "LOGOUT", "TOKEN_REFRESH", "PASSWORD_RESET"],
        "error_rate": 0.03,
        "critical_rate": 0.005,
    },
    {
        "project_name": "Analytics Pipeline",
        "sources": ["data-collector", "etl-worker", "report-generator"],
        "event_types": ["DATA_INGESTED", "TRANSFORM_COMPLETE", "REPORT_GENERATED", "METRIC"],
        "error_rate": 0.08,
        "critical_rate": 0.02,
    },
]

# Realistic payloads for different event types
def generate_payload(event_type: str, source: str) -> dict:
    """Generate realistic payload based on event type."""
    base = {
        "timestamp": datetime.now(UTC).isoformat(),
        "host": f"{source}-{random.randint(1, 5)}.aegis.local",
    }
    
    if event_type == "REQUEST":
        return {
            **base,
            "method": random.choice(["GET", "POST", "PUT", "DELETE"]),
            "path": random.choice(["/api/users", "/api/orders", "/api/products", "/api/checkout"]),
            "status_code": random.choice([200, 200, 200, 201, 400, 404, 500]),
            "user_agent": "Mozilla/5.0",
        }
    elif event_type in ["ORDER_CREATED", "PAYMENT_PROCESSED"]:
        return {
            **base,
            "order_id": f"ORD-{random.randint(10000, 99999)}",
            "amount": round(random.uniform(10, 500), 2),
            "currency": "USD",
        }
    elif event_type in ["LOGIN", "LOGOUT"]:
        return {
            **base,
            "user_id": f"USR-{random.randint(1000, 9999)}",
            "ip_address": f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}",
        }
    elif event_type == "METRIC":
        return {
            **base,
            "metric_name": random.choice(["cpu_usage", "memory_usage", "disk_io", "network_in"]),
            "value": round(random.uniform(0, 100), 2),
            "unit": "%",
        }
    else:
        return {
            **base,
            "details": f"Event {event_type} from {source}",
        }


def generate_severity(error_rate: float, critical_rate: float) -> str:
    """Generate severity based on configured rates."""
    r = random.random()
    if r < critical_rate:
        return "CRITICAL"
    elif r < error_rate:
        return "ERROR"
    elif r < error_rate + 0.1:
        return "WARN"
    elif r < 0.3:
        return "DEBUG"
    else:
        return "INFO"


class Simulator:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.token: Optional[str] = None
        self.api_keys: dict[str, str] = {}  # project_name -> api_key
    
    async def setup(self):
        """Set up user, projects, and API keys."""
        print("🚀 Setting up simulator...")
        
        # Register or login
        await self._ensure_user()
        
        # Create projects and get API keys
        for service in SERVICES:
            await self._ensure_project(service["project_name"])
        
        print(f"✅ Setup complete! {len(self.api_keys)} projects ready.")
    
    async def _ensure_user(self):
        """Register or login the simulator user."""
        # Try to register first
        try:
            response = await self.client.post(
                f"{API_SERVICE_URL}/api/v1/auth/register",
                json={"email": SIMULATOR_USER_EMAIL, "password": SIMULATOR_USER_PASSWORD},
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 201:
                print(f"  ✓ Created user: {SIMULATOR_USER_EMAIL}")
            elif response.status_code == 400:
                print(f"  ℹ User already exists: {SIMULATOR_USER_EMAIL}")
            elif response.status_code == 422:
                print(f"  ⚠ Register validation error: {response.text}")
        except Exception as e:
            print(f"  ⚠ Register exception: {e}")
        
        # Login
        response = await self.client.post(
            f"{API_SERVICE_URL}/api/v1/auth/login",
            json={"email": SIMULATOR_USER_EMAIL, "password": SIMULATOR_USER_PASSWORD},
            headers={"Content-Type": "application/json"}
        )
        if response.status_code != 200:
            print(f"  ❌ Login failed: {response.status_code} - {response.text}")
            response.raise_for_status()
        self.token = response.json()["access_token"]
        print(f"  ✓ Logged in as: {SIMULATOR_USER_EMAIL}")
    
    async def _ensure_project(self, project_name: str):
        """Create project if needed and get API key."""
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # List existing projects
        response = await self.client.get(
            f"{API_SERVICE_URL}/api/v1/projects",
            headers=headers
        )
        response.raise_for_status()
        projects = response.json()["items"]
        
        # Find or create project
        project = next((p for p in projects if p["name"] == project_name), None)
        
        if not project:
            response = await self.client.post(
                f"{API_SERVICE_URL}/api/v1/projects",
                headers=headers,
                json={"name": project_name, "description": f"Simulated {project_name}"}
            )
            response.raise_for_status()
            project = response.json()
            print(f"  ✓ Created project: {project_name}")
        else:
            print(f"  ✓ Found project: {project_name}")
        
        # Check for existing API key
        response = await self.client.get(
            f"{API_SERVICE_URL}/api/v1/projects/{project['id']}/api-keys",
            headers=headers
        )
        response.raise_for_status()
        keys = response.json()["items"]
        active_keys = [k for k in keys if k["is_active"]]
        
        if active_keys:
            # We can't retrieve the full key, need to create a new one
            # Check if we have a simulator key
            sim_key = next((k for k in active_keys if k["name"] == "simulator"), None)
            if sim_key:
                # Revoke old one and create new
                await self.client.delete(
                    f"{API_SERVICE_URL}/api/v1/projects/{project['id']}/api-keys/{sim_key['id']}",
                    headers=headers
                )
        
        # Create new API key
        response = await self.client.post(
            f"{API_SERVICE_URL}/api/v1/projects/{project['id']}/api-keys",
            headers=headers,
            json={"name": "simulator"}
        )
        response.raise_for_status()
        key_data = response.json()
        self.api_keys[project_name] = key_data["key"]
        print(f"  ✓ API key ready for: {project_name}")
    
    async def run(self):
        """Main simulation loop."""
        print(f"\n📡 Starting event simulation ({EVENTS_PER_MINUTE} events/min)...")
        print("   Press Ctrl+C to stop\n")
        
        # Calculate delay between events
        delay = 60.0 / EVENTS_PER_MINUTE
        
        event_count = 0
        while True:
            try:
                # Pick a random service
                service = random.choice(SERVICES)
                project_name = service["project_name"]
                api_key = self.api_keys.get(project_name)
                
                if not api_key:
                    continue
                
                # Generate event
                source = random.choice(service["sources"])
                event_type = random.choice(service["event_types"])
                severity = generate_severity(service["error_rate"], service["critical_rate"])
                latency = random.randint(5, 500) if event_type == "REQUEST" else None
                payload = generate_payload(event_type, source)
                
                event = {
                    "source": source,
                    "event_type": event_type,
                    "severity": severity,
                    "latency_ms": latency,
                    "payload": payload,
                }
                
                # Send event
                response = await self.client.post(
                    f"{INGESTION_SERVICE_URL}/api/v1/events",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=event
                )
                
                event_count += 1
                severity_emoji = {
                    "DEBUG": "🔍",
                    "INFO": "ℹ️ ",
                    "WARN": "⚠️ ",
                    "ERROR": "❌",
                    "CRITICAL": "🔥"
                }.get(severity, "  ")
                
                if response.status_code == 201:
                    print(f"{severity_emoji} [{event_count}] {project_name[:20]:<20} | {source:<20} | {event_type:<20} | {severity}")
                else:
                    print(f"⚠️  Failed to send event: {response.status_code}")
                
                # Wait before next event
                await asyncio.sleep(delay + random.uniform(-0.5, 0.5))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                await asyncio.sleep(5)
        
        print(f"\n👋 Simulator stopped. Sent {event_count} events.")
    
    async def close(self):
        await self.client.aclose()


async def main():
    print("=" * 60)
    print("   AEGIS EVENT SIMULATOR")
    print("=" * 60)
    
    # Wait for services to be ready
    print("\n⏳ Waiting for services to be ready...")
    await asyncio.sleep(5)
    
    simulator = Simulator()
    try:
        await simulator.setup()
        await simulator.run()
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down...")
    finally:
        await simulator.close()


if __name__ == "__main__":
    asyncio.run(main())

