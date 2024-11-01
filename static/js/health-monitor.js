class HealthMonitor {
    constructor() {
        this.healthStatus = {
            ec2: 'healthy',
            rds: 'healthy',
            lastCheck: Date.now(),
            dbConnections: 0,
            dbLatency: 0,
            securityStatus: 'secure'
        };
        this.startMonitoring();
    }

    async checkHealth() {
        try {
            const [ec2Health, rdsHealth, securityHealth] = await Promise.all([
                fetch('/api/health/ec2'),
                fetch('/api/health/rds'),
                fetch('/api/health/security')
            ]);

            this.healthStatus = {
                ec2: await ec2Health.json(),
                rds: await rdsHealth.json(),
                security: await securityHealth.json(),
                lastCheck: Date.now()
            };

            // Handle high traffic scenarios
            if (this.healthStatus.ec2.load > 80) {
                this.triggerAutoScaling();
            }

            // Monitor database performance
            if (this.healthStatus.rds.latency > 1000) {
                this.switchToReadReplica();
            }

            this.updateDashboard();
        } catch (error) {
            console.error('Health check failed:', error);
            this.handleHealthCheckFailure();
        }
    }

    async triggerAutoScaling() {
        try {
            await fetch('/api/scaling/trigger', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
        } catch (error) {
            console.error('Auto-scaling trigger failed:', error);
        }
    }

    async switchToReadReplica() {
        try {
            await fetch('/api/database/switch-replica', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
        } catch (error) {
            console.error('Read replica switch failed:', error);
        }
    }

    startMonitoring() {
        setInterval(() => this.checkHealth(), AWS_CONFIG.healthCheck.interval);
    }

    updateDashboard() {
        const healthIndicators = document.querySelectorAll('.health-indicator');
        healthIndicators.forEach(indicator => {
            const service = indicator.dataset.service;
            indicator.textContent = this.healthStatus[service].status;
            indicator.className = `health-indicator ${this.healthStatus[service].status}`;
        });
    }

    handleHealthCheckFailure() {
        // Implement failover logic
        loadBalancer().getEndpoint()
            .then(endpoint => {
                console.log('Failing over to:', endpoint);
                // Redirect if necessary
                if (window.location.hostname !== endpoint) {
                    window.location.href = endpoint + window.location.pathname;
                }
            });
    }
}
