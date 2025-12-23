import re
import pulumi
import pulumi_aws as aws
from phase2_ecs_alb import deploy_phase2
from phase4_cloudfront_s3_frontend import build_phase4_cloudfront_s3_frontend

project = pulumi.get_project()
stack = pulumi.get_stack()

def slug(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9-]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s

common_tags = {"Project": project, "Stack": stack}

# S3
bucket_name = f"{project}-{stack}-assets"
assets_bucket = aws.s3.Bucket("assetsBucket", bucket=bucket_name, tags=common_tags)

pulumi.export("bucket_name", assets_bucket.bucket)
pulumi.export("bucket_arn", assets_bucket.arn)

# ECR
repo_name = slug(f"{project}-{stack}")
app_repo = aws.ecr.Repository(
    "appRepo",
    name=repo_name,
    image_scanning_configuration=aws.ecr.RepositoryImageScanningConfigurationArgs(scan_on_push=True),
    tags=common_tags,
)

ecr_repo_url = app_repo.repository_url 

pulumi.export("ecr_repo_name", app_repo.name)
pulumi.export("ecr_repo_url", ecr_repo_url)


phase2 = deploy_phase2(ecr_repo_url)
# Phase 2 outputs (existing resources, NOT creating new ones)
alb_dns_name = phase2["alb_dns_name"]   # ALB DNS (used by CloudFront origin)
lb = phase2["lb"]                       # Application Load Balancer
tg = phase2["tg"]                       # Target Group (ALB -> ECS)
cluster = phase2["cluster"]             # ECS Cluster
service = phase2["service"]             # ECS Service


# -----------------------------
# Phase 7 - Observability (minimal)
# Purpose:
#   Add CloudWatch alarms for existing backend resources
#   (NO infrastructure replacement)
# -----------------------------
alarm_prefix = f"{project}-{stack}"

# 1) ALB 5XX errors (ELB generated)
# Detect load balancer level failures
alb_5xx = aws.cloudwatch.MetricAlarm(
    "alb5xxAlarm",
    name=f"{alarm_prefix}-alb-5xx",
    alarm_description="ALB is returning 5xx responses (ELB generated).",
    namespace="AWS/ApplicationELB",
    metric_name="HTTPCode_ELB_5XX_Count",
    statistic="Sum",
    period=60,
    evaluation_periods=1,
    threshold=1,
    comparison_operator="GreaterThanOrEqualToThreshold",
    treat_missing_data="notBreaching",
    dimensions={
        "LoadBalancer": lb.arn_suffix,   # e.g. app/appAlb/xxxx
    },
)

# 2) TargetGroup unhealthy
# Detect backend ECS tasks health issues
tg_unhealthy = aws.cloudwatch.MetricAlarm(
    "targetUnhealthyAlarm",
    name=f"{alarm_prefix}-tg-unhealthy",
    alarm_description="TargetGroup has 0 healthy hosts.",
    namespace="AWS/ApplicationELB",
    metric_name="HealthyHostCount",
    statistic="Minimum",
    period=60,
    evaluation_periods=1,
    threshold=1,
    comparison_operator="LessThanThreshold",
    treat_missing_data="breaching",
    dimensions={
        "LoadBalancer": lb.arn_suffix,
        "TargetGroup": tg.arn_suffix,
    },
)

# 3) ECS CPU high
# Detect CPU pressure on ECS service
ecs_cpu_high = aws.cloudwatch.MetricAlarm(
    "ecsCpuHighAlarm",
    name=f"{alarm_prefix}-ecs-cpu-high",
    alarm_description="ECS service CPU utilization is high.",
    namespace="AWS/ECS",
    metric_name="CPUUtilization",
    statistic="Average",
    period=60,
    evaluation_periods=3,
    threshold=80,
    comparison_operator="GreaterThanOrEqualToThreshold",
    treat_missing_data="notBreaching",
    dimensions={
        "ClusterName": cluster.name,
        "ServiceName": service.name,
    },
)

# 4) ECS Memory high
# Detect memory pressure on ECS service
ecs_mem_high = aws.cloudwatch.MetricAlarm(
    "ecsMemHighAlarm",
    name=f"{alarm_prefix}-ecs-mem-high",
    alarm_description="ECS service Memory utilization is high.",
    namespace="AWS/ECS",
    metric_name="MemoryUtilization",
    statistic="Average",
    period=60,
    evaluation_periods=3,
    threshold=80,
    comparison_operator="GreaterThanOrEqualToThreshold",
    treat_missing_data="notBreaching",
    dimensions={
        "ClusterName": cluster.name,
        "ServiceName": service.name,
    },
)

# Export alarm names (for verification / demo)
name=pulumi.export("alarm_alb_5xx", alb_5xx.name)
pulumi.export("alarm_tg_unhealthy", tg_unhealthy.name)
pulumi.export("alarm_ecs_cpu_high", ecs_cpu_high.name)
pulumi.export("alarm_ecs_mem_high", ecs_mem_high.name)


build_phase4_cloudfront_s3_frontend(
    project=project,
    stack=stack,
    common_tags=common_tags,
    alb_dns_name=alb_dns_name,
    frontend_dir="../frontend",
)