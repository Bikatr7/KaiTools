import subprocess
import os
import tempfile
import unittest
import socket
import threading
import time
import sys
from typing import List, Tuple

class TestPortScanner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.exe_path = cls._compile_go_program()
        cls.test_servers = cls._start_test_servers([8080, 8081, 8082])
        time.sleep(1)  ## Give servers time to start

    @classmethod
    def tearDownClass(cls):
        cls._stop_test_servers(cls.test_servers)

    @classmethod
    def _compile_go_program(cls) -> str:
        """Compile the Go program and return the path to the executable."""
        if sys.platform == "win32":
            exe_path = "portscanner.exe"
        else:
            exe_path = "portscanner"

        subprocess.run(["go", "build", "-o", exe_path, "PortScanner/portscanner.go"], 
                      check=True)
        return os.path.abspath(exe_path)

    @classmethod
    def _create_test_server(cls, port: int) -> Tuple[socket.socket, threading.Thread]:
        """Create a test TCP server on the specified port."""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('localhost', port))
        server_socket.listen(1)

        def server_thread():
            while True:
                try:
                    conn, _ = server_socket.accept()
                    conn.close()
                except:
                    break

        thread = threading.Thread(target=server_thread, daemon=True)
        thread.start()
        return server_socket, thread

    @classmethod
    def _start_test_servers(cls, ports: List[int]) -> List[Tuple[socket.socket, threading.Thread]]:
        """Start multiple test servers."""
        return [cls._create_test_server(port) for port in ports]

    @classmethod
    def _stop_test_servers(cls, servers: List[Tuple[socket.socket, threading.Thread]]):
        """Stop all test servers."""
        for server_socket, thread in servers:
            server_socket.close()

    def _create_temp_file(self, content: str) -> str:
        """Create a temporary file with the given content."""
        temp = tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8')
        temp.write(content)
        temp.close()
        return temp.name

    def _run_scanner(self, args: List[str]) -> Tuple[str, str, int]:
        """Run the port scanner with given arguments."""
        process = subprocess.Popen(
            [self.exe_path] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        return stdout, stderr, process.returncode

    def test_single_open_port(self):
        """Test scanning a single known open port."""
        stdout, stderr, rc = self._run_scanner(["-p", "8080", "-e", "8080", "localhost"])
        self.assertIn("Port 8080: open", stdout)
        self.assertEqual(rc, 0)

    def test_port_range(self):
        """Test scanning a range of ports."""
        stdout, stderr, rc = self._run_scanner(["-p", "8080", "-e", "8082", "localhost"])
        self.assertIn("Port 8080: open", stdout)
        self.assertIn("Port 8081: open", stdout)
        self.assertIn("Port 8082: open", stdout)
        self.assertEqual(rc, 0)

    def test_ports_file(self):
        """Test scanning ports from a file."""
        ports_file = self._create_temp_file("8080\n8081\n8082\n")
        try:
            stdout, stderr, rc = self._run_scanner(["-P", ports_file, "localhost"])
            self.assertIn("Port 8080: open", stdout)
            self.assertIn("Port 8081: open", stdout)
            self.assertIn("Port 8082: open", stdout)
            self.assertEqual(rc, 0)
        finally:
            os.unlink(ports_file)

    def test_hosts_file(self):
        """Test scanning multiple hosts from a file."""
        hosts_file = self._create_temp_file("localhost\n127.0.0.1\n")
        try:
            stdout, stderr, rc = self._run_scanner(["-f", hosts_file, "-p", "8080", "-e", "8080"])
            self.assertIn("Scanning host: localhost", stdout)
            self.assertIn("Scanning host: 127.0.0.1", stdout)
            self.assertEqual(rc, 0)
        finally:
            os.unlink(hosts_file)

    def test_invalid_port_range(self):
        """Test invalid port range handling."""
        stdout, stderr, rc = self._run_scanner(["-p", "65536", "-e", "65537", "localhost"])
        self.assertNotEqual(rc, 0)

    def test_invalid_host(self):
        """Test invalid hostname handling."""
        stdout, stderr, rc = self._run_scanner(["-p", "8080", "-e", "8080", "invalid.host.local"])
        self.assertIn("No open ports found", stdout)
        self.assertEqual(rc, 0)

    def test_show_all_ports(self):
        """Test showing all ports (including closed ones)."""
        stdout, stderr, rc = self._run_scanner(["-p", "8080", "-e", "8081", "-a", "localhost"])
        self.assertIn("Port 8080: open", stdout)
        self.assertIn("Port 8081: open", stdout)
        self.assertEqual(rc, 0)

    def test_worker_count(self):
        """Test different worker counts."""
        stdout1, _, rc1 = self._run_scanner(["-p", "8080", "-e", "8082", "-w", "1", "localhost"])
        stdout2, _, rc2 = self._run_scanner(["-p", "8080", "-e", "8082", "-w", "10", "localhost"])
        
        self.assertEqual(rc1, 0)
        self.assertEqual(rc2, 0)
        self.assertIn("Port 8080: open", stdout1)
        self.assertIn("Port 8080: open", stdout2)

    def test_invalid_ports_file(self):
        """Test handling of invalid ports file."""
        ports_file = self._create_temp_file("invalid\n8080\n")
        try:
            stdout, stderr, rc = self._run_scanner(["-P", ports_file, "localhost"])
            self.assertNotEqual(rc, 0)
        finally:
            os.unlink(ports_file)

    def test_empty_ports_file(self):
        """Test handling of empty ports file."""
        ports_file = self._create_temp_file("")
        try:
            stdout, stderr, rc = self._run_scanner(["-P", ports_file, "localhost"])
            self.assertIn("Error reading ports file: empty ports file", stdout)
            self.assertNotEqual(rc, 0)  ## Should fail with empty ports file
        finally:
            os.unlink(ports_file)

    def test_help_flag(self):
        """Test help flag displays usage information."""
        stdout, stderr, rc = self._run_scanner(["-h"])
        self.assertIn("Usage:", stderr)
        self.assertEqual(rc, 0)

    def test_concurrent_host_scans(self):
        """Test scanning multiple hosts concurrently."""
        hosts_file = self._create_temp_file("localhost\n127.0.0.1\nlocalhost\n")
        try:
            stdout, stderr, rc = self._run_scanner(["-f", hosts_file, "-p", "8080", "-e", "8082", "-w", "50"])
            self.assertIn("Scanning host: localhost", stdout)
            self.assertIn("Port 8080: open", stdout)
            self.assertEqual(rc, 0)
        finally:
            os.unlink(hosts_file)

    def test_mixed_ports_and_range(self):
        """Test that using both -P and port range flags is handled correctly."""
        ports_file = self._create_temp_file("8080\n8081\n")
        try:
            stdout, stderr, rc = self._run_scanner(["-P", ports_file, "-p", "8080", "-e", "8081", "localhost"])
            self.assertNotEqual(rc, 0)  ## Should fail when mixing -P with -p/-e
        finally:
            os.unlink(ports_file)

    def test_duplicate_ports(self):
        """Test handling of duplicate ports in ports file."""
        ports_file = self._create_temp_file("8080\n8080\n8081\n8081\n")
        try:
            stdout, stderr, rc = self._run_scanner(["-P", ports_file, "localhost"])
            self.assertIn("Port 8080: open", stdout)
            self.assertIn("Port 8081: open", stdout)
            self.assertEqual(rc, 0)
        finally:
            os.unlink(ports_file)

    def test_large_port_range(self):
        """Test handling of a large port range."""
        stdout, stderr, rc = self._run_scanner(["-p", "8000", "-e", "8100", "-w", "200", "localhost"])
        self.assertIn("Port 8080: open", stdout)
        self.assertIn("Port 8081: open", stdout)
        self.assertIn("Port 8082: open", stdout)
        self.assertEqual(rc, 0)

    def test_zero_workers(self):
        """Test handling of zero workers."""
        stdout, stderr, rc = self._run_scanner(["-p", "8080", "-e", "8080", "-w", "0", "localhost"])
        self.assertNotEqual(rc, 0)  ## Should fail with invalid worker count

    def test_negative_worker_count(self):
        """Test handling of negative worker count."""
        stdout, stderr, rc = self._run_scanner(["-p", "8080", "-e", "8080", "-w", "-1", "localhost"])
        self.assertNotEqual(rc, 0)  ## Should fail with negative worker count

    def test_extremely_large_worker_count(self):
        """Test handling of extremely large worker count."""
        stdout, stderr, rc = self._run_scanner(["-p", "8080", "-e", "8080", "-w", "1000000", "localhost"])
        self.assertEqual(rc, 0)  ## Should still work, but might be resource-limited

    def test_invalid_host_format(self):
        """Test handling of invalid host format."""
        stdout, stderr, rc = self._run_scanner(["-p", "8080", "-e", "8080", "invalid..host..format"])
        self.assertIn("No open ports found", stdout)
        self.assertEqual(rc, 0)

    def test_non_existent_files(self):
        """Test handling of non-existent files."""
        stdout, stderr, rc = self._run_scanner(["-f", "nonexistent.txt", "-p", "8080", "-e", "8080"])
        self.assertNotEqual(rc, 0)
        
        stdout, stderr, rc = self._run_scanner(["-P", "nonexistent.txt", "localhost"])
        self.assertNotEqual(rc, 0)

    def test_empty_hosts_file(self):
        """Test handling of empty hosts file."""
        hosts_file = self._create_temp_file("")
        try:
            stdout, stderr, rc = self._run_scanner(["-f", hosts_file, "-p", "8080", "-e", "8080"])
            self.assertNotEqual(rc, 0)  ## Should fail with empty hosts file
        finally:
            os.unlink(hosts_file)

    def test_mixed_valid_invalid_ports(self):
        """Test handling of mixed valid and invalid ports in ports file."""
        ports_file = self._create_temp_file("8080\ninvalid\n8081\n-1\n65536\n8082\n")
        try:
            stdout, stderr, rc = self._run_scanner(["-P", ports_file, "localhost"])
            self.assertNotEqual(rc, 0)  ## Should fail with invalid port numbers
        finally:
            os.unlink(ports_file)

    def test_mixed_valid_invalid_hosts(self):
        """Test handling of mixed valid and invalid hosts in hosts file."""
        hosts_file = self._create_temp_file("localhost\ninvalid.host\n127.0.0.1\n")
        try:
            stdout, stderr, rc = self._run_scanner(["-f", hosts_file, "-p", "8080", "-e", "8080"])
            self.assertIn("Scanning host: localhost", stdout)
            self.assertIn("Scanning host: 127.0.0.1", stdout)
            self.assertEqual(rc, 0)  ## Should continue with valid hosts
        finally:
            os.unlink(hosts_file)

    def test_reverse_port_range(self):
        """Test handling of reverse port range."""
        stdout, stderr, rc = self._run_scanner(["-p", "8082", "-e", "8080", "localhost"])
        self.assertNotEqual(rc, 0)  ## Should fail when start port > end port

    def test_same_start_end_port(self):
        """Test handling of same start and end port."""
        stdout, stderr, rc = self._run_scanner(["-p", "8080", "-e", "8080", "localhost"])
        self.assertIn("Port 8080: open", stdout)
        self.assertEqual(rc, 0)

    def test_whitespace_in_files(self):
        """Test handling of whitespace in input files."""
        hosts_file = self._create_temp_file("localhost\n  127.0.0.1  \n\n  \nlocalhost\n")
        ports_file = self._create_temp_file("8080\n  8081  \n\n  \n8082\n")
        try:
            stdout, stderr, rc = self._run_scanner(["-f", hosts_file, "-P", ports_file])
            self.assertIn("Port 8080: open", stdout)
            self.assertIn("Port 8081: open", stdout)
            self.assertEqual(rc, 0)
        finally:
            os.unlink(hosts_file)
            os.unlink(ports_file)

    def test_no_flags(self):
        """Test running scanner without any flags."""
        stdout, stderr, rc = self._run_scanner(["localhost"])
        self.assertEqual(rc, 0)  ## Should work with default values

    def test_invalid_flag_combination(self):
        """Test invalid flag combinations."""
        ## Test -f with positional host argument
        stdout, stderr, rc = self._run_scanner(["-f", "hosts.txt", "localhost"])
        self.assertNotEqual(rc, 0)

    def test_timeout_handling(self):
        """Test handling of connection timeouts."""
        ## Test with a non-routable IP to force timeout
        stdout, stderr, rc = self._run_scanner(["-p", "8080", "-e", "8080", "10.255.255.255"])
        self.assertIn("No open ports found", stdout)
        self.assertEqual(rc, 0)

    def test_unicode_in_files(self):
        """Test handling of Unicode characters in input files."""
        ## Using simpler Unicode characters that are more likely to work across systems
        hosts_file = self._create_temp_file("localhost\néxample.com\n127.0.0.1\n")
        try:
            stdout, stderr, rc = self._run_scanner(["-f", hosts_file, "-p", "8080", "-e", "8080"])
            self.assertIn("Scanning host: localhost", stdout)
            self.assertIn("Scanning host: 127.0.0.1", stdout)
            self.assertEqual(rc, 0)
        finally:
            os.unlink(hosts_file)

    def test_very_long_hostname(self):
        """Test handling of very long hostnames."""
        long_hostname = "a" * 253 + ".com"  # Max DNS name length is 253 characters
        stdout, stderr, rc = self._run_scanner(["-p", "8080", "-e", "8080", long_hostname])
        self.assertIn("No open ports found", stdout)
        self.assertEqual(rc, 0)

    def test_concurrent_port_and_host_scanning(self):
        """Test scanning multiple ports on multiple hosts concurrently."""
        hosts_file = self._create_temp_file("localhost\n127.0.0.1\n")
        try:
            stdout, stderr, rc = self._run_scanner(["-f", hosts_file, "-p", "8080", "-e", "8082", "-w", "50"])
            self.assertIn("Scanning host: localhost", stdout)
            self.assertIn("Scanning host: 127.0.0.1", stdout)
            self.assertIn("Port 8080: open", stdout)
            self.assertIn("Port 8081: open", stdout)
            self.assertIn("Port 8082: open", stdout)
            self.assertEqual(rc, 0)
        finally:
            os.unlink(hosts_file)

    def test_memory_usage_large_scan(self):
        """Test memory usage with a large scan."""
        stdout, stderr, rc = self._run_scanner(["-p", "1", "-e", "10000", "-w", "1000", "localhost"])
        self.assertEqual(rc, 0)  # Should complete without memory issues

    def test_connection_refused_vs_timeout(self):
        """Test different types of connection failures."""
        ## Connection refused (port not listening)
        stdout, stderr, rc = self._run_scanner(["-p", "9999", "-e", "9999", "-a", "localhost"])
        self.assertIn("Port 9999: closed", stdout)
        self.assertEqual(rc, 0)

        ## Connection timeout (non-routable IP, different from existing timeout test)
        stdout, stderr, rc = self._run_scanner(["-p", "8080", "-e", "8080", "192.168.255.255"])
        self.assertIn("No open ports found", stdout)
        self.assertEqual(rc, 0)

    def test_resource_cleanup(self):
        """Test proper cleanup of resources."""
        # Run multiple scans to check for resource leaks
        for _ in range(5):
            stdout, stderr, rc = self._run_scanner(["-p", "8080", "-e", "8082", "-w", "50", "localhost"])
            self.assertEqual(rc, 0)
            self.assertIn("Port 8080: open", stdout)
            
        ## Run a final scan to verify resources are still available
        stdout, stderr, rc = self._run_scanner(["-p", "8080", "-e", "8080", "localhost"])
        self.assertEqual(rc, 0)
        self.assertIn("Port 8080: open", stdout)

    def test_all_valid_flags_combination(self):
        """Test using all valid flags together."""
        hosts_file = self._create_temp_file("localhost\n127.0.0.1\n")
        ports_file = self._create_temp_file("8080\n8081\n8082\n")
        try:
            stdout, stderr, rc = self._run_scanner([
                "-f", hosts_file,
                "-P", ports_file,
                "-w", "50",
                "-a"
            ])
            self.assertIn("Port 8080: open", stdout)
            self.assertIn("Port 8081: open", stdout)
            self.assertIn("Port 8082: open", stdout)
            self.assertEqual(rc, 0)
        finally:
            os.unlink(hosts_file)
            os.unlink(ports_file)

    def test_localhost_variants(self):
        """Test different localhost formats."""
        variants = ["localhost", "127.0.0.1"]
        for host in variants:
            stdout, stderr, rc = self._run_scanner(["-p", "8080", "-e", "8080", host])
            self.assertIn("Port 8080: open", stdout)
            self.assertEqual(rc, 0)

    def test_port_deduplication_and_order(self):
        """Test port deduplication and order preservation."""
        ports_file = self._create_temp_file("8082\n8080\n8081\n8080\n8082\n")
        try:
            stdout, stderr, rc = self._run_scanner(["-P", ports_file, "localhost", "-a"])
            
            ## Check for successful scan
            self.assertEqual(rc, 0)
            
            ## Get all port lines from output
            port_lines = [line for line in stdout.split('\n') if line.startswith('Port ')]
            
            ## Count unique ports
            unique_ports = set(line.split(':')[0] for line in port_lines)
            self.assertEqual(len(unique_ports), 3)  ## Should only have 3 unique ports
            
            for port in ["8080", "8081", "8082"]:
                matching_lines = [line for line in port_lines if line.startswith(f'Port {port}')]
                self.assertEqual(len(matching_lines), 1, f"Port {port} appears multiple times")
        finally:
            os.unlink(ports_file)

    def test_signal_handling(self):
        """Test graceful shutdown on SIGINT."""
        if sys.platform == "win32":
            self.skipTest("Signal handling test skipped on Windows")
            return

        import signal
        import threading

        def kill_after_delay():
            time.sleep(1)  # Give the scan time to start
            os.kill(process.pid, signal.SIGINT)

        process = subprocess.Popen(
            [self.exe_path, "-p", "1", "-e", "1000", "localhost"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        thread = threading.Thread(target=kill_after_delay)
        thread.start()

        try:
            stdout, stderr = process.communicate(timeout=5)  ## Add timeout to prevent hanging
            thread.join(timeout=1)  ## Add timeout for thread join
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            self.fail("Process did not respond to SIGINT within timeout")
        except Exception as e:
            process.kill()
            self.fail(f"Unexpected error during signal handling test: {e}")

        # Check if process exited
        self.assertIsNotNone(process.returncode, "Process did not exit")

    def test_ipv6_localhost(self):
        """Test IPv6 localhost scanning if supported."""
        try:
            sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            sock.close()
            
            stdout, stderr, rc = self._run_scanner(["-p", "8080", "-e", "8080", "::1"])
            self.assertEqual(rc, 0)
            ## Note: Don't assert on open ports as IPv6 support may vary
        except socket.error:
            ## IPv6 not supported, skip test
            self.skipTest("IPv6 not supported on this system")

    def test_reliable_remote_hosts(self):
        """Test scanning well-known remote hosts that have high uptime."""
        ## Test cases: (host, port, expected_status)
        reliable_hosts = [
            ("1.1.1.1", 53, True),        ## Cloudflare DNS
            ("8.8.8.8", 53, True),        ## Google DNS
            ("google.com", 443, True),     ## Google HTTPS
            ("cloudflare.com", 443, True), ## Cloudflare HTTPS
        ]

        for host, port, expected_open in reliable_hosts:
            stdout, stderr, rc = self._run_scanner(["-p", str(port), "-e", str(port), host])
            self.assertEqual(rc, 0, f"Scan failed for {host}:{port}")
            
            if expected_open:
                self.assertIn(f"Port {port}: open", stdout, 
                    f"Expected port {port} to be open on {host}")
            else:
                self.assertIn("No open ports found", stdout, 
                    f"Expected port {port} to be closed on {host}")

if __name__ == '__main__':
    unittest.main(verbosity=2) 