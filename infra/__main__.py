import pulumi
from pulumi_aws import s3

project = pulumi.get_project()
stack = pulumi.get_stack()

# 用 project + stack 組出唯一且可辨識的 bucket name
# 注意：S3 bucket name 必須全域唯一、只能小寫、不能底線
bucket_name = f"{project}-{stack}-assets"

bucket = s3.Bucket(
    resource_name="assetsBucket",
    bucket=bucket_name,
    tags={
        "Project": project,
        "Stack": stack,
    },
)

pulumi.export("bucket_name", bucket.bucket)
pulumi.export("bucket_arn", bucket.arn)
