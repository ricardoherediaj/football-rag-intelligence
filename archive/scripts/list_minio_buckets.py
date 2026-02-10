#!/usr/bin/env python3
"""List MinIO buckets and their contents."""

from minio import Minio


def main():
    client = Minio(
        'localhost:9000',
        access_key='minioadmin',
        secret_key='minioadmin',
        secure=False
    )

    # List all buckets
    buckets = client.list_buckets()
    print("Available buckets:")
    for bucket in buckets:
        print(f"  - {bucket.name}")

        # List objects in bucket
        objects = list(client.list_objects(bucket.name, recursive=True))
        print(f"    Objects: {len(objects)}")
        if objects:
            print(f"    Sample: {objects[0].object_name}")


if __name__ == "__main__":
    main()
