const AWS_CONFIG = {
    regions: {
        primary: 'us-east-1',
        backup: 'us-west-2'
    },
    endpoints: {
        'us-east-1': 'http://ec2-primary.freshbasket.com',
        'us-west-2': 'http://ec2-backup.freshbasket.com'
    },
    healthCheck: {
        interval: 300000, // 5 minutes in milliseconds
        timeout: 5000 // 5 seconds timeout for health checks
    },
    database: {
        readReplicas: ['rds-read-1.freshbasket.com', 'rds-read-2.freshbasket.com'],
        writeEndpoint: 'rds-primary.freshbasket.com'
    }
};

// Health monitoring function
function monitorSystemHealth() {
    return {
        checkEC2Health: async () => {
            try {
                const response = await fetch('/api/health/ec2');
                return await response.json();
            } catch (error) {
                console.error('EC2 health check failed:', error);
                return { status: 'error', message: error.toString() };
            }
        },
        checkRDSHealth: async () => {
            try {
                const response = await fetch('/api/health/rds');
                return await response.json();
            } catch (error) {
                console.error('RDS health check failed:', error);
                return { status: 'error', message: error.toString() };
            }
        }
    };
}

// Load balancing function
function loadBalancer() {
    return {
        getEndpoint: async () => {
            try {
                const health = await monitorSystemHealth().checkEC2Health();
                return health.status === 'healthy' 
                    ? AWS_CONFIG.endpoints[AWS_CONFIG.regions.primary]
                    : AWS_CONFIG.endpoints[AWS_CONFIG.regions.backup];
            } catch (error) {
                console.error('Load balancer error:', error);
                return AWS_CONFIG.endpoints[AWS_CONFIG.regions.backup];
            }
        }
    };
}
