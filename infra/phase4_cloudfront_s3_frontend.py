import os
import json
import mimetypes

import pulumi
import pulumi_aws as aws


def upload_dir_as_s3_objects(bucket_name: pulumi.Input[str], src_dir: str):
    """
    Upload all files under src_dir to S3 bucket as objects.
    Good for MVP / demo. For production, prefer CI/CD sync (aws s3 sync) + invalidation.
    """
    if not os.path.isdir(src_dir):
        pulumi.log.warn(f"[frontend] directory not found: {src_dir} (skip upload)")
        return []

    objects = []
    for root, _, files in os.walk(src_dir):
        for filename in files:
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, src_dir).replace("\\", "/")

            content_type, _ = mimetypes.guess_type(full_path)
            content_type = content_type or "application/octet-stream"

            obj = aws.s3.BucketObject(
                f"frontend-{rel_path.replace('/', '-')}",
                bucket=bucket_name,
                key=rel_path,
                source=pulumi.FileAsset(full_path),
                content_type=content_type,
            )
            objects.append(obj)

    return objects


def build_phase4_cloudfront_s3_frontend(
    *,
    project: str,
    stack: str,
    common_tags: dict,
    alb_dns_name: pulumi.Input[str],
    frontend_dir: str = "../frontend",
):
    """
    CloudFront single entrypoint (HTTPS) with 2 origins:
      - default behavior: S3 static frontend
      - /api/* behavior: ALB backend (HTTP origin ok)
    This avoids browser mixed-content issues.
    """

    # -------------------------
    # S3 bucket (private)
    # -------------------------
    frontend_bucket = aws.s3.Bucket(
        "frontendBucket",
        bucket=f"{project}-{stack}-frontend",
        tags=common_tags,
    )

    aws.s3.BucketPublicAccessBlock(
        "frontendBucketPab",
        bucket=frontend_bucket.id,
        block_public_acls=True,
        block_public_policy=True,
        ignore_public_acls=True,
        restrict_public_buckets=True,
    )

    # Upload frontend (MVP)
    upload_dir_as_s3_objects(frontend_bucket.bucket, frontend_dir)

    # -------------------------
    # CloudFront OAC for S3
    # -------------------------
    oac = aws.cloudfront.OriginAccessControl(
        "frontendOac",
        name=f"{project}-{stack}-frontend-oac",
        description="OAC for S3 static frontend",
        origin_access_control_origin_type="s3",
        signing_behavior="always",
        signing_protocol="sigv4",
    )

    # -------------------------
    # CloudFront Distribution
    # -------------------------
    dist = aws.cloudfront.Distribution(
        "appCdn",
        enabled=True,
        comment=f"{project}-{stack} CloudFront (S3 frontend + ALB api)",
        default_root_object="index.html",
        price_class="PriceClass_100",
        origins=[
            # Origin: S3 (REST endpoint)
            aws.cloudfront.DistributionOriginArgs(
                origin_id="s3-frontend",
                domain_name=frontend_bucket.bucket_regional_domain_name,
                origin_access_control_id=oac.id,
            ),
            # Origin: ALB (custom origin)
            aws.cloudfront.DistributionOriginArgs(
                origin_id="alb-backend",
                domain_name=alb_dns_name,
                custom_origin_config=aws.cloudfront.DistributionOriginCustomOriginConfigArgs(
                    http_port=80,
                    https_port=443,
                    origin_protocol_policy="http-only",
                    origin_ssl_protocols=["TLSv1.2"],
                ),
            ),
        ],
        default_cache_behavior=aws.cloudfront.DistributionDefaultCacheBehaviorArgs(
            target_origin_id="s3-frontend",
            viewer_protocol_policy="redirect-to-https",
            allowed_methods=["GET", "HEAD", "OPTIONS"],
            cached_methods=["GET", "HEAD"],
            compress=True,
            forwarded_values=aws.cloudfront.DistributionDefaultCacheBehaviorForwardedValuesArgs(
                query_string=False,
                cookies=aws.cloudfront.DistributionDefaultCacheBehaviorForwardedValuesCookiesArgs(
                    forward="none"
                ),
            ),
        ),
        ordered_cache_behaviors=[
            # API: /api/* -> ALB
            aws.cloudfront.DistributionOrderedCacheBehaviorArgs(
                path_pattern="/api/*",
                target_origin_id="alb-backend",
                viewer_protocol_policy="redirect-to-https",
                allowed_methods=["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"],
                cached_methods=["GET", "HEAD"],
                compress=True,
                # Disable caching for APIs
                min_ttl=0,
                default_ttl=0,
                max_ttl=0,
                forwarded_values=aws.cloudfront.DistributionOrderedCacheBehaviorForwardedValuesArgs(
                    query_string=True,
                    headers=["*"],
                    cookies=aws.cloudfront.DistributionOrderedCacheBehaviorForwardedValuesCookiesArgs(
                        forward="all"
                    ),
                ),
            )
        ],
        restrictions=aws.cloudfront.DistributionRestrictionsArgs(
            geo_restriction=aws.cloudfront.DistributionRestrictionsGeoRestrictionArgs(
                restriction_type="none"
            )
        ),
        viewer_certificate=aws.cloudfront.DistributionViewerCertificateArgs(
            cloudfront_default_certificate=True
        ),
        tags=common_tags,
    )

    # -------------------------
    # Bucket policy: allow CF distribution to read objects (OAC)
    # -------------------------
    policy = pulumi.Output.all(frontend_bucket.arn, dist.arn).apply(
        lambda args: json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "AllowCloudFrontReadOnly",
                        "Effect": "Allow",
                        "Principal": {"Service": "cloudfront.amazonaws.com"},
                        "Action": ["s3:GetObject"],
                        "Resource": [f"{args[0]}/*"],
                        "Condition": {"StringEquals": {"AWS:SourceArn": args[1]}},
                    }
                ],
            }
        )
    )

    aws.s3.BucketPolicy(
        "frontendBucketPolicy",
        bucket=frontend_bucket.id,
        policy=policy,
    )

    # Exports
    pulumi.export("frontend_bucket_name", frontend_bucket.bucket)
    pulumi.export("cloudfront_domain_name", dist.domain_name)
    pulumi.export("cloudfront_distribution_id", dist.id)

    return {
        "frontend_bucket": frontend_bucket,
        "cloudfront_distribution": dist,
    }
