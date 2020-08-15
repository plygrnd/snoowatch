#!/usr/bin/python3

from troposphere import Parameter, Ref, Template
from troposphere.ecs import Cluster, Service, TaskDefinition, \
    ContainerDefinition, NetworkConfiguration, \
    AwsvpcConfiguration, PortMapping

t = Template()
t.set_version('2010-09-09')


snoowatch_cluster = t.add_resource((Cluster(
    'SnooWatchAnalyzerCluster'
)))

private_fargate_subnet = t.add_parameter(Parameter(
    'Subnet',
    Type='AWS::EC2::Subnet::Id',
    Description='Private subnet for SnooWatch containers',
))

fargate_task_def = t.add_resource(TaskDefinition(
    'SnooWatchAnalyzer',
    RequiresCompatibilities=['FARGATE'],
    Cpu='1024',
    Memory='2048',
    NetworkMode='awsvpc',
    ContainerDefinitions=[
        ContainerDefinition(
            Name='snoowatch',
            Image='snoowatch',
            Essential=True,
            PortMappings=[PortMapping(ContainerPort=9200)]
        )
    ]
))

snoowatch_fargate_service = t.add_resource(Service(
    'SnooWatchAnalyzerService',
    Cluster=Ref(snoowatch_cluster),
    DesiredCount=1,
    TaskDefinition=Ref(fargate_task_def),
    LaunchType='FARGATE',
    NetworkConfiguration=NetworkConfiguration(
        AwsvpcConfiguration=AwsvpcConfiguration(
            Subnets=Ref(private_fargate_subnet)
        )
    )
))

print(t.to_yaml())
