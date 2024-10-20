package main

import (
	"bufio"
	"flag"
	"fmt"
	"net"
	"os"
	"sort"
	"sync"
	"time"
)

type ScanResult struct {
	Port int
	Open bool
}

func main() {
	hostsFile := flag.String("f", "", "File containing list of hosts to scan")
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
	}

	flag.Parse()

	if *help {
		flag.Usage()
		os.Exit(0)
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

	for _, host := range hosts {
		fmt.Printf("Scanning host: %s\n", host)
		results := scanHost(host, *startPort, *endPort, *numWorkers, *showAll)
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
		hosts = append(hosts, scanner.Text())
	}

	if err := scanner.Err(); err != nil {
		return nil, err
	}

	return hosts, nil
}

func scanHost(host string, startPort, endPort, numWorkers int, showAll bool) []ScanResult {
	ports := make(chan int, numWorkers)
	results := make(chan ScanResult, endPort-startPort+1)
	var wg sync.WaitGroup

	for i := 0; i < numWorkers; i++ {
		wg.Add(1)
		go worker(host, ports, results, &wg)
	}

	go func() {
		for port := startPort; port <= endPort; port++ {
			ports <- port
		}
		close(ports)
	}()

	go func() {
		wg.Wait()
		close(results)
	}()

	var scanResults []ScanResult
	for result := range results {
		if result.Open || showAll {
			scanResults = append(scanResults, result)
		}
	}

	return scanResults
}

func worker(host string, ports <-chan int, results chan<- ScanResult, wg *sync.WaitGroup) {
	defer wg.Done()
	for port := range ports {
		address := fmt.Sprintf("%s:%d", host, port)
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
	sort.Slice(results, func(i, j int) bool {
		return results[i].Port < results[j].Port
	})

	fmt.Printf("Scan results for %s:\n", host)
	openPorts := 0
	for _, result := range results {
		if result.Open {
			fmt.Printf("Port %d: open\n", result.Port)
			openPorts++
		} else if showAll {
			fmt.Printf("Port %d: closed\n", result.Port)
		}
	}
	if openPorts == 0 {
		fmt.Println("No open ports found.")
	} else {
		fmt.Printf("Total open ports: %d\n", openPorts)
	}
	fmt.Println()
}
