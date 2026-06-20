When configuring HTTP load balancing on NetScaler ADC, the standard workflow involves:
1. Creating Server objects (representing physical/virtual backend IPs).
2. Creating a Service Group (logical grouping of servers running the same service type, e.g., HTTP).
3. Binding the Server objects to the Service Group with specific destination ports.
4. Creating an LB Virtual Server (VIP) to receive client traffic.
5. Binding the Service Group to the LB Virtual Server.

Always verify that the VIP and backend servers are reachable and that the service group members show an 'UP' state after binding.