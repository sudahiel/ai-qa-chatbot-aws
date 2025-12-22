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


alb_dns_name = deploy_phase2(ecr_repo_url)



build_phase4_cloudfront_s3_frontend(
    project=project,
    stack=stack,
    common_tags=common_tags,
    alb_dns_name=alb_dns_name,
    frontend_dir="../frontend",
)


