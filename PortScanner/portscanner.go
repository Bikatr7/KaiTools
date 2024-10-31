package main

import (
	"bufio"
	"flag"
	"fmt"
	"net"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"
)

type ScanResult struct {
	Port int
	Open bool
}

func main() {
	hostsFile := flag.String("f", "", "File containing list of hosts to scan")
	portsFile := flag.String("P", "", "File containing list of ports to scan")
	startPort := flag.Int("p", 1, "Start port for scanning (default: 1)")
	endPort := flag.Int("e", 65535, "End port for scanning (default: 65535)")
	numWorkers := flag.Int("w", 100, "Number of worker goroutines (default: 100)")
	help := flag.Bool("h", false, "Show help")
	showAll := flag.Bool("a", false, "Show all ports (including closed)")

	flag.Usage = func() {
		fmt.Fprintf(os.Stderr, "Usage:\n")
		fmt.Fprintf(os.Stderr, "  %s [flags] <host>\n", os.Args[0])
		fmt.Fprintf(os.Stderr, "  %s [flags] -f <hosts_file>\n\n", os.Args[0])
		fmt.Fprintf(os.Stderr, "Flags:\n")
		flag.PrintDefaults()
		fmt.Fprintf(os.Stderr, "\nExamples:\n")
		fmt.Fprintf(os.Stderr, "  Scan a single host with default settings:\n")
		fmt.Fprintf(os.Stderr, "    %s example.com\n\n", os.Args[0])
		fmt.Fprintf(os.Stderr, "  Scan a single host with a specific port range:\n")
		fmt.Fprintf(os.Stderr, "    %s -p 80 -e 443 example.com\n\n", os.Args[0])
		fmt.Fprintf(os.Stderr, "  Scan multiple hosts from a file:\n")
		fmt.Fprintf(os.Stderr, "    %s -f hosts.txt\n\n", os.Args[0])
		fmt.Fprintf(os.Stderr, "  Scan multiple hosts from a file with custom settings:\n")
		fmt.Fprintf(os.Stderr, "    %s -f hosts.txt -p 1 -e 1024 -w 200\n", os.Args[0])
		fmt.Fprintf(os.Stderr, "  Scan a single host with ports from a file:\n")
		fmt.Fprintf(os.Stderr, "    %s -P ports.txt example.com\n", os.Args[0])
	}

	flag.Parse()

	if *help {
		flag.Usage()
		os.Exit(0)
	}

	if (*portsFile == "" && (*startPort < 1 || *startPort > 65535 || *endPort < 1 || *endPort > 65535 || *startPort > *endPort)) ||
		(*portsFile != "" && (*startPort != 1 || *endPort != 65535)) {
		fmt.Println("Invalid port configuration. Provide a valid port range with -p and -e or use -P to specify a ports file.")
		os.Exit(1)
	}

	if *numWorkers <= 0 {
		fmt.Println("Error: Number of workers must be greater than 0")
		os.Exit(1)
	}

	var hosts []string
	if *hostsFile != "" {
		var err error
		hosts, err = readHostsFromFile(*hostsFile)
		if err != nil {
			fmt.Printf("Error reading hosts file: %v\n", err)
			os.Exit(1)
		}
	} else if len(flag.Args()) > 0 {
		hosts = []string{flag.Arg(0)}
	} else {
		flag.Usage()
		os.Exit(1)
	}

	var ports []int
	if *portsFile != "" {
		var err error
		ports, err = readPortsFromFile(*portsFile)
		if err != nil {
			fmt.Printf("Error reading ports file: %v\n", err)
			os.Exit(1)
		}
	} else {
		for port := *startPort; port <= *endPort; port++ {
			ports = append(ports, port)
		}
	}

	for _, host := range hosts {
		fmt.Printf("Scanning host: %s\n", host)
		results := scanHost(host, ports, *numWorkers, *showAll)
		printResults(host, results, *showAll)
	}
}

func readHostsFromFile(filename string) ([]string, error) {
	file, err := os.Open(filename)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	var hosts []string
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line != "" {
			hosts = append(hosts, line)
		}
	}

	if err := scanner.Err(); err != nil {
		return nil, err
	}

	if len(hosts) == 0 {
		return nil, fmt.Errorf("empty hosts file")
	}

	return hosts, nil
}

func readPortsFromFile(filename string) ([]int, error) {
	file, err := os.Open(filename)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	seen := make(map[int]bool) // Track seen ports
	var ports []int
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line != "" {
			port, err := strconv.Atoi(line)
			if err != nil || port < 1 || port > 65535 {
				return nil, fmt.Errorf("invalid port number: %s", line)
			}
			if !seen[port] { // Only add port if not seen before
				seen[port] = true
				ports = append(ports, port)
			}
		}
	}

	if err := scanner.Err(); err != nil {
		return nil, err
	}

	if len(ports) == 0 {
		return nil, fmt.Errorf("empty ports file")
	}

	return ports, nil
}

func scanHost(host string, ports []int, numWorkers int, showAll bool) []ScanResult {
	portChan := make(chan int, numWorkers)
	results := make(chan ScanResult, numWorkers)
	var wg sync.WaitGroup

	for i := 0; i < numWorkers; i++ {
		wg.Add(1)
		go worker(host, portChan, results, &wg)
	}

	go func() {
		for _, port := range ports {
			portChan <- port
		}
		close(portChan)
	}()

	// Close the results channel once all workers are done
	go func() {
		wg.Wait()
		close(results)
	}()

	// Process results as they come
	var scanResults []ScanResult
	openPorts := 0
	for result := range results {
		if result.Open || showAll {
			fmt.Printf("Port %d: %s\n", result.Port, portStatus(result.Open))
			if result.Open {
				openPorts++
			}
			scanResults = append(scanResults, result)
		}
	}

	if openPorts == 0 {
		fmt.Println("No open ports found.")
	} else {
		fmt.Printf("Total open ports: %d\n", openPorts)
	}

	return scanResults
}

func portStatus(open bool) string {
	if open {
		return "open"
	}
	return "closed"
}

func worker(host string, portChan <-chan int, results chan<- ScanResult, wg *sync.WaitGroup) {
	defer wg.Done()
	for port := range portChan {
		address := net.JoinHostPort(host, strconv.Itoa(port))
		conn, err := net.DialTimeout("tcp", address, 1*time.Second)
		if err == nil {
			conn.Close()
			results <- ScanResult{Port: port, Open: true}
		} else {
			results <- ScanResult{Port: port, Open: false}
		}
	}
}

func printResults(host string, results []ScanResult, showAll bool) {
	if len(results) == 0 {
		fmt.Println("No results to display.")
		return
	}

	openPorts := 0
	for _, result := range results {
		if showAll {
			fmt.Printf("Port %d: %s\n", result.Port, portStatus(result.Open))
		}
		if result.Open {
			openPorts++
		}
	}

	if openPorts == 0 {
		fmt.Println("No open ports found.")
	} else {
		fmt.Printf("Total open ports on %s: %d\n", host, openPorts)
	}
}
