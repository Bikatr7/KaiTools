# KaiTools

An (ongoing) set of Cybersecurity tools written in Go that I've been making for the purpose of furthering my knowledge in Golang and Cybersecurity.

## PortScanner

A Go-based TCP port scanner that can scan multiple hosts and ports simultaneously. It has error handling, efficient resource use, and a wide range of configuration options.

### Features

- **Port Scanning Options**:
  - Single port scanning
  - Port range scanning
  - Port list from file
  - Concurrent port scanning
  - Port deduplication

- **Host Management**:
  - Single host scanning
  - Multiple hosts from file
  - Support for various host formats
  - IPv4 and IPv6 support (where available)

- **Performance**:
  - Configurable worker count
  - Concurrent host and port scanning
  - Efficient resource management
  - Connection timeout handling

- **Input/Output**:
  - Show all ports (including closed)
  - Custom port ranges
  - File-based input for hosts and ports
  - Detailed scan results
  - Progress reporting

### Installation

```bash
go build -o portscanner PortScanner/portscanner.go
```

### Usage

Basic syntax:
```bash
./portscanner [flags] <host>
./portscanner [flags] -f <hosts_file>
```

### Flags

- `-f string`: File containing list of hosts to scan
- `-P string`: File containing list of ports to scan
- `-p int`: Start port for scanning (default: 1)
- `-e int`: End port for scanning (default: 65535)
- `-w int`: Number of worker goroutines (default: 100) (increasing this may impact system performance but will speed up the scan)
- `-a`: Show all ports (including closed)
- `-h`: Show help information

### Examples

1. **Scan a single host with default settings**:
   ```bash
   ./portscanner example.com
   ```

2. **Scan specific port range**:
   ```bash
   ./portscanner -p 80 -e 443 example.com
   ```

3. **Scan multiple hosts from file**:
   ```bash
   ./portscanner -f hosts.txt
   ```

4. **Scan using ports from file**:
   ```bash
   ./portscanner -P ports.txt example.com
   ```

5. **Custom worker count and show all ports**:
   ```bash
   ./portscanner -w 200 -a example.com
   ```

6. **Combine multiple options**:
   ```bash
   ./portscanner -f hosts.txt -P ports.txt -w 200 -a
   ```

### Testing

The port scanner includes a comprehensive test suite covering:
- Core functionality
- Error handling
- Edge cases
- Performance
- Resource management
- Network conditions

Run tests:
```bash
python -m unittest tests/portscanner/test_portscanner.py -v
```

Test coverage includes:
- Input validation
- File handling
- Network operations
- Concurrent processing
- Resource cleanup
- Error conditions
- Platform-specific behavior

### Notes

- Large worker counts may impact system performance
- Some tests require internet connectivity
- IPv6 support depends on system capabilities
- Signal handling behavior varies by platform

### Requirements

- Go 1.x
- Python 3.6+ (for testing)
- Network connectivity (for remote host tests)