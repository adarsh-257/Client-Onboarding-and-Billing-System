#!/bin/bash
set -e

echo "🚀 Starting AWS Docker Deployment for Client Onboarding System..."

# 1. Check for AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI could not be found."
    echo "Please install it via Homebrew: brew install awscli"
    echo "Then configure it: aws configure"
    exit 1
fi

# Confirm credentials
aws sts get-caller-identity > /dev/null || { echo "❌ Invalid or Missing AWS Credentials. Please run 'aws configure'."; exit 1; }

# Determine deployment variables
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region || echo "us-east-1")
BUCKET_NAME="onboarding-deploy-${ACCOUNT_ID}-${REGION}"
ZIP_NAME="source-$(date +%s).zip"

# 2. Package Source Code
echo "📦 Packaging source code..."
cd ..
zip -r deploy/${ZIP_NAME} . -x "*.git*" "*venv*" "*__pycache__*" "*.pytest_cache*" "*deploy/*.zip*" "*.DS_Store*" "*.sqlite3*" "*.db*"
cd deploy

# 3. Setup S3 Deployment Bucket
echo "☁️  Verifying S3 Deployment Bucket: ${BUCKET_NAME}"
if aws s3api head-bucket --bucket "$BUCKET_NAME" 2>/dev/null; then
    echo "  ✓ Bucket exists"
else
    echo "  Creating deployment bucket..."
    if [ "$REGION" == "us-east-1" ]; then
        aws s3api create-bucket --bucket "$BUCKET_NAME" > /dev/null
    else
        aws s3api create-bucket --bucket "$BUCKET_NAME" --create-bucket-configuration LocationConstraint="$REGION" > /dev/null
    fi
fi

# 4. Upload to S3
echo "⬆️  Uploading code to S3..."
aws s3 cp ${ZIP_NAME} s3://${BUCKET_NAME}/${ZIP_NAME}

# 5. CloudFormation Deployment
STACK_NAME="onboarding-system-docker"
echo "⚙️  Deploying CloudFormation Stack: ${STACK_NAME}..."
echo "⏳ This may take 3-5 minutes depending on the AWS region."

aws cloudformation deploy \
    --template-file cloudformation.yaml \
    --stack-name ${STACK_NAME} \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides \
        InstanceType=t3.small \
        CodeS3Bucket=${BUCKET_NAME} \
        CodeS3Key=${ZIP_NAME}

# 6. Retrieve Outputs
echo "\n🎉 Deployment completed successfully!"
aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME} \
    --query "Stacks[0].Outputs" \
    --output table

echo "👉 Note: The application might take another 60-90 seconds to finish booting Docker and seeding the database internally."
