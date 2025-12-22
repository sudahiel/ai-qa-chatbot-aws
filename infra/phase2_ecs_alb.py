import pulumi
import pulumi_aws as aws


def deploy_phase2(ecr_repo_url: pulumi.Input[str]):
    project = pulumi.get_project()
    stack = pulumi.get_stack()

    # 你 Phase 1 已 push 的 image tag
    image_uri = pulumi.Output.concat(ecr_repo_url, ":dev-latest")


    # -----------------------------
    # Network: Minimal public VPC
    # -----------------------------
    vpc = aws.ec2.Vpc(
        "appVpc",
        cidr_block="10.0.0.0/16",
        enable_dns_hostnames=True,
        enable_dns_support=True,
        tags={"Project": project, "Stack": stack},
    )
    #igw=（Internet Gateway）
    igw = aws.ec2.InternetGateway(
        "appIgw",
        vpc_id=vpc.id,
        tags={"Project": project, "Stack": stack},
    )

    public_rt = aws.ec2.RouteTable(
        "publicRt",
        vpc_id=vpc.id,
        routes=[aws.ec2.RouteTableRouteArgs(cidr_block="0.0.0.0/0", gateway_id=igw.id)],
        tags={"Project": project, "Stack": stack},
    )
    #AZ=Availability Zone（可用區）
    azs = aws.get_availability_zones(state="available").names[:2]

    public_subnets = []
    for i, az in enumerate(azs):
        subnet = aws.ec2.Subnet(
            f"publicSubnet-{i}",
            vpc_id=vpc.id,
            availability_zone=az,
            cidr_block=f"10.0.{i}.0/24",
            map_public_ip_on_launch=True,
            tags={"Project": project, "Stack": stack},
        )
        aws.ec2.RouteTableAssociation(
            f"publicRta-{i}",
            subnet_id=subnet.id,
            route_table_id=public_rt.id,
        )
        public_subnets.append(subnet)

    # -----------------------------
    # Security Groups (create ONCE)  ← 注意：這段在迴圈外
    # -----------------------------
    alb_sg = aws.ec2.SecurityGroup(
        "albSg",
        vpc_id=vpc.id,
        description="ALB SG",
        tags={"Project": project, "Stack": stack},
    )

    aws.ec2.SecurityGroupRule(
        "albSgIngressHttp",
        type="ingress",
        security_group_id=alb_sg.id,
        protocol="tcp",
        from_port=80,
        to_port=80,
        cidr_blocks=["0.0.0.0/0"],
    )
    # ALB -> targets (ECS tasks)
    # 這條是關鍵：沒有 egress，ALB health check 會 Target.Timeout，最後變 503
    aws.ec2.SecurityGroupRule(
        "albSgEgressAll",
        type="egress",
        security_group_id=alb_sg.id,
        protocol="-1",
        from_port=0,
        to_port=0,
        cidr_blocks=["0.0.0.0/0"],
    )
    ecs_sg = aws.ec2.SecurityGroup(
        "ecsSg",
        vpc_id=vpc.id,
        description="ECS tasks SG",
        tags={"Project": project, "Stack": stack},
    )

    aws.ec2.SecurityGroupRule(
        "ecsSgIngressFromAlb",
        type="ingress",
        security_group_id=ecs_sg.id,
        protocol="tcp",
        from_port=8080,
        to_port=8080,
        source_security_group_id=alb_sg.id,
    )

    aws.ec2.SecurityGroupRule(
        "ecsSgEgressAll",
        type="egress",
        security_group_id=ecs_sg.id,
        protocol="-1",
        from_port=0,
        to_port=0,
        cidr_blocks=["0.0.0.0/0"],
    )


    # -----------------------------
    # CloudWatch Logs
    # -----------------------------
    log_group = aws.cloudwatch.LogGroup(
        "backendLogGroup",
        retention_in_days=7,
        tags={"Project": project, "Stack": stack},
    )

    # -----------------------------
    # ECS Cluster
    # -----------------------------
    cluster = aws.ecs.Cluster(
        "appCluster",
        tags={"Project": project, "Stack": stack},
    )

    # -----------------------------
    # IAM Task Execution Role
    # -----------------------------
    task_exec_role = aws.iam.Role(
        "taskExecRole",
        assume_role_policy=aws.iam.get_policy_document(statements=[
            aws.iam.GetPolicyDocumentStatementArgs(
                effect="Allow",
                principals=[aws.iam.GetPolicyDocumentStatementPrincipalArgs(
                    type="Service",
                    identifiers=["ecs-tasks.amazonaws.com"]
                )],
                actions=["sts:AssumeRole"]
            )
        ]).json,
        tags={"Project": project, "Stack": stack},
    )

    aws.iam.RolePolicyAttachment(
        "taskExecRolePolicy",
        role=task_exec_role.name,
        policy_arn="arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy",
    )

    # -----------------------------
    # ALB + Target Group + Listener
    # -----------------------------
    lb = aws.lb.LoadBalancer(
        "appAlb",
        load_balancer_type="application",
        security_groups=[alb_sg.id],
        subnets=[s.id for s in public_subnets],
        tags={"Project": project, "Stack": stack},
    )

    tg = aws.lb.TargetGroup(
        "appTg",
        port=8080,
        protocol="HTTP",
        target_type="ip",
        vpc_id=vpc.id,
        health_check=aws.lb.TargetGroupHealthCheckArgs(
            protocol="HTTP",
            path="/health",
            matcher="200-499",
            interval=15,
            timeout=5,
            healthy_threshold=2,
            unhealthy_threshold=2,
        ),
        tags={"Project": project, "Stack": stack},
    )

    listener = aws.lb.Listener(
        "appListener",
        load_balancer_arn=lb.arn,
        port=80,
        protocol="HTTP",
        default_actions=[aws.lb.ListenerDefaultActionArgs(
            type="forward",
            target_group_arn=tg.arn,
        )],
    )

    # -----------------------------
    # ECS Task Definition + Service
    # -----------------------------
    task_def = aws.ecs.TaskDefinition(
        "backendTaskDef",
        family=f"{project}-{stack}-backend",
        cpu="256",
        memory="512",
        network_mode="awsvpc",
        requires_compatibilities=["FARGATE"],
        execution_role_arn=task_exec_role.arn,
        container_definitions=pulumi.Output.json_dumps([{
            "name": "backend",
            "image": image_uri,
            "essential": True,
            "portMappings": [{
                "containerPort": 8080,
                "hostPort": 8080,
                "protocol": "tcp"
            }],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": log_group.name,
                    "awslogs-region": aws.get_region().region,
                    "awslogs-stream-prefix": "backend"
                }
            }
        }]),
        tags={"Project": project, "Stack": stack},
    )

    service = aws.ecs.Service(
        "backendService",
        cluster=cluster.arn,
        desired_count=1,
        launch_type="FARGATE",
        task_definition=task_def.arn,
        health_check_grace_period_seconds=60,
        network_configuration=aws.ecs.ServiceNetworkConfigurationArgs(
            subnets=[s.id for s in public_subnets],
            security_groups=[ecs_sg.id],
            assign_public_ip=True,
        ),
        load_balancers=[aws.ecs.ServiceLoadBalancerArgs(
            target_group_arn=tg.arn,
            container_name="backend",
            container_port=8080,
        )],
        # 這裡是重點：避免 pulumi up 把 CI/CD 更新過的 task definition 蓋回去
        opts=pulumi.ResourceOptions(
            depends_on=[listener],
            ignore_changes=["task_definition"],
        ),
        tags={"Project": project, "Stack": stack},
    )


    pulumi.export("backend_image_uri", image_uri)
    pulumi.export("alb_dns_name", lb.dns_name)
    pulumi.export("ecs_cluster_name", cluster.name)
    pulumi.export("ecs_service_name", service.name)


    return lb.dns_name
