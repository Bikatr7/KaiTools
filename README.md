# KaiTools

An (ongoing) set of Cybersecurity tools written in Go that I've been making for the purpose of furthering my knowledge in Golang and Cybersecurity.


## PortScanner

A tool for scanning TCP ports on one or multiple hosts. It allows users to specify port ranges, adjust concurrency, and scan multiple hosts from a file.

## Features

- Scan a single host or multiple hosts from a file
- Customizable port range
- Adjustable number of concurrent workers
- Option to show all ports (including closed ones)
- Simple command-line interface

## Usage

The basic syntax for using the PortScanner is:

```
./portscanner.exe [flags] <host>
./portscanner.exe [flags] -f <hosts_file>
```

## Flags

- `-f`: Specify a file containing a list of hosts to scan
- `-p`: Set the start port for scanning (default: 1)
- `-e`: Set the end port for scanning (default: 65535)
- `-w`: Set the number of worker goroutines (default: 100)
- `-h`: Show help information
- `-a`: Show all ports, including closed ones

## Examples

1. Scan a single host with default settings:
   ```
   ./portscanner.exe example.com
   ```

2. Scan a single host with a specific port range:
   ```
   ./portscanner.exe -p 80 -e 443 example.com
   ```

3. Scan multiple hosts from a file:
   ```
   ./portscanner.exe -f hosts.txt
   ```

4. Scan multiple hosts from a file with custom settings:
   ```
   ./portscanner.exe -f hosts.txt -p 1 -e 1024 -w 200
   ```