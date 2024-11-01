import boto3
from datetime import datetime

class LoadBalancer:
    def __init__(self):
        self.ec2_client = boto3.client('ec2')
        self.elb_client = boto3.client('elbv2')
        
    def check_instance_health(self):
        try:
            response = self.elb_client.describe_target_health(
                TargetGroupArn='your-target-group-arn'
            )
            return response['TargetHealthDescriptions']
        except Exception as e:
            return None
    
    def route_traffic(self):
        try:
            instances = self.check_instance_health()
            healthy_instances = [i for i in instances if i['TargetHealth']['State'] == 'healthy']
            return healthy_instances[0] if healthy_instances else None
        except Exception as e:
            return None
