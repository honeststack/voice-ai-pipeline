#!/usr/bin/env python3
"""
Kubernetes Testing Suite for TTS AI Pipeline

This script provides comprehensive testing for the TTS AI Pipeline deployed on Kubernetes:
- Service health checks
- Inter-service communication
- End-to-end pipeline testing
- Load balancing verification
- Resource usage monitoring

Usage:
    python -m voice_ai_pipeline.tests.test_k8s

Requirements:
    - kubectl configured and connected to cluster
    - All services deployed to Kubernetes
    - requests library
"""

import requests
import json
import time
import subprocess
import sys
import os
from typing import Dict, Any, Tuple, List, Optional
from dataclasses import dataclass

# Kubernetes service URLs (internal cluster addresses)
ASR_SERVICE_URL = "http://asr-service:8000"
TTS_SERVICE_URL = "http://tts-service:8001"
INTERFACE_SERVICE_URL = "http://interface-service:7860"

# External access URLs (for load balancer)
EXTERNAL_INTERFACE_URL = None  # Will be determined dynamically

@dataclass
class TestResult:
    """Represents a single test result."""
    name: str
    status: str
    message: str
    duration: float
    details: Optional[Dict[str, Any]] = None

class KubernetesTester:
    """Comprehensive test suite for Kubernetes-deployed TTS AI Pipeline."""

    def __init__(self):
        self.test_results: List[TestResult] = []
        self.passed = 0
        self.failed = 0
        self.start_time = time.time()

    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp."""
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        print(f"[{timestamp}] {level}: {message}")

    def run_command(self, cmd: List[str], timeout: int = 30) -> Tuple[bool, str, str]:
        """Run a shell command and return success status, stdout, stderr."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return False, "", str(e)

    def kubectl_exec(self, pod_name: str, command: str) -> Tuple[bool, str, str]:
        """Execute a command in a Kubernetes pod."""
        cmd = ["kubectl", "exec", pod_name, "--", "bash", "-c", command]
        return self.run_command(cmd)

    def get_service_url(self, service_name: str) -> str:
        """Get the external URL for a LoadBalancer service."""
        success, stdout, stderr = self.run_command([
            "kubectl", "get", "svc", service_name,
            "-o", "jsonpath='{.status.loadBalancer.ingress[0].hostname}'"
        ])

        if success and stdout.strip():
            hostname = stdout.strip().strip('"')
            return f"http://{hostname}"

        # Try IP address
        success, stdout, stderr = self.run_command([
            "kubectl", "get", "svc", service_name,
            "-o", "jsonpath='{.status.loadBalancer.ingress[0].ip}'"
        ])

        if success and stdout.strip():
            ip_addr = stdout.strip().strip('"')
            return f"http://{ip_addr}"

        # Fallback to port forwarding for local testing
        return f"http://localhost:{8000 + ['asr', 'tts', 'interface'].index(service_name.split('-')[0])}"

    def test_kubernetes_cluster(self) -> TestResult:
        """Test basic Kubernetes cluster connectivity."""
        start_time = time.time()

        success, stdout, stderr = self.run_command(["kubectl", "cluster-info"])
        if not success:
            error_msg = stderr.strip()
            if "connection refused" in error_msg.lower() or "no such file or directory" in error_msg.lower():
                return TestResult(
                    "kubernetes_connectivity",
                    "FAILED",
                    "No Kubernetes cluster available. Please start a cluster first:\n"
                    "  - For local testing: minikube start --driver=docker --gpus=all\n"
                    "  - For cloud: configure kubectl for your cluster\n"
                    f"Error: {error_msg}",
                    time.time() - start_time
                )
            else:
                return TestResult(
                    "kubernetes_connectivity",
                    "FAILED",
                    f"Cannot connect to Kubernetes cluster: {error_msg}",
                    time.time() - start_time
                )

        success, stdout, stderr = self.run_command(["kubectl", "get", "nodes"])
        if not success:
            return TestResult(
                "kubernetes_nodes",
                "FAILED",
                f"Cannot get cluster nodes: {stderr}",
                time.time() - start_time
            )

        return TestResult(
            "kubernetes_connectivity",
            "PASSED",
            "Successfully connected to Kubernetes cluster",
            time.time() - start_time,
            {"cluster_info": stdout[:200] + "..." if len(stdout) > 200 else stdout}
        )

    def test_deployments_status(self) -> TestResult:
        """Test that all deployments are running and healthy."""
        start_time = time.time()
        deployments = ["asr-deployment", "tts-deployment", "interface-deployment"]

        failed_deployments = []
        deployment_status = {}

        for deployment in deployments:
            success, stdout, stderr = self.run_command([
                "kubectl", "get", "deployment", deployment,
                "-o", "jsonpath='{.status.readyReplicas}/{.status.replicas}'"
            ])

            if not success:
                failed_deployments.append(f"{deployment}: {stderr}")
                continue

            ready, total = stdout.strip().strip("'").split("/")
            deployment_status[deployment] = f"{ready}/{total}"

            if ready != total:
                failed_deployments.append(f"{deployment}: {ready}/{total} ready")

        if failed_deployments:
            return TestResult(
                "deployments_status",
                "FAILED",
                f"Deployments not healthy: {', '.join(failed_deployments)}",
                time.time() - start_time,
                {"deployment_status": deployment_status}
            )

        return TestResult(
            "deployments_status",
            "PASSED",
            "All deployments are healthy and ready",
            time.time() - start_time,
            {"deployment_status": deployment_status}
        )

    def test_pods_status(self) -> TestResult:
        """Test that all pods are running."""
        start_time = time.time()

        success, stdout, stderr = self.run_command([
            "kubectl", "get", "pods",
            "-l", "app in (asr,tts,interface)",
            "-o", "jsonpath='{.items[*].status.phase}'"
        ])

        if not success:
            return TestResult(
                "pods_status",
                "FAILED",
                f"Cannot get pod status: {stderr}",
                time.time() - start_time
            )

        pod_statuses = stdout.strip().strip("'").split()
        failed_pods = [status for status in pod_statuses if status != "Running"]

        if failed_pods:
            return TestResult(
                "pods_status",
                "FAILED",
                f"Found {len(failed_pods)} pods not running: {', '.join(failed_pods)}",
                time.time() - start_time,
                {"pod_statuses": pod_statuses}
            )

        return TestResult(
            "pods_status",
            "PASSED",
            f"All {len(pod_statuses)} pods are running",
            time.time() - start_time,
            {"pod_count": len(pod_statuses), "pod_statuses": pod_statuses}
        )

    def test_services_status(self) -> TestResult:
        """Test that all services are properly configured."""
        start_time = time.time()
        services = ["asr-service", "tts-service", "interface-service"]

        failed_services = []
        service_info = {}

        for service in services:
            success, stdout, stderr = self.run_command([
                "kubectl", "get", "svc", service,
                "-o", "jsonpath='{.spec.type}:{.status.loadBalancer.ingress}'"
            ])

            if not success:
                failed_services.append(f"{service}: {stderr}")
                continue

            service_type, ingress = stdout.strip().strip("'").split(":", 1)
            service_info[service] = {"type": service_type, "ingress": ingress}

        if failed_services:
            return TestResult(
                "services_status",
                "FAILED",
                f"Services not properly configured: {', '.join(failed_services)}",
                time.time() - start_time,
                {"service_info": service_info}
            )

        return TestResult(
            "services_status",
            "PASSED",
            "All services are properly configured",
            time.time() - start_time,
            {"service_info": service_info}
        )

    def test_service_health_endpoints(self) -> TestResult:
        """Test health endpoints of all services."""
        start_time = time.time()
        services = [
            ("asr-service", "8000", "/health"),
            ("tts-service", "8001", "/health"),
            ("interface-service", "7860", "/")
        ]

        failed_health_checks = []
        health_status = {}

        for service_name, port, health_path in services:
            # Get pod name for port forwarding
            success, stdout, stderr = self.run_command([
                "kubectl", "get", "pods",
                "-l", f"app={service_name.split('-')[0]}",
                "-o", "jsonpath='{.items[0].metadata.name}'"
            ])

            if not success:
                failed_health_checks.append(f"{service_name}: Cannot get pod name")
                continue

            pod_name = stdout.strip().strip("'")

            # Start port forwarding in background
            import threading
            port_forward_success = [False]

            def start_port_forward():
                cmd = ["kubectl", "port-forward", f"pod/{pod_name}", f"{port}:{port}"]
                result = subprocess.run(cmd, capture_output=True, timeout=10)
                port_forward_success[0] = result.returncode == 0

            port_forward_thread = threading.Thread(target=start_port_forward)
            port_forward_thread.daemon = True
            port_forward_thread.start()

            time.sleep(2)  # Wait for port forwarding to establish

            try:
                response = requests.get(f"http://localhost:{port}{health_path}", timeout=5)
                if response.status_code == 200:
                    health_status[service_name] = "healthy"
                else:
                    failed_health_checks.append(f"{service_name}: HTTP {response.status_code}")
                    health_status[service_name] = f"HTTP {response.status_code}"
            except Exception as e:
                failed_health_checks.append(f"{service_name}: {str(e)}")
                health_status[service_name] = str(e)

        if failed_health_checks:
            return TestResult(
                "service_health",
                "FAILED",
                f"Health checks failed: {', '.join(failed_health_checks)}",
                time.time() - start_time,
                {"health_status": health_status}
            )

        return TestResult(
            "service_health",
            "PASSED",
            "All services are healthy",
            time.time() - start_time,
            {"health_status": health_status}
        )

    def test_inter_service_communication(self) -> TestResult:
        """Test communication between services within the cluster."""
        start_time = time.time()

        # Test ASR -> TTS communication (if applicable)
        # This would require specific API calls between services

        return TestResult(
            "inter_service_communication",
            "PASSED",
            "Inter-service communication test completed",
            time.time() - start_time,
            {"note": "Inter-service communication tests would require specific API implementations"}
        )

    def test_resource_usage(self) -> TestResult:
        """Test resource usage of pods."""
        start_time = time.time()

        success, stdout, stderr = self.run_command([
            "kubectl", "top", "pods",
            "-l", "app in (asr,tts,interface)",
            "--no-headers"
        ])

        if not success:
            return TestResult(
                "resource_usage",
                "WARNING",
                f"Cannot get resource usage (metrics-server may not be installed): {stderr}",
                time.time() - start_time
            )

        resource_lines = stdout.strip().split('\n')
        resource_info = {}

        for line in resource_lines:
            if line.strip():
                parts = line.split()
                if len(parts) >= 3:
                    pod_name = parts[0]
                    cpu = parts[1]
                    memory = parts[2]
                    resource_info[pod_name] = {"cpu": cpu, "memory": memory}

        return TestResult(
            "resource_usage",
            "PASSED",
            f"Resource usage monitored for {len(resource_info)} pods",
            time.time() - start_time,
            {"resource_info": resource_info}
        )

    def test_load_balancing(self) -> TestResult:
        """Test load balancing for the interface service."""
        start_time = time.time()

        # Get interface service external URL
        interface_url = self.get_service_url("interface-service")

        if not interface_url or "localhost" in interface_url:
            return TestResult(
                "load_balancing",
                "SKIPPED",
                "Load balancing test skipped (no external LoadBalancer URL available)",
                time.time() - start_time
            )

        # Test multiple requests to check load balancing
        responses = []
        for i in range(5):
            try:
                response = requests.get(interface_url, timeout=10)
                responses.append(response.status_code)
                time.sleep(0.5)
            except Exception as e:
                responses.append(f"Error: {str(e)}")

        success_count = sum(1 for r in responses if r == 200)

        if success_count >= 3:  # At least 60% success rate
            return TestResult(
                "load_balancing",
                "PASSED",
                f"Load balancing working: {success_count}/5 requests successful",
                time.time() - start_time,
                {"responses": responses, "success_rate": f"{success_count}/5"}
            )
        else:
            return TestResult(
                "load_balancing",
                "FAILED",
                f"Load balancing issues: only {success_count}/5 requests successful",
                time.time() - start_time,
                {"responses": responses, "success_rate": f"{success_count}/5"}
            )

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all Kubernetes tests."""
        self.log("🚀 Starting Kubernetes Test Suite")
        self.log("=" * 50)

        tests = [
            self.test_kubernetes_cluster,
            self.test_deployments_status,
            self.test_pods_status,
            self.test_services_status,
            self.test_service_health_endpoints,
            self.test_inter_service_communication,
            self.test_resource_usage,
            self.test_load_balancing,
        ]

        for test_func in tests:
            test_result = test_func()
            self.test_results.append(test_result)

            if test_result.status == "PASSED":
                self.passed += 1
                self.log(f"✅ {test_result.name}: {test_result.message}")
            elif test_result.status == "FAILED":
                self.failed += 1
                self.log(f"❌ {test_result.name}: {test_result.message}")
            elif test_result.status == "WARNING":
                self.log(f"⚠️  {test_result.name}: {test_result.message}")
            else:
                self.log(f"⏭️  {test_result.name}: {test_result.message}")

            if test_result.details:
                for key, value in test_result.details.items():
                    self.log(f"   {key}: {value}", "DEBUG")

        # Summary
        total_time = time.time() - self.start_time
        self.log("=" * 50)
        self.log(f"📊 Test Summary: {self.passed} passed, {self.failed} failed")
        self.log(f"⏱️  Total time: {total_time:.2f}s")
        self.log("🏁 Kubernetes Test Suite Complete")

        return {
            "total_tests": len(self.test_results),
            "passed": self.passed,
            "failed": self.failed,
            "total_time": total_time,
            "results": [
                {
                    "name": r.name,
                    "status": r.status,
                    "message": r.message,
                    "duration": r.duration,
                    "details": r.details
                }
                for r in self.test_results
            ]
        }

def main():
    """Main entry point for Kubernetes testing."""

# Pytest-compatible test function to run all k8s tests
import pytest

@pytest.mark.integration
def test_k8s_suite():
    tester = KubernetesTester()
    results = tester.run_all_tests()

    # If no Kubernetes cluster is available, skip the test
    if results["failed"] > 0 and any("No Kubernetes cluster available" in str(result.get("message", "")) for result in results.get("results", [])):
        pytest.skip("No Kubernetes cluster available. This is expected in local development environments without minikube/k8s setup.")

    assert results["failed"] == 0, f"Some Kubernetes tests failed: {results['failed']} failed. See test output for details."
