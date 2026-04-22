"""AWS S3 client for encrypted document storage with lifecycle policies."""
import os
import logging
import hashlib
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class S3Client:
    """
    Manages S3 operations for encrypted document storage.

    Features:
    - Server-side encryption (SSE-S3 / AES256)
    - Pre-signed URLs for secure downloads
    - Lifecycle policies for automated deletion schedules
    - Bucket versioning for data protection
    """

    def __init__(self, app=None):
        self.s3 = None
        self.bucket_name = None
        self.encryption = None
        self.region = None

        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize S3 client from Flask app config."""
        self.bucket_name = app.config.get('S3_BUCKET_NAME', 'client-onboarding-docs')
        self.encryption = app.config.get('S3_ENCRYPTION', 'AES256')
        self.region = app.config.get('AWS_DEFAULT_REGION', 'us-east-1')

        try:
            self.s3 = boto3.client(
                's3',
                region_name=self.region,
                aws_access_key_id=app.config.get('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=app.config.get('AWS_SECRET_ACCESS_KEY'),
            )
            logger.info(f"S3 client initialized for bucket '{self.bucket_name}'")
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            self.s3 = None

    def ensure_bucket_exists(self):
        """Create the S3 bucket if it doesn't exist, with encryption enabled."""
        if not self.s3:
            logger.warning("S3 client not initialized")
            return False

        try:
            self.s3.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Bucket '{self.bucket_name}' already exists")
            return True
        except ClientError as e:
            error_code = int(e.response['Error']['Code'])
            if error_code == 404:
                try:
                    # Create bucket
                    create_args = {'Bucket': self.bucket_name}
                    if self.region != 'us-east-1':
                        create_args['CreateBucketConfiguration'] = {
                            'LocationConstraint': self.region
                        }
                    self.s3.create_bucket(**create_args)

                    # Enable default encryption
                    self.s3.put_bucket_encryption(
                        Bucket=self.bucket_name,
                        ServerSideEncryptionConfiguration={
                            'Rules': [{
                                'ApplyServerSideEncryptionByDefault': {
                                    'SSEAlgorithm': 'AES256'
                                },
                                'BucketKeyEnabled': True,
                            }]
                        }
                    )

                    # Block public access
                    self.s3.put_public_access_block(
                        Bucket=self.bucket_name,
                        PublicAccessBlockConfiguration={
                            'BlockPublicAcls': True,
                            'IgnorePublicAcls': True,
                            'BlockPublicPolicy': True,
                            'RestrictPublicBuckets': True,
                        }
                    )

                    # Enable versioning
                    self.s3.put_bucket_versioning(
                        Bucket=self.bucket_name,
                        VersioningConfiguration={'Status': 'Enabled'}
                    )

                    logger.info(
                        f"Bucket '{self.bucket_name}' created with encryption, "
                        f"public access blocked, and versioning enabled"
                    )
                    return True
                except ClientError as create_err:
                    logger.error(f"Failed to create bucket: {create_err}")
                    return False
            else:
                logger.error(f"Error checking bucket: {e}")
                return False

    def upload_file(self, file_obj, s3_key, content_type='application/octet-stream', metadata=None):
        """
        Upload a file to S3 with server-side encryption.

        Args:
            file_obj: File-like object to upload
            s3_key: S3 object key (path)
            content_type: MIME type of the file
            metadata: Optional dict of metadata to attach

        Returns:
            dict with upload details, or None on failure
        """
        if not self.s3:
            logger.warning("S3 client not initialized")
            return None

        extra_args = {
            'ContentType': content_type,
            'ServerSideEncryption': self.encryption,
        }
        if metadata:
            extra_args['Metadata'] = {k: str(v) for k, v in metadata.items()}

        try:
            # Calculate checksum
            file_content = file_obj.read()
            checksum = hashlib.sha256(file_content).hexdigest()
            file_obj.seek(0)

            self.s3.upload_fileobj(
                file_obj,
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args,
            )

            logger.info(f"Uploaded '{s3_key}' to bucket '{self.bucket_name}'")

            return {
                's3_key': s3_key,
                's3_bucket': self.bucket_name,
                'size_bytes': len(file_content),
                'checksum': checksum,
                'encryption': self.encryption,
                'content_type': content_type,
            }
        except ClientError as e:
            logger.error(f"Failed to upload '{s3_key}': {e}")
            return None

    def download_file(self, s3_key):
        """Download a file from S3. Returns file content bytes."""
        if not self.s3:
            return None

        try:
            response = self.s3.get_object(Bucket=self.bucket_name, Key=s3_key)
            content = response['Body'].read()
            logger.info(f"Downloaded '{s3_key}' ({len(content)} bytes)")
            return content
        except ClientError as e:
            logger.error(f"Failed to download '{s3_key}': {e}")
            return None

    def generate_presigned_url(self, s3_key, expiration=900):
        """
        Generate a pre-signed URL for secure, time-limited access.

        Args:
            s3_key: S3 object key
            expiration: URL validity in seconds (default 15 minutes)

        Returns:
            Pre-signed URL string, or None on failure
        """
        if not self.s3:
            return None

        try:
            url = self.s3.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key,
                },
                ExpiresIn=expiration,
            )
            logger.info(f"Generated presigned URL for '{s3_key}' (expires in {expiration}s)")
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None

    def delete_file(self, s3_key):
        """Delete a file from S3."""
        if not self.s3:
            return False

        try:
            self.s3.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"Deleted '{s3_key}' from bucket '{self.bucket_name}'")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete '{s3_key}': {e}")
            return False

    def apply_lifecycle_policy(self, retention_days=365):
        """
        Apply a lifecycle policy to auto-delete files after retention period.

        This automates deletion schedules across 2,000+ client files.
        """
        if not self.s3:
            return False

        try:
            self.s3.put_bucket_lifecycle_configuration(
                Bucket=self.bucket_name,
                LifecycleConfiguration={
                    'Rules': [
                        {
                            'ID': 'auto-delete-expired-documents',
                            'Filter': {'Prefix': 'documents/'},
                            'Status': 'Enabled',
                            'Expiration': {'Days': retention_days},
                        },
                        {
                            'ID': 'move-to-glacier-after-90-days',
                            'Filter': {'Prefix': 'archives/'},
                            'Status': 'Enabled',
                            'Transitions': [{
                                'Days': 90,
                                'StorageClass': 'GLACIER',
                            }],
                            'Expiration': {'Days': retention_days},
                        },
                        {
                            'ID': 'delete-old-versions',
                            'Filter': {'Prefix': ''},
                            'Status': 'Enabled',
                            'NoncurrentVersionExpiration': {
                                'NoncurrentDays': 30,
                            },
                        },
                    ]
                }
            )
            logger.info(
                f"Lifecycle policy applied: auto-delete after {retention_days} days, "
                f"glacier after 90 days, old versions after 30 days"
            )
            return True
        except ClientError as e:
            logger.error(f"Failed to apply lifecycle policy: {e}")
            return False

    def list_files(self, prefix='documents/', max_keys=100):
        """List files in S3 bucket with a given prefix."""
        if not self.s3:
            return []

        try:
            response = self.s3.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys,
            )
            files = []
            for obj in response.get('Contents', []):
                files.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                })
            return files
        except ClientError as e:
            logger.error(f"Failed to list files: {e}")
            return []

    def get_bucket_stats(self):
        """Get basic bucket statistics."""
        if not self.s3:
            return {'total_files': 0, 'total_size': 0}

        try:
            response = self.s3.list_objects_v2(Bucket=self.bucket_name)
            total_files = response.get('KeyCount', 0)
            total_size = sum(obj.get('Size', 0) for obj in response.get('Contents', []))
            return {
                'total_files': total_files,
                'total_size_bytes': total_size,
                'total_size_display': self._human_size(total_size),
            }
        except ClientError:
            return {'total_files': 0, 'total_size_bytes': 0, 'total_size_display': '0 B'}

    @staticmethod
    def _human_size(size_bytes):
        """Convert bytes to human-readable."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f'{size_bytes:.1f} {unit}'
            size_bytes /= 1024
        return f'{size_bytes:.1f} TB'


# Module-level singleton
s3_client = S3Client()
