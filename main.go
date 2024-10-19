package main

import (
	"fmt"
	"net"
	"os"
	"sync"
	"time"
)

func main() {
	if len(os.Args) != 2 {
		fmt.Println("Usage: go run main.go <host>")
		os.Exit(1)
	}

	host := os.Args[1]
	var wg sync.WaitGroup

	for port := 1; port <= 65535; port++ {
		wg.Add(1)
		go func(p int) {
			defer wg.Done()
			address := fmt.Sprintf("%s:%d", host, p)
			conn, err := net.DialTimeout("tcp", address, 1*time.Second)
			if err == nil {
				conn.Close()
				fmt.Printf("Port %d: Open\n", p)
			}
		}(port)
	}

	wg.Wait()
}
