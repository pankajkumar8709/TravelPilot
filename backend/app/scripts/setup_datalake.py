"""Phase 10 — create the S3 data-lake bucket (idempotent).

Usage:
  set DATA_LAKE_BUCKET=travelpilot-datalake-<your-suffix>
  set AWS_PROFILE=travelpilot
  python -m app.scripts.setup_datalake
"""
from __future__ import annotations

from app.config import settings


def main() -> int:
    bucket = settings.data_lake_bucket
    if not bucket:
        print("Set DATA_LAKE_BUCKET first (globally-unique name).")
        return 2
    try:
        import boto3
        from botocore.exceptions import ClientError

        session = (boto3.Session(profile_name=settings.aws_profile, region_name=settings.aws_region_name)
                   if settings.aws_profile else boto3.Session(region_name=settings.aws_region_name))
        s3 = session.client("s3")
        region = settings.aws_region_name
        try:
            if region == "us-east-1":
                s3.create_bucket(Bucket=bucket)
            else:
                s3.create_bucket(Bucket=bucket,
                                 CreateBucketConfiguration={"LocationConstraint": region})
            print(f"[setup_datalake] created bucket {bucket} in {region}")
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
                print(f"[setup_datalake] bucket {bucket} already exists — OK")
            else:
                raise
        # keep raw data private (it's a landing zone, not a website)
        s3.put_public_access_block(
            Bucket=bucket,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True, "IgnorePublicAcls": True,
                "BlockPublicPolicy": True, "RestrictPublicBuckets": True,
            },
        )
        print("[setup_datalake] public access blocked (private raw landing zone). Done.")
        return 0
    except Exception as e:  # noqa: BLE001
        print(f"[setup_datalake] FAILED: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
