import boto3
import json
import time
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FargateServiceDeployer:
    def __init__(self):
        self.ecs = boto3.client('ecs')
        self.cluster_name = 'typescript-apps-cluster'
        
    def create_cluster(self):
        """Create ECS cluster if it doesn't exist"""
        try:
            self.ecs.create_cluster(
                clusterName=self.cluster_name,
                capacityProviders=['FARGATE']
            )
            logger.info(f"Created cluster: {self.cluster_name}")
        except self.ecs.exceptions.ClientException:
            logger.info(f"Cluster {self.cluster_name} already exists")

    def register_task_definition(
        self,
        image_uri: str,
        config_json: Dict,
        env_vars: Dict[str, str],
        cpu: str = '256',  # 0.25 vCPU
        memory: str = '512'  # 512 MB
    ) -> str:
        """Register a task definition for the TypeScript application"""
        
        container_definition = {
            'name': 'typescript-app',
            'image': image_uri,
            'essential': True,
            'environment': [
                {'name': k, 'value': str(v)} for k, v in env_vars.items()
            ],
            # Add the JSON configuration as an environment variable
            'environment': [
                *[{'name': k, 'value': str(v)} for k, v in env_vars.items()],
                {'name': 'APP_CONFIG', 'value': json.dumps(config_json)}
            ],
            'logConfiguration': {
                'logDriver': 'awslogs',
                'options': {
                    'awslogs-group': '/ecs/typescript-apps',
                    'awslogs-region': boto3.session.Session().region_name,
                    'awslogs-stream-prefix': 'typescript'
                }
            },
            # Health check for the continuous application
            'healthCheck': {
                'command': ['CMD-SHELL', 'curl -f http://localhost:3000/health || exit 1'],
                'interval': 30,
                'timeout': 5,
                'retries': 3,
                'startPeriod': 60
            }
        }

        response = self.ecs.register_task_definition(
            family='typescript-app',
            networkMode='awsvpc',
            requiresCompatibilities=['FARGATE'],
            cpu=cpu,
            memory=memory,
            containerDefinitions=[container_definition],
            executionRoleArn='arn:aws:iam::YOUR_ACCOUNT_ID:role/ecsTaskExecutionRole'
        )
        
        return response['taskDefinition']['taskDefinitionArn']

    def create_service(
        self,
        service_name: str,
        task_definition_arn: str,
        subnet_ids: List[str],
        security_group_ids: List[str]
    ):
        """Create a service to maintain the running container"""
        try:
            self.ecs.create_service(
                cluster=self.cluster_name,
                serviceName=service_name,
                taskDefinition=task_definition_arn,
                desiredCount=1,  # Each service maintains one container
                launchType='FARGATE',
                networkConfiguration={
                    'awsvpcConfiguration': {
                        'subnets': subnet_ids,
                        'securityGroups': security_group_ids,
                        'assignPublicIp': 'ENABLED'
                    }
                },
                schedulingStrategy='REPLICA',
                deploymentConfiguration={
                    'maximumPercent': 200,
                    'minimumHealthyPercent': 100
                }
            )
            logger.info(f"Created service: {service_name}")
        except self.ecs.exceptions.ServiceNotFoundException:
            logger.info(f"Updating existing service: {service_name}")
            self.ecs.update_service(
                cluster=self.cluster_name,
                service=service_name,
                taskDefinition=task_definition_arn
            )

def main():
    # Replace these with your values
    IMAGE_URI = 'YOUR_ECR_REPO.dkr.ecr.REGION.amazonaws.com/typescript-app:latest'
    SUBNET_IDS = ['subnet-xxxxx', 'subnet-yyyyy']  # Your subnet IDs
    SECURITY_GROUP_IDS = ['sg-xxxxx']  # Your security group IDs
    NUM_SERVICES = 200  # Number of containers/services to deploy
    
    # Base environment variables (common across all containers)
    BASE_ENV_VARS = {
        'NODE_ENV': 'production',
        'PORT': '3000'
    }

    deployer = FargateServiceDeployer()
    
    try:
        # Create cluster
        deployer.create_cluster()
        
        # Deploy services
        for i in range(NUM_SERVICES):
            service_name = f'typescript-app-{i}'
            
            # Create unique configuration for each container
            config_json = {
                'instanceId': i,
                'config': f'config-{i}'
                # Add other instance-specific configuration
            }
            
            # Combine base env vars with instance-specific ones
            env_vars = {
                **BASE_ENV_VARS,
                'INSTANCE_ID': str(i)
            }
            
            # Register task definition
            task_def_arn = deployer.register_task_definition(
                IMAGE_URI,
                config_json,
                env_vars
            )
            
            # Create/update service
            deployer.create_service(
                service_name,
                task_def_arn,
                SUBNET_IDS,
                SECURITY_GROUP_IDS
            )
            
            logger.info(f"Deployed service {i+1} of {NUM_SERVICES}")
            
            # Small delay to avoid API throttling
            time.sleep(1)

    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        raise

if __name__ == "__main__":
    main()