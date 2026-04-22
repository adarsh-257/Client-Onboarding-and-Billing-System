"""
Setup AWS resources for the onboarding system.
Run: python scripts/setup_aws.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import boto3
from botocore.exceptions import ClientError


def setup_s3(region='us-east-1', bucket_name='client-onboarding-docs'):
    """Create and configure S3 bucket."""
    print("\n☁️  Setting up AWS S3...\n")

    s3 = boto3.client('s3', region_name=region)

    # Create bucket
    try:
        if region == 'us-east-1':
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': region}
            )
        print(f"  ✅ Bucket '{bucket_name}' created")
    except ClientError as e:
        if e.response['Error']['Code'] in ['BucketAlreadyOwnedByYou', 'BucketAlreadyExists']:
            print(f"  ✓ Bucket '{bucket_name}' already exists")
        else:
            print(f"  ❌ Error: {e}")
            return

    # Enable default encryption (SSE-S3)
    try:
        s3.put_bucket_encryption(
            Bucket=bucket_name,
            ServerSideEncryptionConfiguration={
                'Rules': [{
                    'ApplyServerSideEncryptionByDefault': {
                        'SSEAlgorithm': 'AES256'
                    },
                    'BucketKeyEnabled': True,
                }]
            }
        )
        print("  ✅ Default encryption enabled (AES256)")
    except ClientError as e:
        print(f"  ⚠️  Encryption setup: {e}")

    # Block public access
    try:
        s3.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                'BlockPublicAcls': True,
                'IgnorePublicAcls': True,
                'BlockPublicPolicy': True,
                'RestrictPublicBuckets': True,
            }
        )
        print("  ✅ Public access blocked")
    except ClientError as e:
        print(f"  ⚠️  Public access block: {e}")

    # Enable versioning
    try:
        s3.put_bucket_versioning(
            Bucket=bucket_name,
            VersioningConfiguration={'Status': 'Enabled'}
        )
        print("  ✅ Versioning enabled")
    except ClientError as e:
        print(f"  ⚠️  Versioning: {e}")

    # Lifecycle policy
    try:
        s3.put_bucket_lifecycle_configuration(
            Bucket=bucket_name,
            LifecycleConfiguration={
                'Rules': [
                    {
                        'ID': 'auto-delete-expired-documents',
                        'Filter': {'Prefix': 'documents/'},
                        'Status': 'Enabled',
                        'Expiration': {'Days': 365},
                    },
                    {
                        'ID': 'delete-old-versions',
                        'Filter': {'Prefix': ''},
                        'Status': 'Enabled',
                        'NoncurrentVersionExpiration': {'NoncurrentDays': 30},
                    },
                ]
            }
        )
        print("  ✅ Lifecycle policies configured (365 day retention)")
    except ClientError as e:
        print(f"  ⚠️  Lifecycle: {e}")

    print(f"\n🎉 S3 setup complete!")
    print(f"   Bucket: {bucket_name}")
    print(f"   Region: {region}")
    print(f"   Encryption: AES256 (SSE-S3)")
    print(f"   Public Access: Blocked\n")


def setup_lambda(region='us-east-1'):
    """Setup Lambda function for error monitoring (creates from deployment package)."""
    print("⚡ Lambda setup instructions:")
    print("   The Lambda function code is in: lambda/error_monitor/handler.py")
    print("   Deploy via AWS Console or CLI:")
    print()
    print("   cd lambda/error_monitor")
    print("   zip -r function.zip handler.py")
    print(f"   aws lambda create-function \\")
    print(f"     --function-name onboarding-error-monitor \\")
    print(f"     --runtime python3.11 \\")
    print(f"     --handler handler.lambda_handler \\")
    print(f"     --zip-file fileb://function.zip \\")
    print(f"     --role <YOUR_LAMBDA_ROLE_ARN> \\")
    print(f"     --region {region}")
    print()


if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()

    region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    bucket = os.getenv('S3_BUCKET_NAME', 'client-onboarding-docs')

    setup_s3(region=region, bucket_name=bucket)
    setup_lambda(region=region)
